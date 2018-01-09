# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler


class PoolProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        pool_ids = self.get_arguments('pool_id')
        self.render('pooling.html', pool_ids=pool_ids)
