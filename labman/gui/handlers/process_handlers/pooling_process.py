# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler
from labman.db import PoolingProcess


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

# Created base method to not duplicate code for running pooling calculation
# There might be a better way. 
class LibraryPoolBaseHandler(BaseHandler):
    def calculate_pools(self, plate_ids):
        # import pooling functions
        pool_funcs = {'eq vol':
                         PoolingProcess._compute_shotgun_pooling_values_eqvol,
                      'min vol':
                         PoolingProcess._compute_shotgun_pooling_values_minvol}

        # get pooling parameters used, depending on function chosen
        pool_params = {}
        if pool_f == 'eq vol':
            pool_params['vol'] = self.get_argument('vol')
        elif pool_f == 'min vol':
            pool_params['min_vol'] = self.get_argument('min vol')
            pool_params['floor_vol'] = self.get_argument('floor vol')
            pool_params['total_ng'] = self.get_argument('total_ng')

        plate_pools = {}
        # for each plate chosen, execute pooling
        for each plate_id in plate_ids:
            plate_pools[plate_id] = {}

            plate = some_function_that_returns_plates(plate_id)

            # calculate volumes
            plate_pools[plate_id] =  pool_funcs[pool_f](plate.concentrations, **kwargs)
        
        return(plate_pools)

# Class to actually execute pooling and store in db
class LibraryPoolProcessHandler(LibraryPoolBaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        self.render('library_pooling.html', plate_ids=plate_ids)

    @authenticated
    def post(self):
        plate_ids = json_decode(self.get_argument('plate_ids'))
        pool_f = self.get_argument('pool_algorithm')

        plate_pools = self.calculate_pools(plate_ids)

        for plate_id in plate_ids:
            plate = some_function_that_returns_plates(plate_id)

            # for each plate, store in DB
            plate.PoolingProcess.create(cls, user, quantification_process, pool_name, volume,
               input_compositions, robot=None)


# The LibraryPoolVisualHandler is meant to calculate the results from
# the pooling process and disply for user approval. 
class LibraryPoolVisualHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = json_decode(self.get_argument('plate_ids'))
        pool_f = self.get_argument('pool_algorithm')

        plate_pools = self.calculate_pools(plate_ids)
        
        output_dict = {}
        for plate_id in plate_ids:

            plate = some_function_that_returns_plates(plate_id)

            # get output image
            output_dict[plate_id]['image'] = \
                PoolingProcess._plot_plate_vals(plate_pools[plate_id])

            # get pool estimate
            output_dict[plate_id]['text'] = \
                PoolingProcess._estimate_pool_conc_vol(plate_pools[plate_id],
                                                       plate.concentrations)

        # return (outputs)

        self.write(output_dict)
