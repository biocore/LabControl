# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_decode

from labman.gui.handlers.base import BaseHandler, BaseDownloadHandler
from labman.db.plate import Plate
from labman.db.process import LibraryPrepShotgunProcess
from labman.db.composition import ReagentComposition
from labman.db.exceptions import LabmanUnknownIdError


class LibraryPrepShotgunProcessHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        process_id = self.get_argument('process_id', None)
        kappa = None
        stub = None
        volume = None
        norm_plate = None
        i5plate = None
        i7plate = None
        if process_id is not None:
            try:
                process = LibraryPrepShotgunProcess(process_id)
            except LabmanUnknownIdError:
                raise HTTPError(404, reason="Shotgun library prep process %s "
                                            "doesn't exist" % process_id)
            kappa = process.kappa_hyper_plus_kit.external_lot_id
            stub = process.stub_lot.external_lot_id
            norm_plate = process.normalized_plate.id
            i5plate = process.i5_primer_plate.id
            i7plate = process.i7_primer_plate.id
            volume = process.volume

        primer_plates = []
        for pp in Plate.list_plates(['primer']):
            plate = Plate(pp['plate_id'])
            if plate.process.primer_set.target_name == 'Shotgun':
                primer_plates.append(pp)

        self.render('library_prep_shotgun.html', plate_ids=plate_ids,
                    primer_plates=primer_plates, process_id=process_id,
                    kappa=kappa, stub=stub, volume=volume,
                    norm_plate=norm_plate, i5plate=i5plate, i7plate=i7plate)

    @authenticated
    def post(self):
        user = self.current_user
        plates_info = self.get_argument('plates_info')
        volume = self.get_argument('volume')
        kappa_hyper_plus_kit = self.get_argument('kappa_hyper_plus_kit')
        stub_lot = self.get_argument('stub_lot')

        processes = [
            [pid, LibraryPrepShotgunProcess.create(
                user, Plate(pid), plate_name,
                ReagentComposition.from_external_id(kappa_hyper_plus_kit),
                ReagentComposition.from_external_id(stub_lot), volume,
                Plate(i5p), Plate(i7p)).id]
            for pid, plate_name, i5p, i7p in json_decode(plates_info)]

        self.write({'processes': processes})


class DownloadLibraryPrepShotgunProcessHandler(BaseDownloadHandler):
    @authenticated
    def get(self, process_id):
        process = LibraryPrepShotgunProcess(int(process_id))
        text = process.generate_echo_picklist()
        compressed_plate_name = process.normalization_process.compressed_plate\
            .external_id
        name_pieces = [compressed_plate_name, "indices"]
        self.deliver_text(name_pieces, process, text)
