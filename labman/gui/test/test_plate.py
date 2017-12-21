# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode
from tornado.web import HTTPError

from labman.gui.testing import TestHandlerBase
from labman.db.plate import Plate
from labman.db.user import User
from labman.gui.handlers.plate import (
    _get_plate, plate_handler_patch_request, plate_layout_handler_get_request,
    plate_map_handler_get_request)


class TestUtils(TestHandlerBase):
    def test_get_plate(self):
        self.assertEqual(_get_plate('17'), Plate(17))
        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            _get_plate(100)

    def test_plate_map_handler_get_request(self):
        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_map_handler_get_request(100)

        obs = plate_map_handler_get_request(17)
        exp_plate_confs = [[1, '96-well deep-well plate', 8, 12],
                           [2, '96-well microtiter plate', 8, 12],
                           [3, '384-well microtiter plate', 16, 24],
                           [4, '96-well template plate', 8, 12]]
        exp = {'plate_confs': exp_plate_confs, 'plate_id': 17, 'process_id': 6}
        self.assertEqual(obs, exp)

        obs = plate_map_handler_get_request(None)
        exp = {'plate_confs': exp_plate_confs, 'plate_id': None,
               'process_id': None}
        self.assertEqual(obs, exp)

    def test_plate_handler_patch_request(self):
        tester = Plate(17)
        user = User('test@foo.bar')

        # Incorrect path parameter
        regex = 'Incorrect path parameter'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 17, 'replace', '/name/newname',
                                        'NewName', None)

        # Unknown attribute
        regex = 'Attribute unknown not recognized'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 17, 'replace', '/unknown/',
                                        'NewName', None)

        # Unknown operation
        regex = ('Operation add not supported. Current supported '
                 'operations: replace')
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 17, 'add', '/name/',
                                        'NewName', None)

        # Plate doesn't exist
        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 100, 'replace', '/name/',
                                        'NewName', None)

        # Test success - Name
        plate_handler_patch_request(user, 17, 'replace', '/name/',
                                    'NewName', None)
        self.assertEqual(tester.external_id, 'NewName')
        tester.external_id = 'Test plate 1'

    def test_plate_layout_handler_get_request(self):
        obs = plate_layout_handler_get_request(17)
        self.assertEqual(len(obs), 8)
        exp = [{'sample': '1.SKB1.640202', 'notes': None},
               {'sample': '1.SKB2.640194', 'notes': None},
               {'sample': '1.SKB3.640195', 'notes': None},
               {'sample': '1.SKB4.640189', 'notes': None},
               {'sample': '1.SKB5.640181', 'notes': None},
               {'sample': '1.SKB6.640176', 'notes': None},
               {'sample': '1.SKB7.640196', 'notes': None},
               {'sample': '1.SKB8.640193', 'notes': None},
               {'sample': '1.SKB9.640200', 'notes': None},
               {'sample': '1.SKD1.640179', 'notes': None},
               {'sample': '1.SKD2.640178', 'notes': None},
               {'sample': '1.SKD3.640198', 'notes': None}]
        # The first 6 rows are all equal
        for row in obs[:6]:
            self.assertEqual(row, exp)

        # The 7th row contains virio controls
        exp = [{'sample': 'vibrio positive control', 'notes': None}] * 12
        self.assertEqual(obs[6], exp)

        # The 8th row contains blanks
        exp = [{'sample': 'blank', 'notes': None}] * 12
        self.assertEqual(obs[7], exp)

        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_layout_handler_get_request(100)


class TestPlateHandlers(TestHandlerBase):
    def test_get_plate_map_handler(self):
        response = self.get('/plate')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/plate?plate_id=17')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/plate?plate_id=100')
        self.assertEqual(response.code, 404)
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
        response = self.get('/plate/17/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'plate_id': 17,
               'plate_name': 'Test plate 1',
               'discarded': False,
               'plate_configuration': [1, '96-well deep-well plate', 8, 12],
               'notes': None}
        self.assertEqual(obs, exp)

        # Plate doesn't exist
        response = self.get('/plate/100/')
        self.assertEqual(response.code, 404)

    def test_patch_plate_handler(self):
        tester = Plate(17)
        data = {'op': 'replace', 'path': '/name/', 'value': 'NewName'}
        response = self.patch('/plate/17/', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(tester.external_id, 'NewName')
        tester.external_id = 'Test plate 1'

    def test_get_plate_layout_handler(self):
        response = self.get('/plate/17/layout')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        # Spot check some positions, since a more in-depth test has already
        # been performed in test_plate_layout_handler_get_request
        self.assertEqual(obs[0][0], {'sample': '1.SKB1.640202', 'notes': None})
        self.assertEqual(obs[5][9], {'sample': '1.SKD1.640179', 'notes': None})
        self.assertEqual(obs[6][1],
                         {'sample': 'vibrio positive control', 'notes': None})
        self.assertEqual(obs[7][4], {'sample': 'blank', 'notes': None})


if __name__ == '__main__':
    main()
