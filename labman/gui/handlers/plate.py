# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from tornado.web import authenticated
from tornado.escape import json_encode

from labman.gui.handlers.base import BaseHandler
from labman.db.exceptions import LabmanUnknownIdError


class PlateMapHandler(BaseHandler):
    @authenticated
    def get(self):
        # TODO: Get the plate configuration from the DB
        def get_plate_confs():
            """Placeholder for the actual DB call"""
            return [[1, '96-well plate', 8, 12],
                    [2, '26-well plate', 4, 6],
                    [3, '384-well plate', 16, 24]]

        plate_id = self.get_argument('plate_id', None)

        plate_confs = get_plate_confs()
        self.render("plate.html", plate_confs=plate_confs, plate_id=plate_id)

    @authenticated
    def post(self):
        # TODO: Perform the call to the DB
        def create_plate(name, configuration):
            """Placeholder for the actual DB call"""
            if name == 'Throw an error please':
                raise ValueError(name)
            return 1

        plate_name = self.get_argument('plate_name')
        plate_configuration = self.get_argument('plate_configuration')
        plate_id = create_plate(plate_name, plate_configuration)
        self.write(json_encode({'plate_id': plate_id}))
        self.finish()


class PlateNameHandler(BaseHandler):
    @authenticated
    def get(self):
        # TODO: Check on the DB if the plate exist
        def exists(new_name):
            """Placeholder for the actual DB call"""
            if new_name == 'error':
                raise ValueError('Forcing a way to test that the error '
                                 'reporting works as expected')
            return new_name == 'exists'

        new_name = self.get_argument('new-name')
        status = 200 if exists(new_name) else 404
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

    @authenticated
    def post(self, plate_id):
        # TODO: Update the database
        def edit_plate_well(p_id, row, col, content):
            """Placeholder for the actual DB call"""
            if content == 'error':
                raise ValueError('Placeholder to show error reporting')

        row = self.get_argument('row')
        col = self.get_argument('col')
        content = self.get_argument('content')

        try:
            edit_plate_well(plate_id, row, col, content)
        except LabmanUnknownIdError:
            self.set_status(404)
        self.finish()
