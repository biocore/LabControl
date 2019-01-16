# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.composition import PoolComposition
from labcontrol.db.exceptions import LabmanUnknownIdError


class PoolListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('pool_list.html')


class PoolListHandler(BaseHandler):
    @authenticated
    def get(self):
        res = {"data": [
            [p.id, p.container.external_id, p.is_plate_pool,
             p.upstream_process.id, ]
            for p in PoolComposition.get_pools()
        ]}
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
