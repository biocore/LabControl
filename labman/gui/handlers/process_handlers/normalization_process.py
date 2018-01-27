# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode, json_encode

from labman.gui.handlers.base import BaseHandler
from labman.db.process import NormalizationProcess
from labman.db.composition import ReagentComposition
from labman.db.plate import Plate
from labman.db.exceptions import LabmanUnknownIdError


class NormalizationProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        water = None
        compressed_plate = None
        func_data = {}
        if process_id is not None:
            try:
                process = NormalizationProcess(process_id)
            except LabmanUnknownIdError:
                raise HTTPError(404, reason="Normalization process %s doesn't "
                                            "exist" % process_id)
            water = process.water_lot.external_lot_id
            func_data = process.normalization_function_data
            compressed_plate = process.compressed_plate.id
        self.render('normalization.html', plate_ids=plate_ids,
                    process_id=process_id, water=water,
                    func_data=json_encode(func_data),
                    compressed_plate=compressed_plate)

    @authenticated
    def post(self):
        user = self.current_user
        plates_info = self.get_argument('plates_info')
        water = self.get_argument('water')
        total_vol = self.get_argument('total_vol')
        ng = self.get_argument('ng')
        min_vol = self.get_argument('min_vol')
        max_vol = self.get_argument('max_vol')
        resolution = self.get_argument('resolution')
        reformat = self.get_argument('reformat')

        processes = [
            [plate_id, NormalizationProcess.create(
                user, Plate(plate_id).quantification_process,
                ReagentComposition.from_external_id(water),
                plate_name, total_vol=float(total_vol), ng=float(ng),
                min_vol=float(min_vol), max_vol=float(max_vol),
                resolution=float(resolution), reformat=reformat).id]
            for plate_id, plate_name in json_decode(plates_info)]

        self.write({'processes': processes})


class DownloadNormalizationProcessHandler(BaseHandler):
    @authenticated
    def get(self, process_id):
        process = NormalizationProcess(int(process_id))
        text = process.generate_echo_picklist()

        self.set_header('Content-Type', 'text/csv')
        self.set_header('Expires', '0')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Content-Disposition', 'attachment; filename='
                        'NormalizationSheet_%s.csv' % process_id)
        self.write(text)
        self.finish()
