# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated

from labman.gui.handlers.base import BaseHandler
from labman.db.plate import Plate
from labman.db.process import LibraryPrepShotgunProcess
from labman.db.composition import ReagentComposition


class LibraryPrepShotgunProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        primer_plates = Plate.list_plates('primer')
        self.render('library_prep_shotgun.html', plate_ids=plate_ids,
                    primer_plates=primer_plates)

    @authenticated
    def post(self):
        plate_name = self.get_argument('plate_name')
        volume = self.get_argument('volume')
        plate = self.get_argument('plate')
        i5_plate = self.get_argument('i5_plate')
        i7_plate = self.get_argument('i7_plate')
        kappa_hyper_plus_kit = self.get_argument('kappa_hyper_plus_kit')
        stub_lot = self.get_argument('stub_lot')

        process = LibraryPrepShotgunProcess.create(
            self.current_user, Plate(plate), plate_name,
            ReagentComposition.from_external_id(kappa_hyper_plus_kit),
            ReagentComposition.from_external_id(stub_lot), volume,
            Plate(i5_plate), Plate(i7_plate))

        self.write({'process': process.id})
