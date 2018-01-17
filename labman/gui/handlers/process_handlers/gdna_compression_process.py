# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.process import GDNACompressionProcess
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition
from labman.db.plate import Plate


class GDNACompressionProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        self.render('compression.html', plate_ids)

    @authenticated
    def post(self):

        plates = self.get_argument('plates')
        plates = [Plate(pid) for pid in json_decode(plates)]
        plate_name = self.get_argument('plate_name')
        process = GDNACompressionProcess.create(
            self.current_user, plates,
            plate_name
            )

        self.write({'process': process.id})
