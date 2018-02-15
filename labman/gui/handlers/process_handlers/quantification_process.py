# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_decode

import numpy as np

from labman.gui.handlers.base import BaseHandler
from labman.db.plate import Plate
from labman.db.process import QuantificationProcess
from labman.db.composition import (LibraryPrepShotgunComposition,
                                   LibraryPrep16SComposition)


class QuantificationProcessParseHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        self.render('parse_quantification.html', plate_ids=plate_ids)

    @authenticated
    def post(self):
        # We will receive as many files as plates the user has selected
        # The key of the self.request.files dictionary is of the form
        # plate-file-<PLATE_ID> so use the keys to know the plates
        # that we need to quantify
        plates = []
        for key in self.request.files:
            plate_id = key.rsplit('-', 1)[1]
            # The 0 is because for each key we have a single file
            file_content = self.request.files[key][0]['body'].decode('utf-8')
            plate = Plate(plate_id)
            pc = plate.plate_configuration
            concentrations = QuantificationProcess.parse(
                file_content, rows=pc.num_rows, cols=pc.num_columns)

            names = np.empty_like(plate.layout, dtype='object')
            blanks = np.zeros_like(plate.layout, dtype=bool)

            # fetch the sample names and whether or not the samples are blanks
            # by default these are set to be None and False.
            for i, full_row in enumerate(plate.layout):
                for j, well in enumerate(full_row):

                    # some wells have no compositions at all so skip those
                    if well is None:
                        continue
                    comp = well.composition

                    # cache the sample compositions to avoid extra intermediate
                    # queries
                    if isinstance(comp, LibraryPrep16SComposition):
                        smp = comp.gdna_composition.sample_composition

                        blanks[i][j] = smp.sample_composition_type == 'blank'
                        names[i][j] = smp.sample_id
                    elif isinstance(comp, LibraryPrepShotgunComposition):
                        smp = comp.normalized_gdna_composition\
                            .compressed_gdna_composition.gdna_composition\
                            .sample_composition

                        blanks[i][j] = smp.sample_composition_type == 'blank'
                        names[i][j] = smp.sample_id
                    else:
                        raise ValueError('This composition type is not '
                                         'supported')

            plates.append({'plate_name': plate.external_id,
                           'plate_id': plate_id,
                           'concentrations': concentrations.tolist(),
                           'names': names.tolist(),
                           'blanks': blanks.tolist(),
                           'type': plate.process._process_type
                           })

        self.render('quantification.html', plates=plates)


class QuantificationProcessHandler(BaseHandler):
    @authenticated
    def post(self):
        plates_info = json_decode(self.get_argument('plates-info'))
        processes = []
        for pinfo in plates_info:
            plate = Plate(pinfo['plate_id'])
            concentrations = np.asarray(pinfo['concentrations'])

            processes.append(QuantificationProcess.create(
                self.current_user, plate, concentrations).id)

        self.write({'processes': processes})
