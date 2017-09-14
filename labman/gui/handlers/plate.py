# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler


class PlateHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("plate.html")


class PlateNameHandler(BaseHandler):
    @authenticated
    def get(self):
        # TODO: Check on the DB if the plate exist
        def exists(new_name):
            """Placeholder for the actual DB call"""
            if new_name == 'error':
                raise ValueError('Forcing a way to test that the error '
                                 'reporting works as expected')
            return new_name == 'exists'

        new_name = self.get_argument('new-name')
        status = 200 if exists(new_name) else 404
        self.set_status(status)
        self.finish()
