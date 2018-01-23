# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import re

from datetime import datetime

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode, json_encode
import numpy as np

from labman.gui.handlers.base import BaseHandler
from labman.db.process import PoolingProcess, QuantificationProcess
from labman.db.plate import Plate
from labman.db.equipment import Equipment
from labman.db.composition import PoolComposition
from labman.db.exceptions import LabmanUnknownIdError


POOL_FUNCS = {
    'equal': {'function': PoolingProcess.compute_shotgun_pooling_values_eqvol,
              'parameters': [('total_vol', 'volume-'),
                             ('size', 'lib-size-')]},
    'min': {'function': PoolingProcess.compute_shotgun_pooling_values_minvol,
            'parameters': [('floor_vol', 'floor-vol-'),
                           ('floor_conc', 'floor-conc-'),
                           ('total_nmol', 'total-nm-'),
                           ('size', 'lib-size-')]},
    'floor': {'function': PoolingProcess.compute_shotgun_pooling_values_floor,
              'parameters': [('floor_vol', 'floor-vol-'),
                             ('floor_conc', 'floor-conc-'),
                             ('total_nmol', 'total-nm-'),
                             ('size', 'lib-size-')]},
    # As everything, amplicon works differently here, we use this just for
    # being able to retrieve the arguments
    'amplicon': {'function': None,
                 'parameters': [('dna_amount', 'dna-amount-'),
                                ('min_val', 'min-val-'),
                                ('max_val', 'max-val-'),
                                ('blank_volume', 'blank-val-'),
                                ('robot', 'epmotion-'),
                                ('destination', 'dest-tube-')]}}

HTML_POOL_PARAMS = {
    'min': [{'prefix': 'floor-vol-', 'value': '100',
             'desc': 'volume for low conc samples (nL):', 'min': '1',
             'step': '1'},
            {'prefix': 'floor-conc-', 'value': '20',
             'desc': 'minimum value for pooling at real estimated value (nM):',
             'min': '0.1', 'step': '0.1'},
            {'prefix': 'total-nm-', 'value': '0.002',
             'desc': 'total number of nM to have in pool (nM):',
             'min': '0.00001', 'step': '0.00001'},
            {'prefix': 'lib-size-', 'value': '500',
             'desc': 'Average library molecule size (bp):', 'min': '1',
             'step': '1'}],
    'equal': [{'prefix': 'volume-', 'value': '200',
               'desc': 'volume to pool per sample (nL):', 'min': '1',
               'step': '1'},
              {'prefix': 'lib-size-', 'value': '500',
               'desc': 'Average library molecule size (bp):', 'min': '1',
               'step': '1'}],
    'floor': [{'prefix': 'floor-vol-', 'value': '10',
               'desc': 'Minimum concentration to be included in the '
                       'pool (nM):',
               'min': '1', 'step': '1'},
              {'prefix': 'floor-conc-', 'value': '50',
               'desc': 'Minimum value for pooling for samples above min '
                       'conc (nM):',
               'min': '1', 'step': '1'},
              {'prefix': 'total-nm-', 'value': '0.002',
               'desc': 'total number of nM to have in pool (nM):',
               'min': '0.00001', 'step': '0.00001'},
              {'prefix': 'lib-size-', 'value': '500',
               'desc': 'Average library molecule size (bp):', 'min': '1',
               'step': '1'}],
    'amplicon': [{'prefix': 'dna-amount-', 'value': '240',
                  'desc': 'Total amount of DNA (ng):', 'min': '1',
                  'step': '1'},
                 {'prefix': 'min-val-', 'value': '1',
                  'desc': 'Minimum concentration value (ng/&mu;l):',
                  'min': '0.001', 'step': '0.001'},
                 {'prefix': 'max-val-', 'value': '15',
                  'desc': 'Maximum concentration value (ng/&mu;l):',
                  'min': '0.001', 'step': '0.001'},
                 {'prefix': 'blank-val-', 'value': '2',
                  'desc': 'Blanks value (ng/&mu;l):', 'min': '0.001',
                  'step': '0.001'},
                 {'prefix': 'epmotion-'}, {'prefix': 'dest-tube-'}]}


# quick function to create 2D representation of well-associated numbers
def make_2D_arrays(plate, quant_process):
    """Returns 2D arrays of the quantification values

    Parameters
    ----------
    plate: Plate
        The quantified plate
    quant_process: QuantificationProcess
        The quantification process that quantified 'plate'

    Returns
    -------
    (np.array, np.array)
        Two 2D np.arrays containing the raw concentration values and the
        the computed concentration values, respectivelly.
    """
    layout = plate.layout
    raw_concs = np.zeros_like(layout, dtype=float)
    comp_concs = np.zeros_like(layout, dtype=float)
    for comp, raw_conc, conc in quant_process.concentrations:
        well = comp.container
        row = well.row - 1
        column = well.column - 1
        raw_concs[row][column] = raw_conc
        comp_concs[row][column] = conc
    return raw_concs, comp_concs


# function to calculate estimated molar fraction for each element of pool
def calc_pool_pcts(conc_vals, pool_vols):
    """Calculate estimated molar fraction for each pool element

    Parameters
    ----------
    conc_vals: np.array
        The per-well concentration values
    pool_vols: np.array
        The per-well pool volumes

    Returns
    -------
    np.array
        The per-well molar fraction
    """
    amts = conc_vals * pool_vols
    total = amts.sum()
    pcts = amts / total
    return pcts


class BasePoolHandler(BaseHandler):
    def _compute_pools(self, plate_info):
        plate_id = plate_info['plate-id']
        func_name = plate_info['pool-func']
        func_info = POOL_FUNCS[func_name]
        function = func_info['function']
        plate = Plate(plate_id)
        quant_process = plate.quantification_process

        output = {}
        if func_name == 'amplicon':
            params = {}
            for arg, pfx in func_info['parameters']:
                param_key = '%s%s' % (pfx, plate_id)
                if param_key not in plate_info:
                    raise HTTPError(
                        400, reason='Missing parameter %s' % param_key)
                if arg in ('robot', 'destination'):
                    params[arg] = plate_info[param_key]
                else:
                    params[arg] = float(plate_info[param_key])
            # Amplicon
            output['robot'] = params.pop('robot')
            output['destination'] = params.pop('destination')
            # Compute the normalized concentrations
            quant_process.compute_concentrations(**params)
            # Compute the pooling values
            raw_concs, comp_concs = make_2D_arrays(plate, quant_process)
            output['raw_vals'] = raw_concs
            output['comp_vals'] = comp_concs
            output['pool_vals'] = comp_concs
        else:
            # Shotgun
            params = {}
            for arg, pfx in func_info['parameters']:
                param_key = '%s%s' % (pfx, plate_id)
                if param_key not in plate_info:
                    raise HTTPError(
                        400, reason='Missing parameter %s' % param_key)
                params[arg] = float(plate_info[param_key])
            # Compute the normalized concentrations
            size = params.pop('size')
            quant_process.compute_concentrations(size=size)
            # Compute the pooling values
            raw_concs, comp_concs = make_2D_arrays(plate, quant_process)
            output['raw_vals'] = raw_concs
            output['comp_vals'] = comp_concs
            output['pool_vals'] = function(comp_concs, **params)
            output['robot'] = None
            output['destination'] = None

        # Make sure the results are JSON serializable
        output['plate_id'] = plate_id
        output['pool_vals'] = output['pool_vals']
        return output


class PoolPoolProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        pool_ids = self.get_arguments('pool_id')
        self.render('pool_pooling.html', pool_ids=pool_ids)

    @authenticated
    def post(self):
        pool_name = self.get_argument('pool_name')
        pools_info = json_decode(self.get_argument('pools_info'))
        concentrations = []
        input_compositions = []
        for p_info in pools_info:
            pool_comp = PoolComposition(p_info['pool_id'])
            concentrations.append({'composition': pool_comp,
                                   'concentration': p_info['concentration']})
            input_compositions.append(
                {'composition': pool_comp, 'input_volume': p_info['volume'],
                 'percentage_of_output': p_info['percentage']})
        # Create the quantification process (DNA conc)
        q_process = QuantificationProcess.create_manual(
            self.current_user, concentrations)
        # Create the pool - Magic number 5 - > the volume for this poolings
        # is always 5 according to the wet lab.
        p_process = PoolingProcess.create(
            self.current_user, q_process, pool_name, 5, input_compositions)
        self.write({'process': p_process.id})


class LibraryPoolProcessHandler(BasePoolHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        epmotions = Equipment.list_equipment('EpMotion')
        self.render('library_pooling.html', plate_ids=plate_ids,
                    epmotions=epmotions, pool_params=HTML_POOL_PARAMS)

    @authenticated
    def post(self):
        plates_info = json_decode(self.get_argument('plates-info'))

        results = []
        for pinfo in plates_info:
            plate_result = self._compute_pools(pinfo)
            plate = Plate(plate_result['plate_id'])
            pool_name = 'Pool from plate %s (%s)' % (
                plate.external_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            # create input molar percentages
            pcts = calc_pool_pcts(plate_result['comp_vals'],
                                  plate_result['pool_vals'])
            quant_process = plate.quantification_process
            input_compositions = []
            for comp, _, _ in quant_process.concentrations:
                well = comp.container
                row = well.row - 1
                column = well.column - 1
                input_compositions.append(
                    {'composition': comp,
                     'input_volume': plate_result['pool_vals'][row][column],
                     'percentage_of_output': pcts[row][column]})
            robot = (Equipment(plate_result['robot'])
                     if plate_result['robot'] is not None else None)
            process = PoolingProcess.create(
                self.current_user, quant_process, pool_name,
                plate_result['pool_vals'].sum(), input_compositions,
                robot=robot, destination=plate_result['destination'])
            results.append({'plate-id': plate.id, 'process-id': process.id})

        self.write(json_encode(results))


# The ComputeLibraryPoolValueslHandler is meant to calculate the results from
# the pooling process and disply for user approval.
class ComputeLibraryPoolValueslHandler(BasePoolHandler):
    @authenticated
    def post(self):
        plate_info = json_decode(self.get_argument('plate-info'))
        output = self._compute_pools(plate_info)
        # we need to make sure the values are serializable
        output['pool_vals'] = output['pool_vals'].tolist()
        # We don't need to return these values to the interface
        output.pop('raw_vals')
        output.pop('comp_vals')
        output.pop('robot')
        output.pop('destination')
        self.write(output)


class DownloadPoolFileHandler(BaseHandler):
    @authenticated
    def get(self, process_id):
        try:
            process = PoolingProcess(int(process_id))
        except LabmanUnknownIdError:
            raise HTTPError(404, reason='PoolingProcess %s does not exist'
                            % process_id)
        text = process.generate_pool_file()

        filename = 'PoolFile_%s_%s.csv' % (
            re.sub('[^0-9a-zA-Z\-\_]+', '_',
                   process.pool.container.external_id), process.id)

        self.set_header('Content-Type', 'text/csv')
        self.set_header('Expires', '0')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Content-Disposition', 'attachment; filename='
                        '%s.csv' % filename)
        self.write(text)
        self.finish()
