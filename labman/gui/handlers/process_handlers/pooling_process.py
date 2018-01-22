# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode
import numpy as np

from labman.gui.handlers.base import BaseHandler
from labman.db.process import PoolingProcess, QuantificationProcess
from labman.db.plate import Plate
from labman.db.equipment import Equipment
from labman.db.composition import PoolComposition


# quick function to create 2D representation of well-associated numbers
def make_2D_array(wells, vals):
    val_array = np.zeros_like(x.layout, dtype=float) + np.nan

    for well, val in zip(wells, vals):
        val_array[well.row - 1, well.column - 1] = val

    return(val_array)

# function to calculate estimated molar fraction for each element of pool
def calc_pool_pcts(conc_vals, pool_vols):
    amts = [x * y for x, y in zip(conc_vals, pool_vols)]
    total = np.sum(amts)
    pcts = [(z / total) for z in amts]
    return(pcts)


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
                                ('blanks', 'blank-val-')]}}


class LibraryPoolProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        self.render('library_pooling.html', plate_ids=plate_ids)

    @authenticated
    def post(self):
        plate_ids = json_decode(self.get_argument('plate_ids'))
        pool_base_name = self.get_argument('pool_base_name')
        robot = Equipment(self.get_argument('robot'))
        pool_volume = self.get_argument('pool_volume')
        pool_f, pool_params = get_pool_params(self)
        plate_pools = self.calculate_pools(plate_ids, pool_f, pool_params)
        output_dict = {}
        p_processes = []
        for plate_id in plate_ids:
            plate = Plate(plate_id)
            pool_name = '%s_%s'.format(pool_base_name, plate.external_id)
            # get pooling results for each plate
            wells, conc_vals, pool_vols = plate_pools[plate_id]
            # create input molar percentages
            pcts = calc_pool_pcts(conc_vals, pool_vols)
            q_process = plate.quantification_process
            # create input compositions
            comps = [{'composition': c,
                      'input_volume': v,
                      'percentage_of_output': p} for c, v, p in zip(wells,
                                                                    pool_vols,
                                                                    pcts)]
            # create pooling process object for each pooled plate
            p_process = PoolingProcess.create(
                self.current_user, q_process, pool_name,
                pool_volume, comps, robot)
            # append to list of process ids
            p_processes.append(p_process.id)
        self.write({'processes': p_processes})


# The ComputeLibraryPoolValueslHandler is meant to calculate the results from
# the pooling process and disply for user approval.
class ComputeLibraryPoolValueslHandler(BaseHandler):
    @authenticated
    def post(self):
        plate_info = json_decode(self.get_argument('plate-info'))

        plate_id = plate_info['plate-id']
        func_name = plate_info['pool-func']
        func_info = POOL_FUNCS[func_name]
        function = func_info['function']
        params = {arg: plate_info['%s%s' % (pfx, plate_id)]
                  for arg, pfx in func_info['parameters']}

        plate = Plate(plate_id)
        quant_process = plate.quantification_process

        output = {}
        if func_name == 'Amplicon':
            # Amplicon
            # Compute the normalized concentrations
            quant_process.compute_concentrations(**params)
            # Compute the pooling values
            output['pool_vals'] = make_2D_array(plate, quant_process)
        else:
            # Shotgun
            # Compute the normalized concentrations
            size = params.pop('size')
            quant_process.compute_concentrations(size=size)
            # Compute the pooling values
            sample_concs = make_2D_array(plate, quant_process)
            output['pool_vals'] = function(sample_concs, **params)

        self.write(output)
