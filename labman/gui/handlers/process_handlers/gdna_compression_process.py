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
from labman.db.process import GDNAPlateCompressionProcess
from labman.db.plate import Plate


class GDNAPlateCompressionProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        self.render('compression.html', plate_ids=plate_ids)

    @authenticated
    def post(self):
        plates = self.get_argument('plates')
        plate_ext_id = self.get_argument('plate_ext_id')

        plates = [Plate(pid) for pid in json_decode(plates)]

        process = GDNAPlateCompressionProcess.create(
            self.current_user, plates, plate_ext_id)

        self.write({'process': process.id})
