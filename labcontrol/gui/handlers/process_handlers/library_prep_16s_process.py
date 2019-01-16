# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import date

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from labcontrol.gui.handlers.base import BaseHandler
from labcontrol.db.equipment import Equipment
from labcontrol.db.plate import Plate
from labcontrol.db.process import LibraryPrep16SProcess
from labcontrol.db.composition import ReagentComposition
from labcontrol.db.exceptions import LabmanUnknownIdError


class LibraryPrep16SProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        gdna_plate = None
        epmotion = None
        epmotion_tm300 = None
        epmotion_tm50 = None
        primer_plate = None
        master_mix = None
        water_lot = None
        volume = None
        prep_date = None
        if process_id is not None:
            try:
                process = LibraryPrep16SProcess(process_id)
            except LabmanUnknownIdError:
                raise HTTPError(404, reason="Amplicon process %s doesn't exist"
                                            % process_id)
            gdna_plate = process.gdna_plate.id
            epmotion = process.epmotion.id
            epmotion_tm300 = process.epmotion_tm300_tool.id
            epmotion_tm50 = process.epmotion_tm50_tool.id
            master_mix = process.mastermix.external_lot_id
            water_lot = process.water_lot.external_lot_id
            primer_plate = process.primer_plate.id
            volume = process.volume
            prep_date = process.date.strftime(process.get_date_format())

        robots = Equipment.list_equipment('EpMotion')
        tools_tm300_8 = Equipment.list_equipment(
            'tm 300 8 channel pipette head')
        tools_tm50_8 = Equipment.list_equipment('tm 50 8 channel pipette head')
        primer_plates = Plate.list_plates(['primer'])
        self.render('library_prep_16S.html', plate_ids=plate_ids,
                    robots=robots, tools_tm300_8=tools_tm300_8,
                    tools_tm50_8=tools_tm50_8, primer_plates=primer_plates,
                    process_id=process_id, gdna_plate=gdna_plate,
                    epmotion=epmotion, epmotion_tm300=epmotion_tm300,
                    epmotion_tm50=epmotion_tm50, master_mix=master_mix,
                    water_lot=water_lot, primer_plate=primer_plate,
                    preparationDate=prep_date, volume=volume)

    @authenticated
    def post(self):
        plates_info = self.get_argument('plates_info')
        volume = self.get_argument('volume')
        preparation_date = self.get_argument('preparation_date')

        month, day, year = map(int, preparation_date.split('/'))
        preparation_date = date(year, month, day)

        processes = [
            LibraryPrep16SProcess.create(
                self.current_user, Plate(pid), Plate(pp), pn, Equipment(ep),
                Equipment(ep300), Equipment(ep50),
                ReagentComposition.from_external_id(mm),
                ReagentComposition.from_external_id(w),
                volume, preparation_date=preparation_date).id
            for pid, pn, pp, ep, ep300, ep50, mm, w in json_decode(plates_info)
        ]

        self.write({'processes': processes})
