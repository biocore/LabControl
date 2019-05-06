# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.util import get_pools_listing
from labcontrol.db.composition import PoolComposition
from labcontrol.db.exceptions import LabControlUnknownIdError


class PoolListingHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render('pool_list.html')


class PoolListHandler(BaseHandler):
    @authenticated
    def get(self, list_type):
        if list_type == "amplicon_plate":
            is_plate_pool_limits = [True]
            is_amplicon_plate_pool_limits = [True]
        elif list_type == "amplicon_sequencing":
            is_plate_pool_limits = [False]
            is_amplicon_plate_pool_limits = [False]
        elif list_type == "metagenomics_plate":
            is_plate_pool_limits = [True]
            is_amplicon_plate_pool_limits = [False]
        elif list_type == "all":
            is_plate_pool_limits = [True, False]
            is_amplicon_plate_pool_limits = [True, False]
        else:
            raise ValueError("Unknown plate list type: {0}".format(list_type))

        res = {"data": get_pools_listing(is_plate_pool_limits,
                                         is_amplicon_plate_pool_limits)}
        self.write(res)


class PoolHandler(BaseHandler):
    @authenticated
    def get(self, pool_id):
        try:
            pool = PoolComposition(int(pool_id))
        except LabControlUnknownIdError:
            raise HTTPError(404, 'Pool %s doesn\'t exist' % pool_id)

        result = {'pool_id': pool.id,
                  'pool_name': pool.container.external_id,
                  'num_components': len(pool.components)}
        self.write(result)
        self.finish()
