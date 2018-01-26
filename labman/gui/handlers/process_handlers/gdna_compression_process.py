# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.process import GDNAPlateCompressionProcess
from labman.db.plate import Plate
from labman.db.equipment import Equipment
from labman.db.exceptions import LabmanUnknownIdError


class GDNAPlateCompressionProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        plate_name = None
        robot = None
        gdna_plates = []
        if process_id is not None:
            try:
                process = GDNAPlateCompressionProcess(process_id)
            except LabmanUnknownIdError:
                raise HTTPError(404, reason="Compression process %s doesn't "
                                            "exist" % process_id)
            plate_name = process.plates[0].external_id
            robot = process.robot.id
            gdna_plates = [p.id for p in process.gdna_plates]
        robots = Equipment.list_equipment('EpMotion')
        self.render('compression.html', plate_ids=plate_ids, robots=robots,
                    plate_name=plate_name, robot=robot,
                    gdna_plates=gdna_plates, process_id=process_id)

    @authenticated
    def post(self):
        plates = self.get_argument('plates')
        plate_ext_id = self.get_argument('plate_ext_id')
        robot = self.get_argument('robot')

        plates = [Plate(pid) for pid in json_decode(plates)]

        process = GDNAPlateCompressionProcess.create(
            self.current_user, plates, plate_ext_id, Equipment(robot))

        self.write({'process': process.id})
