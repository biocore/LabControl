# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated, HTTPError
from tornado.escape import json_encode

from labman.gui.handlers.base import BaseHandler
from labman.db.exceptions import LabmanUnknownIdError
from labman.db.plate import PlateConfiguration, Plate


class PlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        plate_id = self.get_argument('plate_id', None)
        plate_confs = [[pc.id, pc.description, pc.num_rows, pc.num_columns]
                       for pc in PlateConfiguration.iter()]
        self.render("plate.html", plate_confs=plate_confs, plate_id=plate_id)


class PlateNameHandler(BaseHandler):
    @authenticated
    def get(self):
        new_name = self.get_argument('new-name')
        status = 200 if Plate.external_id_exists(new_name) else 404
        self.set_status(status)
        self.finish()


class PlateHandler(BaseHandler):
    @authenticated
    def get(self, plate_id):
        # TODO: Retrieve information from the DB
        def get_plate_info(p_id):
            """Placeholder for the actual DB call"""
            if p_id == 100:
                raise LabmanUnknownIdError('plate', p_id)
            elif p_id == 101:
                raise ValueError('Something else happened')
            return {'plate_id': p_id,
                    'plate_name': 'Test Plate %s' % p_id,
                    'discarded': False,
                    'plate_configuration': [1, '96-well plate', 8, 12],
                    'notes': 'Some plate notes'}

        plate_id = int(plate_id)
        try:
            self.write(json_encode(get_plate_info(plate_id)))
        except LabmanUnknownIdError:
            self.set_status(404)
        self.finish()

    @authenticated
    def patch(self, plate_id):
        # TODO: Perform the modifications in the DB
        def set_plate_name(p_id, new_name):
            """Placeholder for the actual DB call"""
            if new_name == 'Throw an error please':
                raise ValueError(new_name)

        def set_plate_configuration(p_id, new_config):
            """Placeholder for the actual DB call"""
            if new_config == 3:
                raise ValueError('Configuration not supported in plate')

        # Follows the JSON PATCH specification
        # https://tools.ietf.org/html/rfc6902
        req_op = self.get_argument('op')
        req_path = self.get_argument('path')
        param_value = self.get_argument('value', None)
        # This is currently not used, but is part of the JSON PATCH
        # specification, so leaving commented out here in case that needed
        # in the future
        # param_from = self.get_argument('from', None)
        plate_id = int(plate_id)

        if req_op == 'replace':
            req_path = [v for v in req_path.split('/') if v]
            if len(req_path) == 0:
                raise HTTPError(400, 'Incorrect path parameter')

            attribute = req_path[0]
            if attribute == 'name':
                set_plate_name(plate_id, param_value)
            elif attribute == 'configuration':
                param_value = int(param_value)
                set_plate_configuration(plate_id, param_value)
            else:
                raise HTTPError(404, 'Attribute %s not recognized' % attribute)
        else:
            raise HTTPError(400, 'Operation %s not suppert. Current supported '
                                 'operations: replace' % req_op)


class PlateLayoutHandler(BaseHandler):
    @authenticated
    def get(self, plate_id):
        # TODO: Retrieve information from the DB
        def get_plate_layout(p_id):
            """Placeholder for the actual DB call"""
            if p_id == 100:
                raise LabmanUnknownIdError('plate', p_id)
            elif p_id == 101:
                raise ValueError('Something else happened')

            layout = []
            for r in range(8):
                row = []
                for c in range(10):
                    col = {'sample': 'Sample %s %s' % (r, c),
                           'notes': None}
                    row.append(col)
                row.append({'sample': 'VIBRIO', 'notes': None})
                row.append({'sample': 'BLANK', 'notes': None})
                layout.append(row)

            return layout

        plate_id = int(plate_id)
        try:
            self.write(json_encode(get_plate_layout(plate_id)))
        except LabmanUnknownIdError:
            self.set_status(404)
        self.finish()
