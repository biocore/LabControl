# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import datetime

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode, json_encode
import numpy as np

from labcontrol.gui.handlers.base import BaseHandler, BaseDownloadHandler
from labcontrol.db.process import PoolingProcess, QuantificationProcess
from labcontrol.db.plate import Plate
from labcontrol.db.equipment import Equipment
from labcontrol.db.composition import (PoolComposition, LibraryPrep16SComposition,
                                   LibraryPrepShotgunComposition)
from labcontrol.db.exceptions import LabControlUnknownIdError

import logging

POOL_FUNCS = {
    'equal': {'function': PoolingProcess.compute_pooling_values_eqvol,
              'parameters': [('total_vol', 'volume-'),
                             ('size', 'lib-size-'),
                             ('robot', 'robot-'),
                             ('destination', 'dest-tube-'),
                             ('blank_vol', 'blank-vol-'),
                             ('blank_num', 'blank-number-')]},
    'min': {'function': PoolingProcess.compute_pooling_values_minvol,
            'parameters': [('floor_vol', 'floor-vol-'),
                           ('floor_conc', 'floor-conc-'),
                           ('total', 'total-'),
                           ('size', 'lib-size-'),
                           ('robot', 'robot-'),
                           ('destination', 'dest-tube-'),
                           ('blank_vol', 'blank-vol-'),
                           ('blank_num', 'blank-number-')]}}

HTML_POOL_PARAMS_SHOTGUN = {
    'min': [{'prefix': 'floor-vol-', 'value': '100',
             'desc': 'volume for low conc samples (nL):', 'min': '1',
             'step': '1'},
            {'prefix': 'floor-conc-', 'value': '20',
             'desc': 'minimum value for pooling at real estimated value (nM):',
             'min': '0.1', 'step': '0.1'},
            {'prefix': 'total-', 'value': '0.002',
             'desc': 'total number of nM to have in pool (nM):',
             'min': '0.00001', 'step': '0.00001'},
            {'prefix': 'lib-size-', 'value': '500',
             'desc': 'Average library molecule size (bp):', 'min': '1',
             'step': '1'},
            {'prefix': 'robot-'}, {'prefix': 'dest-tube-'},
            {'prefix': 'blank-number-', 'value': '',
             'desc': 'Pool only highest N blanks, N=', 'min': 0,
             'step': 1},
            {'prefix': 'blank-vol-', 'value': '',
             'desc': 'Pool all blanks at volume (nL):', 'min': 0,
             'step': 2.5}],
    'equal': [{'prefix': 'volume-', 'value': '200',
               'desc': 'volume to pool per sample (nL):', 'min': '1',
               'step': '1'},
              {'prefix': 'lib-size-', 'value': '500',
               'desc': 'Average library molecule size (bp):', 'min': '1',
               'step': '1'},
              {'prefix': 'robot-'}, {'prefix': 'dest-tube-'},
              {'prefix': 'blank-number-', 'value': '',
               'desc': 'Pool only highest N blanks, N=', 'min': 0,
               'step': 1},
              {'prefix': 'blank-vol-', 'value': '',
               'desc': 'Pool all blanks at volume (nL):', 'min': 0,
               'step': 2.5}]}

HTML_POOL_PARAMS_16S = {
    'min': [{'prefix': 'floor-vol-', 'value': '2',
             'desc': 'volume for low conc samples (µL):', 'min': '1',
             'step': '1'},
            {'prefix': 'floor-conc-', 'value': '16',
             'desc': 'minimum value for pooling at real estimated value '
                     '(ng/µL):',
             'min': '0.1', 'step': '0.1'},
            {'prefix': 'total-', 'value': '240',
             'desc': 'total quantity of DNA to pool per sample (ng):',
             'min': '1', 'step': '0.1'},
            {'prefix': 'lib-size-', 'value': '390',
             'desc': 'Average library molecule size (bp):', 'min': '1',
             'step': '1'},
            {'prefix': 'robot-'}, {'prefix': 'dest-tube-'},
            {'prefix': 'blank-number-', 'value': 2,
             'desc': 'Pool only highest N blanks, N=', 'min': 0,
             'step': 1},
            {'prefix': 'blank-vol-', 'value': 5,
             'desc': 'Pool all blanks at volume (µL):', 'min': 0,
             'step': 0.1}],
    'equal': [{'prefix': 'volume-', 'value': '5',
               'desc': 'volume to pool per sample (µL):', 'min': '1',
               'step': '1'},
              {'prefix': 'lib-size-', 'value': '390',
               'desc': 'Average library molecule size (bp):', 'min': '1',
               'step': '1'},
              {'prefix': 'robot-'}, {'prefix': 'dest-tube-'},
              {'prefix': 'blank-number-', 'value': 2,
               'desc': 'Pool only highest N blanks, N=', 'min': 0,
               'step': 1},
              {'prefix': 'blank-vol-', 'value': 5,
               'desc': 'Pool all blanks at volume (µL):', 'min': 0,
               'step': 0.1}]}

HTML_POOL_PARAMS = {'16S library prep': HTML_POOL_PARAMS_16S,
                    'shotgun library prep': HTML_POOL_PARAMS_SHOTGUN}

PLATE_TYPES = {LibraryPrep16SComposition: '16S library prep',
               LibraryPrepShotgunComposition: 'shotgun library prep'}

PLATE_TYPE_TO_POOL_TYPE = {'16S library prep': 'amplicon_sequencing',
                           'shotgun library prep': 'shotgun_plate'}

POOL_TYPE_TO_PLATE_TYPE = {value: key for key, value in
                           PLATE_TYPE_TO_POOL_TYPE.items()}

POOL_TYPE_PARAMS = {
    'amplicon_sequencing': {'abbreviation': 'amplicon',
                            'template': 'library_pooling_16S.html'},
    'shotgun_plate': {'abbreviation': 'shotgun',
                      'template': 'library_pooling_shotgun.html'}}


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
    (np.array, np.array, np.array, np.array)
        Four 2D np.arrays containing the raw concentration values, the
        the computed concentration values, a boolean array indicating whether
        each well is a blank, and an array of str with the name of the sample
        in each well.
    """
    layout = plate.layout
    raw_concs = np.zeros_like(layout, dtype=float)
    comp_concs = np.zeros_like(layout, dtype=float)
    comp_is_blank = np.zeros_like(layout, dtype=bool)
    plate_names = np.empty_like(layout, dtype='object')
    for comp, raw_conc, conc in quant_process.concentrations:
        well = comp.container
        row = well.row - 1
        column = well.column - 1
        raw_concs[row][column] = raw_conc
        comp_concs[row][column] = conc

        # cache the sample compositions to avoid extra intermediate queries
        if isinstance(comp, LibraryPrep16SComposition):
            smp = comp.gdna_composition.sample_composition

            comp_is_blank[row][column] = smp.sample_composition_type == 'blank'
            plate_names[row][column] = smp.sample_id
        elif isinstance(comp, LibraryPrepShotgunComposition):
            smp = comp.normalized_gdna_composition \
                .compressed_gdna_composition\
                .gdna_composition.sample_composition

            comp_is_blank[row][column] = smp.sample_composition_type == 'blank'
            plate_names[row][column] = smp.sample_id

    return raw_concs, comp_concs, comp_is_blank, plate_names


class BasePoolHandler(BaseHandler):
    def _compute_pools(self, plate_info):
        self.plate_id = plate_info['plate-id']
        self.func_name = plate_info['pool-func']
        self.plate_type = plate_info['plate-type']
        self.quant_process_id = plate_info['quant-process-id']
        func_info = POOL_FUNCS[self.func_name]
        self.function = func_info['function']

        plate = Plate(self.plate_id)
        quant_process = QuantificationProcess(self.quant_process_id)

        # make params dictionary for function
        params = {}
        for arg, pfx in func_info['parameters']:
            param_key = '%s%s' % (pfx, self.plate_id)
            if param_key not in plate_info:
                raise HTTPError(
                    400, reason='Missing parameter %s' % param_key)
            # empty strings are sent when we have disabled inputs.
            # we are testing for them explicitly where expected.
            if plate_info[param_key] != '':
                params[arg] = float(plate_info[param_key])
            else:
                params[arg] = plate_info[param_key]

        self.params = params

        # compute molar concentrations
        quant_process.compute_concentrations(size=params['size'])

        # calculate pooled values
        self.raw_concs, self.comp_concs, self.comp_blanks, \
        self.plate_names = make_2D_arrays(plate, quant_process)


class PoolPoolProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        pool_ids = self.get_arguments('pool_id')
        process_id = self.get_argument('process_id', None)
        pool_comp_info = None
        pool_name = None
        if process_id is not None:
            try:
                process = PoolingProcess(process_id)
            except LabControlUnknownIdError:
                raise HTTPError(404, reason="Pooling process %s doesn't exist"
                                            % process_id)
            pool_comp_info = [[p.id, p.raw_concentration]
                              for p, _ in process.components]
            pool_name = process.pool.container.external_id
        self.render('pool_pooling.html', pool_ids=pool_ids,
                    process_id=process_id, pool_comp_info=pool_comp_info,
                    pool_name=pool_name)

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
        # Create the pool - Magic number 5 - > the volume for this pooling
        # is always 5 according to the wet lab.
        p_process = PoolingProcess.create(
            self.current_user, q_process, pool_name, 5, input_compositions,
            {"function": "amplicon_pool", "parameters": {}})
        self.write({'process': p_process.id})


class LibraryPool16SProcessHandler(BasePoolHandler):
    @authenticated
    def get(self):
        pool_type = 'amplicon_sequencing'
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        input_plate = None
        pool_func_data = None
        pool_values = []
        pool_blanks = []
        plate_names = []
        if process_id is not None:
            try:
                process = PoolingProcess(process_id)
            except LabControlUnknownIdError:
                raise HTTPError(404, reason="Pooling process %s doesn't exist"
                                            % process_id)
            plate = process.components[0][0].container.plate
            input_plate = plate.id
            pool_func_data = process.pooling_function_data
            content_type = type(plate.get_well(1, 1).composition)
            id_plate_type = PLATE_TYPES[content_type]
            plate_type_mapped = PLATE_TYPE_TO_POOL_TYPE[id_plate_type]
            if plate_type_mapped != pool_type:
                raise HTTPError(400, reason='Pooling process type does not '
                                            'match pooling type')

            _, pool_values, pool_blanks, plate_names = \
                make_2D_arrays(plate, process.quantification_process)

            pool_values = pool_values.tolist()
            pool_blanks = pool_blanks.tolist()
            plate_names = plate_names.tolist()

        elif len(plate_ids) > 0:
            content_types = {type(Plate(pid).get_well(1, 1).composition)
                             for pid in plate_ids}

            if len(content_types) > 1:
                raise HTTPError(400, reason='Plates contain different types '
                                            'of compositions')

            # check if the observed plates are the same type as the pooling
            # type (i.e., no shotgun plates for 16S pooling)
            content_type = content_types.pop()
            id_plate_type = PLATE_TYPES[content_type]
            plate_type_mapped = PLATE_TYPE_TO_POOL_TYPE[id_plate_type]
            if plate_type_mapped != pool_type:
                raise HTTPError(400, reason='Plate type does not match '
                                            'pooling type')

        pool_type_stripped = POOL_TYPE_PARAMS[pool_type]['abbreviation']
        plate_type = POOL_TYPE_TO_PLATE_TYPE[pool_type]

        robots = (Equipment.list_equipment('EpMotion') +
                  Equipment.list_equipment('echo'))

        template = POOL_TYPE_PARAMS[pool_type]['template']

        self.render(template, plate_ids=plate_ids,
                    robots=robots, pool_params=HTML_POOL_PARAMS,
                    input_plate=input_plate, pool_func_data=pool_func_data,
                    process_id=process_id, pool_values=pool_values,
                    plate_type=plate_type, pool_blanks=pool_blanks,
                    plate_names=plate_names, pool_type=pool_type_stripped)


    def _compute_pools(self, plate_info):
        super()._compute_pools(plate_info)

        # for 16S, we calculate each sample independently
        self.params['total_each'] = True
        self.params['vol_constant'] = 1
        pool_vals = self.function(self.raw_concs, **self.params)

        # if adjust blank volume, do that
        if self.params['blank_vol'] != '':
            pool_vals = PoolingProcess.adjust_blank_vols(pool_vals,
                                                         self.comp_blanks,
                                                         self.params['blank_vol'])

        # if only pool some blanks, do that
        if self.params['blank_num'] != '':
            pool_vals = PoolingProcess.select_blanks(pool_vals,
                                                     self.raw_concs,
                                                     self.comp_blanks,
                                                     int(self.params['blank_num']))

        # estimate pool volume and concentration
        total_c, total_v = PoolingProcess.estimate_pool_conc_vol(pool_vals,
                                                                 self.comp_concs)

        # store output values
        output = {}
        output['func_data'] = {'function': self.func_name,
                               'parameters': self.params}
        output['raw_vals'] = self.raw_concs
        output['comp_vals'] = self.comp_concs
        output['pool_vals'] = pool_vals
        output['pool_blanks'] = self.comp_blanks.tolist()
        output['plate_names'] = self.plate_names.tolist()
        output['plate_id'] = self.plate_id
        output['destination'] = self.params['destination']
        output['robot'] = self.params['robot']
        output['blank_vol'] = self.params['blank_vol']
        output['blank_num'] = self.params['blank_num']
        output['total_conc'] = total_c
        output['total_vol'] = total_v
        output['quant-process-id'] = self.quant_process_id

        return output

    @authenticated
    def post(self):
        plates_info = json_decode(self.get_argument('plates-info'))
        results = []
        for pinfo in plates_info:

            plate_result = self._compute_pools(pinfo)
            plate = Plate(plate_result['plate_id'])

            # calculate estimated molar fraction for each element of pool
            amts = plate_result['comp_vals'] * plate_result['pool_vals']
            pcts = amts / amts.sum()

            quant_process = QuantificationProcess(
                plate_result['quant-process-id'])
            pool_name = 'Pool from plate %s (%s)' % (
                plate.external_id,
                datetime.now().strftime(quant_process.get_date_format()))
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
                plate_result['func_data'], robot=robot,
                destination=plate_result['destination'])
            results.append({'plate-id': plate.id, 'process-id': process.id})

        self.write(json_encode(results))


class LibraryPoolShotgunProcessHandler(BasePoolHandler):
    @authenticated
    def get(self):
        pool_type = 'shotgun_plate'
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        input_plate = None
        pool_func_data = None
        pool_values = []
        pool_blanks = []
        plate_names = []
        if process_id is not None:
            try:
                process = PoolingProcess(process_id)
            except LabControlUnknownIdError:
                raise HTTPError(404, reason="Pooling process %s doesn't exist"
                                            % process_id)
            plate = process.components[0][0].container.plate
            input_plate = plate.id
            pool_func_data = process.pooling_function_data
            content_type = type(plate.get_well(1, 1).composition)
            id_plate_type = PLATE_TYPES[content_type]
            plate_type_mapped = PLATE_TYPE_TO_POOL_TYPE[id_plate_type]
            if plate_type_mapped != pool_type:
                raise HTTPError(400, reason='Pooling process type does not '
                                            'match pooling type')

            _, pool_values, pool_blanks, plate_names = \
                make_2D_arrays(plate, process.quantification_process)

            pool_values = pool_values.tolist()
            pool_blanks = pool_blanks.tolist()
            plate_names = plate_names.tolist()

        elif len(plate_ids) > 0:
            content_types = {type(Plate(pid).get_well(1, 1).composition)
                             for pid in plate_ids}

            if len(content_types) > 1:
                raise HTTPError(400, reason='Plates contain different types '
                                            'of compositions')

            # check if the observed plates are the same type as the pooling
            # type (i.e., no shotgun plates for 16S pooling)
            content_type = content_types.pop()
            id_plate_type = PLATE_TYPES[content_type]
            plate_type_mapped = PLATE_TYPE_TO_POOL_TYPE[id_plate_type]
            if plate_type_mapped != pool_type:
                raise HTTPError(400, reason='Plate type does not match '
                                            'pooling type')

        pool_type_stripped = POOL_TYPE_PARAMS[pool_type]['abbreviation']
        plate_type = POOL_TYPE_TO_PLATE_TYPE[pool_type]

        robots = (Equipment.list_equipment('EpMotion') +
                  Equipment.list_equipment('echo'))

        template = POOL_TYPE_PARAMS[pool_type]['template']

        self.render(template, plate_ids=plate_ids,
                    robots=robots, pool_params=HTML_POOL_PARAMS,
                    input_plate=input_plate, pool_func_data=pool_func_data,
                    process_id=process_id, pool_values=pool_values,
                    plate_type=plate_type, pool_blanks=pool_blanks,
                    plate_names=plate_names, pool_type=pool_type_stripped)

    def _compute_pools(self, plate_info):
        super()._compute_pools(plate_info)

        self.params['total_each'] = False
        self.params['vol_constant'] = 10 ** 9
        pool_vals = self.function(self.raw_concs, **self.params)

        # if adjust blank volume, do that
        if self.params['blank_vol'] != '':
            bv = self.params['blank_vol']
            pool_vals = PoolingProcess.adjust_blank_vols(pool_vals,
                                                         self.comp_blanks,
                                                         bv)

        # if only pool some blanks, do that
        if self.params['blank_num'] != '':
            bn = int(self.params['blank_num'])
            pool_vals = PoolingProcess.select_blanks(pool_vals,
                                                     self.raw_concs,
                                                     self.comp_blanks,
                                                     bn)

        # estimate pool volume and concentration
        cs = self.comp_concs
        total_c, total_v = PoolingProcess.estimate_pool_conc_vol(pool_vals, cs)

        # store output values
        output = {}
        output['func_data'] = {'function': self.func_name,
                               'parameters': self.params}
        output['raw_vals'] = self.raw_concs
        output['comp_vals'] = self.comp_concs
        output['pool_vals'] = pool_vals
        output['pool_blanks'] = self.comp_blanks.tolist()
        output['plate_names'] = self.plate_names.tolist()
        output['plate_id'] = self.plate_id
        output['destination'] = self.params['destination']
        output['robot'] = self.params['robot']
        output['blank_vol'] = self.params['blank_vol']
        output['blank_num'] = self.params['blank_num']
        output['total_conc'] = total_c
        output['total_vol'] = total_v
        output['quant-process-id'] = self.quant_process_id

        return output

    @authenticated
    def post(self):
        plates_info = json_decode(self.get_argument('plates-info'))
        results = []
        for pinfo in plates_info:

            plate_result = self._compute_pools(pinfo)
            plate = Plate(plate_result['plate_id'])

            # calculate estimated molar fraction for each element of pool
            amts = plate_result['comp_vals'] * plate_result['pool_vals']
            pcts = amts / amts.sum()

            quant_process = QuantificationProcess(
                plate_result['quant-process-id'])
            pool_name = 'Pool from plate %s (%s)' % (
                plate.external_id,
                datetime.now().strftime(quant_process.get_date_format()))
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
                plate_result['func_data'], robot=robot,
                destination=plate_result['destination'])
            results.append({'plate-id': plate.id, 'process-id': process.id})

        self.write(json_encode(results))


# The ComputeLibraryPoolValuesHandler calculates the results from
# the pooling process and display for user approval.
class ComputeLibraryPoolValuesHandler(BasePoolHandler):
    @authenticated
    def post(self):
        plate_info = json_decode(self.get_argument('plate-info'))
        output = self._compute_pools(plate_info)
        # we need to make sure the values are serializable
        output['pool_vals'] = output['pool_vals'].tolist()
        output['pool_blanks'] = output['pool_blanks']
        self.write(output)

    def _compute_pools(self, plate_info):
        super()._compute_pools(plate_info)
        logging.debug(self.params)

        # pool_vals looks like its needed in the output
        pool_vals = self.function(self.raw_concs, **self.params)

        # if adjust blank volume, do that
        if self.params['blank_vol'] != '':
            pool_vals = PoolingProcess.adjust_blank_vols(pool_vals,
                                                         self.comp_blanks,
                                                         self.params['blank_vol'])

        # if only pool some blanks, do that
        if self.params['blank_num'] != '':
            pool_vals = PoolingProcess.select_blanks(pool_vals,
                                                     self.raw_concs,
                                                     self.comp_blanks,
                                                     int(self.params['blank_num']))

        # estimate pool volume and concentration
        total_c, total_v = PoolingProcess.estimate_pool_conc_vol(pool_vals,
                                                                 self.comp_concs)

        # store output values
        output = {}
        output['pool_vals'] = pool_vals
        output['pool_blanks'] = self.comp_blanks.tolist()
        output['plate_names'] = self.plate_names.tolist()
        output['plate_id'] = self.plate_id
        output['destination'] = self.params['destination']
        output['robot'] = self.params['robot']
        output['blank_vol'] = self.params['blank_vol']
        output['blank_num'] = self.params['blank_num']
        output['total_conc'] = total_c
        output['total_vol'] = total_v
        output['quant-process-id'] = self.quant_process_id

        logging.debug(output)
        return output


class DownloadPoolFileHandler(BaseDownloadHandler):
    @authenticated
    def get(self, process_id):
        try:
            process = PoolingProcess(int(process_id))
        except LabControlUnknownIdError:
            raise HTTPError(404, reason='PoolingProcess %s does not exist'
                                        % process_id)
        text = process.generate_pool_file()
        plate_names_set = {x[0].container.plate.external_id for x in
                           process.components}

        # Note that PoolingProcess objects (what `process` is above) definitely
        # *can* validly have components from multiple plates: a user could
        # chose to make a "plate pool" from more than one amplicon library prep
        # plate.  However, as of 10/09/2018, the wet lab apparently currently
        # chooses not to do this, and instead chooses to make one pool per
        # library prep plate.  Given this self-imposed limitation, they expect
        # to be able to have the (one-and-only) library plate name embedded in
        # the name of the resulting normpool file.  This
        # *file naming convention* won't work--or at least, won't work as they
        # expect it to--if there are multiple plates represented in the pool,
        # so if that happens we generate an error below, at the point where the
        #  *file name* is generated.  If they decide they want to allow
        # themselves to make plate pools from multiple plates, all they need to
        # do is decide on a more flexible naming convention, and
        # we can change this naming code and remove this error condition.
        if len(plate_names_set) > 1:
            raise ValueError("Unable to generate normpool file name for pool "
                             "based on more than one plate: " +
                             ", ".join(str(x) for x in plate_names_set))

        plate_name = plate_names_set.pop()
        name_pieces = [plate_name, "normpool"]
        self.deliver_text(name_pieces, process, text, extension="csv")
