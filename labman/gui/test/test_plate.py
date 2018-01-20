# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from json import dumps
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
        self.assertEqual(_get_plate('21'), Plate(21))
        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            _get_plate(100)

    def test_plate_map_handler_get_request(self):
        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_map_handler_get_request(100)

        obs = plate_map_handler_get_request(21)
        exp_plate_confs = [[1, '96-well deep-well plate', 8, 12],
                           [2, '96-well microtiter plate', 8, 12],
                           [3, '384-well microtiter plate', 16, 24],
                           [4, '96-well template plate', 8, 12],
                           [5, '384-well template plate', 16, 24]]
        exp = {'plate_confs': exp_plate_confs, 'plate_id': 21,
               'process_id': 10}
        self.assertEqual(obs, exp)

        obs = plate_map_handler_get_request(None)
        exp = {'plate_confs': exp_plate_confs, 'plate_id': None,
               'process_id': None}
        self.assertEqual(obs, exp)

    def test_plate_handler_patch_request(self):
        tester = Plate(21)
        user = User('test@foo.bar')

        # Incorrect path parameter
        regex = 'Incorrect path parameter'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 21, 'replace', '/name/newname',
                                        'NewName', None)

        # Unknown attribute
        regex = 'Attribute unknown not recognized'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 21, 'replace', '/unknown/',
                                        'NewName', None)

        # Unknown operation
        regex = ('Operation add not supported. Current supported '
                 'operations: replace')
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 21, 'add', '/name/',
                                        'NewName', None)

        # Plate doesn't exist
        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_handler_patch_request(user, 100, 'replace', '/name/',
                                        'NewName', None)

        # Test success - Name
        plate_handler_patch_request(user, 21, 'replace', '/name/',
                                    'NewName', None)
        self.assertEqual(tester.external_id, 'NewName')
        tester.external_id = 'Test plate 1'

    def test_plate_layout_handler_get_request(self):
        obs = plate_layout_handler_get_request(21)
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
        exp = [{'sample': 'vibrio.positive.control.21.G%s' % i, 'notes': None}
               for i in range(1, 13)]
        self.assertEqual(obs[6], exp)

        # The 8th row contains blanks
        exp = [{'sample': 'blank.21.H%s' % i, 'notes': None}
               for i in range(1, 13)]
        self.assertEqual(obs[7], exp)

        regex = 'Plate 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_layout_handler_get_request(100)


class TestPlateHandlers(TestHandlerBase):
    def test_get_plate_list_handler(self):
        response = self.get('/plate_list')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 26)
        self.assertEqual(obs_data[0], [1, 'EMP 16S V4 primer plate 1'])

        response = self.get('/plate_list?plate_type=sample')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(obs_data[0], [21, 'Test plate 1'])

    def test_get_plate_map_handler(self):
        response = self.get('/plate')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/plate?plate_id=21')
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
        response = self.get('/plate/21/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'plate_id': 21,
               'plate_name': 'Test plate 1',
               'discarded': False,
               'plate_configuration': [1, '96-well deep-well plate', 8, 12],
               'notes': None,
               'studies': [1]}
        self.assertEqual(obs, exp)

        # Plate doesn't exist
        response = self.get('/plate/100/')
        self.assertEqual(response.code, 404)

    def test_patch_plate_handler(self):
        tester = Plate(21)
        data = {'op': 'replace', 'path': '/name/', 'value': 'NewName'}
        response = self.patch('/plate/21/', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(tester.external_id, 'NewName')
        tester.external_id = 'Test plate 1'

    def test_get_plate_layout_handler(self):
        response = self.get('/plate/21/layout')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        # Spot check some positions, since a more in-depth test has already
        # been performed in test_plate_layout_handler_get_request
        self.assertEqual(obs[0][0], {'sample': '1.SKB1.640202', 'notes': None})
        self.assertEqual(obs[5][9], {'sample': '1.SKD1.640179', 'notes': None})
        self.assertEqual(
            obs[6][1], {'sample':
                        'vibrio.positive.control.21.G2', 'notes': None})
        self.assertEqual(obs[7][4], {'sample': 'blank.21.H5', 'notes': None})

    def test_get_plate_search_handler(self):
        response = self.get('/plate_search')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_plate_search_handler(self):
        pass
        # # TODO: This test needs to be filled in by someone who knows what samples/etc the test database will hold
        # post_data = {
        #     'sample_names': dumps(sampleNames),
        #     'plate_comment_keywords': plate_comment_keywords,
        #     'well_comment_keywords': well_comment_keywords,
        #     'operation': "INTERSECT"
        # }
        # response = self.post('/plate_search', post_data)
        # self.assertEqual(response.code, 200)
        # obs = json_decode(response.body)
        # self.assertCountEqual(obs.keys(), ['data'])
        # obs_data = obs['data']
        # self.assertEqual(len(obs_data), 1)
        # self.assertEqual(obs_data[0], [21, 'Test plate 1'])

if __name__ == '__main__':
    main()
