# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import date

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler
from labman.db.process import GDNAExtractionProcess
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition
from labman.db.plate import Plate
from labman.db.exceptions import LabmanUnknownIdError


class GDNAExtractionProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        kingfisher = None
        epmotion = None
        epmotion_tool = None
        extraction_kit = None
        sample_plate = None
        externally_extracted = False
        volume = None
        ext_date = None
        notes = None
        if process_id is not None:
            try:
                process = GDNAExtractionProcess(process_id)
            except LabmanUnknownIdError:
                raise HTTPError(
                    404, reason="Extraction process %s doesn't exist"
                                % process_id)
            kingfisher = process.kingfisher.id
            epmotion = process.epmotion.id
            epmotion_tool = process.epmotion_tool.id
            extraction_kit = process.extraction_kit.external_lot_id
            sample_plate = process.sample_plate.id
            externally_extracted = process.externally_extracted
            volume = process.volume
            ext_date = process.date.strftime('%Y/%m/%d')
            notes = process.notes

        ep_robots = Equipment.list_equipment('EpMotion')
        kf_robots = Equipment.list_equipment('King Fisher')
        tools = Equipment.list_equipment('tm 1000 8 channel pipette head')
        self.render('extraction.html', plate_ids=plate_ids,
                    kf_robots=kf_robots, ep_robots=ep_robots,
                    tools=tools, process_id=process_id,
                    kingfisher=kingfisher, epmotion=epmotion,
                    epmotion_tool=epmotion_tool, extraction_kit=extraction_kit,
                    sample_plate=sample_plate,
                    externally_extracted=externally_extracted,
                    volume=volume, extraction_date=ext_date, notes=notes)

    @authenticated
    def post(self):
        plates_info = self.get_argument('plates_info')
        extraction_date = self.get_argument('extraction_date')
        volume = self.get_argument('volume')

        month, day, year = map(int, extraction_date.split('/'))
        extraction_date = date(year, month, day)

        # We create one process per plate
        processes = []
        for pid, ee, kf, ep, ept, kit, p_name, nt in json_decode(plates_info):
            # Check whether plate was externally extracted
            if ee is True:
                # find the id of null things
                eq_no = \
                  Equipment.list_equipment('Not applicable')[0]['equipment_id']
                ep = ept = kf = Equipment(eq_no)
                kit = ReagentComposition.from_external_id('Not applicable')
            else:
                kf = Equipment(kf)
                ep = Equipment(ep)
                ept = Equipment(ept)
                kit = ReagentComposition.from_external_id(kit)
            processes.append(GDNAExtractionProcess.create(
                self.current_user, Plate(pid), kf, ep, ept, kit,
                volume, p_name, externally_extracted=ee,
                extraction_date=extraction_date, notes=nt).id)

        self.write({'processes': processes})
