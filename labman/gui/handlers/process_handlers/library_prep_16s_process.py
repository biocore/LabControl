# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import date

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
        process_id = self.get_argument('process_id', None)
        plates_info = {}
        if process_id is not None:
            process = LibraryPrep16SProcess(process_id)
            plates_info = process.plates_info
            for pinfo in plates_info:
                for key in ['Plate', 'EpMotion', 'EpMotion TM300',
                            'EpMotion TM50', 'Primer Plate']:
                    pinfo[key] = pinfo[key].id
                for key in ['Master mix', 'Water lot']:
                    pinfo[key] = pinfo[key].external_lot_id
        robots = Equipment.list_equipment('EpMotion')
        tools_tm300_8 = Equipment.list_equipment(
            'tm 300 8 channel pipette head')
        tools_tm50_8 = Equipment.list_equipment('tm 50 8 channel pipette head')
        primer_plates = Plate.list_plates('primer')
        self.render('library_prep_16S.html', plate_ids=plate_ids,
                    robots=robots, tools_tm300_8=tools_tm300_8,
                    tools_tm50_8=tools_tm50_8, primer_plates=primer_plates,
                    process_id=process_id, plates_info=plates_info)

    @authenticated
    def post(self):
        plates_info = self.get_argument('plates_info')
        volume = self.get_argument('volume')
        preparation_date = self.get_argument('preparation_date')

        month, day, year = map(int, preparation_date.split('/'))
        preparation_date = date(year, month, day)

        plates_info = [
            (Plate(pid), pn, Plate(pp), Equipment(ep), Equipment(ep300),
             Equipment(ep50), ReagentComposition.from_external_id(mm),
             ReagentComposition.from_external_id(w))
            for pid, pn, pp, ep, ep300, ep50, mm, w in json_decode(plates_info)
        ]

        process = LibraryPrep16SProcess.create(
            self.current_user, plates_info, volume,
            preparation_date=preparation_date)

        self.write({'process': process.id})
