# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode

from labman.gui.testing import TestHandlerBase


class TestPlateHandlers(TestHandlerBase):
    def test_get_plate_map_handler(self):
        response = self.get('/plate')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_get_plate_name_handler(self):
        response = self.get('/platename')
        # It is missing the parameter
        self.assertEqual(response.code, 400)
        # It doesn't exist
        response = self.get('/platename?new-name=something')
        self.assertEqual(response.code, 404)
        # It exists
        response = self.get('/platename?new-name=Test%20plate%201')
        self.assertEqual(response.code, 200)

    def test_get_plate_handler(self):
        response = self.get('/plate/1/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'plate_id': 1,
               'plate_name': 'Test Plate 1',
               'discarded': False,
               'plate_configuration': [1, '96-well plate', 8, 12],
               'notes': 'Some plate notes'}
        self.assertEqual(obs, exp)

        # Plate doesn't exist
        response = self.get('/plate/100/')
        self.assertEqual(response.code, 404)

        # Error
        response = self.get('/plate/101/')
        self.assertEqual(response.code, 500)
        self.assertNotEqual(response.body, '')

    def test_patch_plate_handler(self):
        data = {'op': 'replace', 'path': '/name/', 'value': 'NewName'}
        response = self.patch('/plate/1/', data)
        self.assertEqual(response.code, 200)

        data = {'op': 'replace', 'path': '/configuration', 'value': 1}
        response = self.patch('/plate/1/', data)
        self.assertEqual(response.code, 200)

        # Incorrect path parameter
        data = {'op': 'replace', 'path': '/', 'value': 'NewName'}
        response = self.patch('/plate/1/', data)
        self.assertEqual(response.code, 400)

        # Unknown attribute
        data = {'op': 'replace', 'path': '/unknown', 'value': 'NewName'}
        response = self.patch('/plate/1/', data)
        self.assertEqual(response.code, 404)

        # Unknown operation
        data = {'op': 'add', 'path': '/name', 'value': 'NewName'}
        response = self.patch('/plate/1/', data)
        self.assertEqual(response.code, 400)

        # Error
        data = {'op': 'replace', 'path': '/configuration', 'value': 3}
        response = self.patch('/plate/1/', data)
        self.assertEqual(response.code, 500)
        self.assertNotEqual(response.body, '')

    def test_get_plate_layout_handler(self):
        response = self.get('/plate/1/layout')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = []
        for r in range(8):
            row = []
            for c in range(10):
                col = {'sample': 'Sample %s %s' % (r, c),
                       'notes': None}
                row.append(col)
            row.append({'sample': 'VIBRIO', 'notes': None})
            row.append({'sample': 'BLANK', 'notes': None})
            exp.append(row)
        self.assertEqual(obs, exp)

        # Plate doesn't exist
        response = self.get('/plate/100/layout')
        self.assertEqual(response.code, 404)

        # Error
        response = self.get('/plate/101/layout')
        self.assertEqual(response.code, 500)
        self.assertNotEqual(response.body, '')


if __name__ == '__main__':
    main()
