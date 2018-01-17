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
from labman.db.process import NormalizationProcess
from labman.db.plate import Plate


class NormalizationProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')
        plate = Plate(plate_id)

        self.render('normalization.html', plate=plate)

    @authenticated
    def post(self):
        user = self.current_user
        plate_id = self.get_argument('plate_id')
        water = self.get_argument('water')
        plate_name = self.get_argument('plate_name')
        total_vol = self.get_argument('total_vol')
        ng = self.get_argument('ng')
        min_vol = self.get_argument('min_vol')
        max_vol = self.get_argument('max_vol')
        resolution = self.get_argument('resolution')
        reformat = self.get_argument('reformat')

        quant_process = Plate(plate_id).quant_process

        process = NormalizationProcess(
            user, quant_process, water, plate_name, total_vol=total_vol,
            ng=ng, min_vol=min_vol, max_vol=max_vol, resolution=resolution,
            reformat=reformat)

        # NormalizationProcess(user, quant_process, water, plate_name, total_vol=3500,
        #           ng=5, min_vol=2.5, max_vol=3500, resolution=2.5,
        #           reformat=False)

        self.write({'process': process.id})
