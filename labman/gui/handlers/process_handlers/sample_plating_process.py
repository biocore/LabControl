# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError

from labman.gui.handlers.base import BaseHandler
from labman.db.process import SamplePlatingProcess
from labman.db.plate import PlateConfiguration


class SamplePlatingProcessListHandler(BaseHandler):
    @authenticated
    def post(self):
        user = self.current_user
        plate_config_id = self.get_argument('plate_configuration')
        plate_ext_id = self.get_argument('plate_name')
        volume = self.get_argument('volume')

        spp = SamplePlatingProcess.create(
            user, PlateConfiguration(plate_config_id), plate_ext_id, volume)

        self.write({'plate_id': spp.plate.id, 'process_id': spp.id})
