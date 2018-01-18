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
        ep_robots = Equipment.list_equipment('EpMotion')
        kf_robots = Equipment.list_equipment('King Fisher')
        tools = Equipment.list_equipment('tm 1000 8 channel pipette head')
        self.render('extraction.html', plate_ids=plate_ids,
                    kf_robots=kf_robots, ep_robots=ep_robots,
                    tools=tools)

    @authenticated
    def post(self):
        plates_info = self.get_argument('plates_info')
        volume = self.get_argument('volume')

        plates_info = [
            (Plate(pid), Equipment(kf), Equipment(ep), Equipment(ept),
             ReagentComposition.from_external_id(kit), p_name)
            for pid, kf, ep, ept, kit, p_name in json_decode(plates_info)]

        process = GDNAExtractionProcess.create(
            self.current_user, plates_info, volume)

        self.write({'process': process.id})
