# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.composition import PoolComposition
from labman.db.exceptions import LabmanUnknownIdError
from labman.db.process import QuantificationProcess, PoolingProcess


class PoolListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('pool_list.html')


class PoolListHandler(BaseHandler):
    @authenticated
    def get(self):
        res = {"data": [[p['pool_composition_id'], p['external_id']]
                        for p in PoolComposition.list_pools()]}
        self.write(res)

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


class PoolHandler(BaseHandler):
    @authenticated
    def get(self, pool_id):
        try:
            pool = PoolComposition(int(pool_id))
        except LabmanUnknownIdError:
            raise HTTPError(404, 'Pool %s doesn\'t exist' % pool_id)

        result = {'pool_id': pool.id,
                  'pool_name': pool.container.external_id,
                  'num_components': len(pool.components)}
        self.write(result)
        self.finish()
