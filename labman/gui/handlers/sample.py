# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_encode

from labman.gui.handlers.base import BaseHandler


class ControlSamplesHandler(BaseHandler):
    @authenticated
    def get(self):
        # TODO: Get the sample controls from the DB
        def get_control_samples(term=None):
            """Placeholder for the actual BD call"""
            control_samples = ['BLANK', 'VIBRIO', 'MOCK1']
            if term is not None:
                control_samples = [cs for cs in control_samples if term in cs]
            return control_samples
        term = self.get_argument('term', None)
        self.write(json_encode(get_control_samples(term)))
        self.finish()
