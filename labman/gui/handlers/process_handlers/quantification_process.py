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


class QuantificationProcessParseHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_ids = self.get_arguments('plate_id')
        plates = [[p['plate_id'], p['external_id']]
                  for p in Plate.list_plates('16S library prep')]
        self.render('parse_quantification.html', plate_ids=plate_ids,
                    plates=plates)

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
            plates.append({'plate_name': plate.external_id,
                           'plate_id': plate_id,
                           'concentrations': concentrations.tolist()})

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
