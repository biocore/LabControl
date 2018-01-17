# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler
from labman.db.process import NormalizationProcess
from labman.db.composition import ReagentComposition
from labman.db.plate import Plate


class NormalizationProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id')

        self.render('normalization.html', plateIds=[plate_id])

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

        qprocess = Plate(plate_id).quantification_process

        process = NormalizationProcess.create(
            user, qprocess, ReagentComposition.from_external_id(water),
            plate_name, total_vol=float(total_vol), ng=float(ng),
            min_vol=float(min_vol), max_vol=float(max_vol),
            resolution=float(resolution), reformat=reformat)

        self.write({'process': process.id})
