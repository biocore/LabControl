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
from labman.db.equipment import Equipment
from labman.db.plate import Plate
from labman.db.process import LibraryPrep16SProcess
from labman.db.composition import ReagentComposition


class LibraryPrep16SProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        robots = Equipment.list_equipment('EpMotion')
        tools_tm300_8 = Equipment.list_equipment(
            'tm 300 8 channel pipette head')
        tools_tm50_8 = Equipment.list_equipment('tm 50 8 channel pipette head')
        primer_plates = Plate.list_plates('primer')
        self.render('library_prep_16S.html', plate_ids=plate_ids,
                    robots=robots, tools_tm300_8=tools_tm300_8,
                    tools_tm50_8=tools_tm50_8, primer_plates=primer_plates)

    @authenticated
    def post(self):
        master_mix = self.get_argument('master_mix')
        water = self.get_argument('water')
        robot = self.get_argument('robot')
        tm300_8_tool = self.get_argument('tm300_8_tool')
        tm50_8_tool = self.get_argument('tm50_8_tool')
        volume = self.get_argument('volume')
        plates = self.get_argument('plates')

        plates = [(Plate(pid), Plate(ppid))
                  for pid, ppid in json_decode(plates)]

        process = LibraryPrep16SProcess.create(
            self.current_user, ReagentComposition.from_external_id(master_mix),
            ReagentComposition.from_external_id(water), Equipment(robot),
            Equipment(tm300_8_tool), Equipment(tm50_8_tool), volume,
            plates)

        self.write({'process': process.id})
