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
from labman.db.process import GDNAExtractionProcess
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition
from labman.db.plate import Plate


class GDNAExtractionProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        robots = Equipment.list_equipment('EpMotion')
        tools = Equipment.list_equipment('tm 1000 8 channel pipette head')
        self.render('extraction.html', plate_ids=plate_ids, robots=robots,
                    tools=tools)

    @authenticated
    def post(self):
        robot = self.get_argument('robot')
        tool = self.get_argument('tool')
        kit = self.get_argument('kit')
        plates = self.get_argument('plates')
        volume = self.get_argument('volume')

        plates = [Plate(pid) for pid in json_decode(plates)]

        process = GDNAExtractionProcess.create(
            self.current_user, Equipment(robot), Equipment(tool),
            ReagentComposition.from_external_id(kit), plates, volume)

        self.write({'process': process.id})
