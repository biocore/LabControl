# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError

from labman.gui.handlers.base import BaseHandler
from labman.db.composition import PoolComposition
from labman.db.exceptions import LabmanUnknownIdError


class PoolListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('pool_list.html')


class PoolListHandler(BaseHandler):
    @authenticated
    def get(self):
        res = {"data": [[p['pooling_process_id'], p['pool_composition_id'],
                         p['external_id']]
                        for p in PoolComposition.list_pools()]}
        self.write(res)


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
