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
from labman.db.process import QuantificationProcess, PoolingProcess


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
        plate_id = self.get_argument('plate-select')
        # Magic number 0 -> there is only 1 file attached
        file_content = self.request.files[
            'plate-reader-fp'][0]['body'].decode('utf-8')
        concentrations = QuantificationProcess.parse(file_content)
        plate = Plate(plate_id)
        self.render('quantification.html',
                    concentrations=concentrations.tolist(),
                    plate_name=plate.external_id, plate_id=plate.id,
                    plate_conf=plate.plate_configuration.description)


class QuantificationProcessHandler(BaseHandler):
    @authenticated
    def post(self):
        plate_id = self.get_argument('plate-id')
        concentrations = json_decode(self.get_argument('concentrations'))
        concentrations = np.asarray(concentrations)

        plate = Plate(plate_id)
        q_process = QuantificationProcess.create(
            self.current_user, plate, concentrations)

        pool_name = 'Pool - %s' % plate.external_id

        input_compositions = []
        concentrations = q_process.concentrations
        total_vol = 0
        for conc in concentrations:
            in_vol = conc[1]
            total_vol += in_vol
            input_compositions.append(
                {'composition': conc[0],
                 'input_volume': in_vol, 'percentage_of_output': in_vol})

        for ic in input_compositions:
            ic['percentage_of_output'] = ic['percentage_of_output'] / total_vol

        process = PoolingProcess.create(
            self.current_user, q_process, pool_name, total_vol,
            input_compositions)

        self.write({'process': process.id})
