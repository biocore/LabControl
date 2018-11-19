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
from labman.db.composition import ReagentComposition
from labman.db.process import ReagentCreationProcess


class ReagentCompositionListHandler(BaseHandler):
    @authenticated
    def get(self):
        reagent_type = self.get_argument('reagent_type', None)
        term = self.get_argument('term', None)

        self.write(json_encode(ReagentComposition.list_reagents(
            reagent_type=reagent_type, term=term)))

    @authenticated
    def post(self):
        external_id = self.get_argument('external_id')
        volume = self.get_argument('volume')
        reagent_type = self.get_argument('reagent_type')

        process = ReagentCreationProcess.create(
            self.current_user, external_id, volume, reagent_type)
        self.write({'process': process.id})
