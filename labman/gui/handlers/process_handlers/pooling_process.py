# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler
from labman.db.process import PoolingProcess
from labman.db.plate import Plate
from labman.db.equipment import Equipment

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


POOL_FUNCS = {'eq vol':
                 PoolingProcess.compute_shotgun_pooling_values_eqvol,
              'min vol':
                 PoolingProcess.compute_shotgun_pooling_values_minvol}


def get_pool_params(obj):
    # get pooling parameters used, depending on function chosen
    pool_f = obj.get_argument('pool_f')
    if pool_f not in POOL_FUNCS:
        raise ValueError("Unknown pool function: %s" % str(pool_f))

    pool_params = {}
    if pool_f == 'eq vol':
        pool_params['vol'] = obj.get_argument('vol')
    elif pool_f == 'min vol':
        pool_params['min_vol'] = obj.get_argument('min vol')
        pool_params['floor_vol'] = obj.get_argument('floor vol')
        pool_params['total_ng'] = obj.get_argument('total_ng')
    else:
        raise ValueError("Unknown pool function: %s" % str(pool_f))

    return pool_f, pool_params


# function to calculate pools based on provided function
def calculate_pools(plate_ids, pool_func, pool_args):
    plate_pools = {}
    pool_f = POOL_FUNCS[pool_func]

    # for each plate chosen, execute pooling
    for plate_id in plate_ids:

        plate = Plate(plate_id)

        concs = plate.quantification_process.concentrations
        conc_objs = [x for (x, _, _) in concs]

        # can get conc_obj[i].row and conc_obj[i].column
        # use to construct 2D array for conc_vals

        conc_vals = [y for (_, _, y) in concs]

        # calculate volumes
        pool_vols = pool_f(conc_vals, **pool_args)

        plate_pools[plate_id] =  (conc_objs, conc_vals, pool_vols)

    return(plate_pools)


# quick function to create 2D representation of well-associated numbers
def make_2D_array(wells, vals):
    val_array = np.zeros_like(x.layout, dtype=float) + np.nan

    for well, val in zip(wells, vals):
        val_array[well.row - 1, well.column - 1] = val

    return(val_array)


# function to calculate estimated molar fraction for each element of pool
def calc_pool_pcts(conc_vals, pool_vols):
    amts = [x * y for x, y in zip(conc_vals, pool_vols)]

    total = np.sum(amt)

    pcts = [(z / total) for z in amts]

    return(pcts)

# Class to actually execute pooling and store in db
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


# The LibraryPoolVisualHandler is meant to calculate the results from
# the pooling process and disply for user approval. 
class LibraryPoolVisualHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = json_decode(self.get_argument('plate_ids'))
                
        pool_f, pool_params = get_pool_params(self)
        plate_pools = calculate_pools(plate_ids, pool_f, pool_params)
        
        output_dict = {}
        for plate_id in plate_ids:

            # get pooling results for each plate
            wells, conc_vals, pool_vols = plate_pools[plate_id]

            # make 2D array for visualization
            pool_array = make_2D_array(wells, pool_vols)

            # # get output image
            # output_dict[plate_id]['image'] = \
            #     PoolingProcess._plot_plate_vals(pool_array)

            # get pool total molarity estimate
            output_dict[plate_id]['text'] = \
                PoolingProcess.estimate_pool_conc_vol(pool_vols, conc_vals)

        # return (outputs)
        self.write(output_dict)
