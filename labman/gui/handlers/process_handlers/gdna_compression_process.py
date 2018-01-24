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
from labman.db.exceptions import LabmanUnknownIdError


class GDNAPlateCompressionProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)

        if process_id is not None:
            # bail if a process id and a plate id is specified
            if plate_ids:
                self.set_status(400)
                self.finish()
                return

            try:
                process = GDNAPlateCompressionProcess(process_id)
            except LabmanUnknownIdError:
                self.set_status(404)
                self.finish()
                return

            plate_ids = [plate.id for plate in process.plates]

        self.render('compression.html', plate_ids=plate_ids,
                    process_id=process_id)

    @authenticated
    def post(self):
        plates = self.get_argument('plates')
        plate_ext_id = self.get_argument('plate_ext_id')

        plates = [Plate(pid) for pid in json_decode(plates)]

        process = GDNAPlateCompressionProcess.create(
            self.current_user, plates, plate_ext_id)

        self.write({'process': process.id})
