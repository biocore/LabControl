# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import datetime
from json import dumps
from unittest import main

from tornado.escape import json_decode
from tornado.web import HTTPError

from labman.gui.testing import TestHandlerBase
from labman.db.plate import Plate
from labman.db.user import User
from labman.db.process import Process
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
        regex = 'Plating process 100 doesn\'t exist'
        with self.assertRaisesRegex(HTTPError, regex):
            plate_map_handler_get_request(100)

        obs = plate_map_handler_get_request(10)
        exp_plate_confs = [[1, '96-well deep-well plate', 8, 12],
                           [2, '96-well microtiter plate', 8, 12],
                           [3, '384-well microtiter plate', 16, 24]]
        exp_contr_desc = [
            {'external_id': 'blank',
             'description': 'gDNA extraction blanks. Represents an empty '
                            'extraction well.'},
            {'external_id': 'empty',
             'description': 'Empty well. Represents an empty well that should '
                            'not be included in library preparation.'},
            {'external_id': 'vibrio.positive.control',
             'description': 'Bacterial isolate control (Vibrio fischeri ES114)'
                            '. Represents an extraction well loaded with '
                            'Vibrio.'},
            {'external_id': 'zymo.mock',
             'description': 'Bacterial community control (Zymo Mock D6306). '
                            'Represents an extraction well loaded with Zymo '
                            'Mock community.'}]
        exp = {'plate_confs': exp_plate_confs, 'plate_id': 21,
               'process_id': 10, 'controls_description': exp_contr_desc}
        self.assertEqual(obs, exp)

        obs = plate_map_handler_get_request(None)
        exp = {'plate_confs': exp_plate_confs, 'plate_id': None,
               'process_id': None, 'controls_description': exp_contr_desc}
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

        # Test success - discarded
        plate_handler_patch_request(user, 21, 'replace', '/discarded/',
                                    True, None)
        self.assertEqual(tester.discarded, True)
        tester.discarded = False

    def test_plate_layout_handler_get_request(self):
        obs = plate_layout_handler_get_request(21)
        self.assertEqual(len(obs), 8)
        exp = [{'sample': '1.SKB1.640202.21.A1', 'notes': None},
               {'sample': '1.SKB2.640194.21.A2', 'notes': None},
               {'sample': '1.SKB3.640195.21.A3', 'notes': None},
               {'sample': '1.SKB4.640189.21.A4', 'notes': None},
               {'sample': '1.SKB5.640181.21.A5', 'notes': None},
               {'sample': '1.SKB6.640176.21.A6', 'notes': None},
               {'sample': '1.SKB7.640196.21.A7', 'notes': None},
               {'sample': '1.SKB8.640193.21.A8', 'notes': None},
               {'sample': '1.SKB9.640200.21.A9', 'notes': None},
               {'sample': '1.SKD1.640179.21.A10', 'notes': None},
               {'sample': '1.SKD2.640178.21.A11', 'notes': None},
               {'sample': '1.SKD3.640198.21.A12', 'notes': None}]
        self.assertEqual(obs[0], exp)

        # The 7th row contains virio controls
        exp = [{'sample': 'vibrio.positive.control.21.G%s' % i, 'notes': None}
               for i in range(1, 13)]
        self.assertEqual(obs[6], exp)

        # The 8th row contains blanks
        exp = [{'sample': 'blank.21.H%s' % i, 'notes': None}
               for i in range(1, 12)]
        self.assertEqual(obs[7][:-1], exp)
        self.assertEqual(obs[7][11], {'sample': 'empty.21.H12', 'notes': None})

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
        self.assertEqual(obs_data[0], [1, 'EMP 16S V4 primer plate 1', None])

        response = self.get('/plate_list?plate_type=%5B%22sample%22%5D')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(
            obs_data[0], [
             21, 'Test plate 1',
             ['Identification of the Microbiomes for Cannabis Soils']])

        response = self.get(
            '/plate_list?plate_type=%5B%22compressed+gDNA%22%2C+%22'
            'normalized+gDNA%22%5D')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 2)
        self.assertEqual(
            obs_data,
            [[24, 'Test compressed gDNA plate 1',
              ['Identification of the Microbiomes for Cannabis Soils']],
             [25, 'Test normalized gDNA plate 1',
              ['Identification of the Microbiomes for Cannabis Soils']]])
        response = self.get(
            '/plate_list?plate_type=%5B%22compressed+gDNA%22%2C+%22'
            'normalized+gDNA%22%5D&only_quantified=true')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(
            obs_data,
            [[24, 'Test compressed gDNA plate 1',
              ['Identification of the Microbiomes for Cannabis Soils']]])

    def test_get_plate_map_handler(self):
        response = self.get('/plate')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/plate?process_id=10')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/plate?process_id=100')
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
               'studies': [1],
               'duplicates': [
                    [1, 1, '1.SKB1.640202.21.A1'],
                    [2, 1, '1.SKB1.640202.21.B1'],
                    [3, 1, '1.SKB1.640202.21.C1'],
                    [4, 1, '1.SKB1.640202.21.D1'],
                    [5, 1, '1.SKB1.640202.21.E1'],
                    [6, 1, '1.SKB1.640202.21.F1'],
                    [1, 2, '1.SKB2.640194.21.A2'],
                    [2, 2, '1.SKB2.640194.21.B2'],
                    [3, 2, '1.SKB2.640194.21.C2'],
                    [4, 2, '1.SKB2.640194.21.D2'],
                    [5, 2, '1.SKB2.640194.21.E2'],
                    [6, 2, '1.SKB2.640194.21.F2'],
                    [1, 3, '1.SKB3.640195.21.A3'],
                    [2, 3, '1.SKB3.640195.21.B3'],
                    [3, 3, '1.SKB3.640195.21.C3'],
                    [4, 3, '1.SKB3.640195.21.D3'],
                    [5, 3, '1.SKB3.640195.21.E3'],
                    [6, 3, '1.SKB3.640195.21.F3'],
                    [1, 4, '1.SKB4.640189.21.A4'],
                    [2, 4, '1.SKB4.640189.21.B4'],
                    [3, 4, '1.SKB4.640189.21.C4'],
                    [4, 4, '1.SKB4.640189.21.D4'],
                    [5, 4, '1.SKB4.640189.21.E4'],
                    [6, 4, '1.SKB4.640189.21.F4'],
                    [1, 5, '1.SKB5.640181.21.A5'],
                    [2, 5, '1.SKB5.640181.21.B5'],
                    [3, 5, '1.SKB5.640181.21.C5'],
                    [4, 5, '1.SKB5.640181.21.D5'],
                    [5, 5, '1.SKB5.640181.21.E5'],
                    [6, 5, '1.SKB5.640181.21.F5'],
                    [1, 6, '1.SKB6.640176.21.A6'],
                    [2, 6, '1.SKB6.640176.21.B6'],
                    [3, 6, '1.SKB6.640176.21.C6'],
                    [4, 6, '1.SKB6.640176.21.D6'],
                    [5, 6, '1.SKB6.640176.21.E6'],
                    [6, 6, '1.SKB6.640176.21.F6'],
                    [1, 7, '1.SKB7.640196.21.A7'],
                    [2, 7, '1.SKB7.640196.21.B7'],
                    [3, 7, '1.SKB7.640196.21.C7'],
                    [4, 7, '1.SKB7.640196.21.D7'],
                    [5, 7, '1.SKB7.640196.21.E7'],
                    [6, 7, '1.SKB7.640196.21.F7'],
                    [1, 8, '1.SKB8.640193.21.A8'],
                    [2, 8, '1.SKB8.640193.21.B8'],
                    [3, 8, '1.SKB8.640193.21.C8'],
                    [4, 8, '1.SKB8.640193.21.D8'],
                    [5, 8, '1.SKB8.640193.21.E8'],
                    [6, 8, '1.SKB8.640193.21.F8'],
                    [1, 9, '1.SKB9.640200.21.A9'],
                    [2, 9, '1.SKB9.640200.21.B9'],
                    [3, 9, '1.SKB9.640200.21.C9'],
                    [4, 9, '1.SKB9.640200.21.D9'],
                    [5, 9, '1.SKB9.640200.21.E9'],
                    [6, 9, '1.SKB9.640200.21.F9'],
                    [1, 10, '1.SKD1.640179.21.A10'],
                    [2, 10, '1.SKD1.640179.21.B10'],
                    [3, 10, '1.SKD1.640179.21.C10'],
                    [4, 10, '1.SKD1.640179.21.D10'],
                    [5, 10, '1.SKD1.640179.21.E10'],
                    [6, 10, '1.SKD1.640179.21.F10'],
                    [1, 11, '1.SKD2.640178.21.A11'],
                    [2, 11, '1.SKD2.640178.21.B11'],
                    [3, 11, '1.SKD2.640178.21.C11'],
                    [4, 11, '1.SKD2.640178.21.D11'],
                    [5, 11, '1.SKD2.640178.21.E11'],
                    [6, 11, '1.SKD2.640178.21.F11'],
                    [1, 12, '1.SKD3.640198.21.A12'],
                    [2, 12, '1.SKD3.640198.21.B12'],
                    [3, 12, '1.SKD3.640198.21.C12'],
                    [4, 12, '1.SKD3.640198.21.D12'],
                    [5, 12, '1.SKD3.640198.21.E12'],
                    [6, 12, '1.SKD3.640198.21.F12']],
               'previous_plates': [],
               'unknowns': [],
               'quantitation_processes': []}
        obs_duplicates = obs.pop('duplicates')
        exp_duplicates = exp.pop('duplicates')
        self.assertEqual(obs, exp)
        self.assertCountEqual(obs_duplicates, exp_duplicates)

        # Plate doesn't exist
        response = self.get('/plate/100/')
        self.assertEqual(response.code, 404)

        # Plate has multiple quantitation processes
        # Note: cannot hard-code the date in the below known-good object
        # because date string representation is specific to physical location
        # in which system running the tests is located!
        tester = Plate(26)
        first_date_str = datetime.strftime(
            tester.quantification_processes[0].date,
            Process.get_date_format())
        second_date_str = datetime.strftime(
            tester.quantification_processes[1].date,
            Process.get_date_format())

        response = self.get('/plate/26/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'plate_id': 26,
               'plate_name': 'Test shotgun library plate 1',
               'discarded': False,
               'plate_configuration': [3, '384-well microtiter plate', 16, 24],
               'notes': None,
               'studies': [1],
               'duplicates': [],
               'previous_plates': [],
               'unknowns': [],
               'quantitation_processes': [
                   [4, 'Dude', first_date_str, None],
                   [5, 'Dude', second_date_str, 'Requantification--oops']]
               }
        obs_duplicates = obs.pop('duplicates')
        exp_duplicates = exp.pop('duplicates')
        self.assertEqual(obs, exp)
        self.assertCountEqual(obs_duplicates, exp_duplicates)

    def test_patch_plate_handler(self):
        tester = Plate(21)
        data = {'op': 'replace', 'path': '/name/', 'value': 'NewName'}
        response = self.patch('/plate/21/', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(tester.external_id, 'NewName')
        tester.external_id = 'Test plate 1'

    def test_patch_plate_discarded_handler(self):
        tester = Plate(21)
        data = {'op': 'replace', 'path': '/discarded/', 'value': True}
        response = self.patch('/plate/21/', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(tester.discarded, True)
        tester.discarded = False

    def test_get_plate_layout_handler(self):
        response = self.get('/plate/21/layout')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        # Spot check some positions, since a more in-depth test has already
        # been performed in test_plate_layout_handler_get_request
        self.assertEqual(obs[0][0],
                         {'sample': '1.SKB1.640202.21.A1', 'notes': None})
        self.assertEqual(obs[5][9],
                         {'sample': '1.SKD1.640179.21.F10', 'notes': None})
        self.assertEqual(
            obs[6][1], {'sample':
                        'vibrio.positive.control.21.G2', 'notes': None})
        self.assertEqual(obs[7][4], {'sample': 'blank.21.H5', 'notes': None})

    def test_get_plate_search_handler(self):
        response = self.get('/plate_search')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_plate_search_handler(self):
        # Note: these tests don't exercise all the cases covered in
        # db/tests/test_plate.py test_search; instead, they focus on
        # testing at least one search based on each of the input
        # fields, to verify that these are being passed through
        # correctly to the db's Plate.search method.

        # Test search by sample names:
        post_data = {
            'sample_names': dumps(['1.SKB1.640202', '1.SKB2.640194']),
            'plate_comment_keywords': "",
            'well_comment_keywords': "",
            'operation': "INTERSECT"
        }

        response = self.post('/plate_search', post_data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(obs_data[0], [21, 'Test plate 1'])

        # Test search by plate comment keywords:
        # It looks like none of the plates in the test database have
        # any notes, so it is necessary to add some to be able to
        # test the keywords search functionality; the below is lifted
        # verbatim from db/tests/test_plate.py test_search
        plate22 = Plate(22)
        plate23 = Plate(23)

        # Add comments to a plate so we can actually test the
        # search functionality
        plate22.notes = 'Some interesting notes'
        plate23.notes = 'More boring notes'
        # end verbatim lift

        post_data = {
            'sample_names': dumps([]),
            'plate_comment_keywords': 'interesting boring',
            'well_comment_keywords': "",
            'operation': "INTERSECT"
        }
        response = self.post('/plate_search', post_data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 0)

        # Test search by intersecting or unioning multiple search terms:
        post_data = {
            'sample_names': dumps(['1.SKB1.640202']),
            'plate_comment_keywords': 'interesting boring',
            'well_comment_keywords': "",
            'operation': "INTERSECT"
        }
        response = self.post('/plate_search', post_data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 0)

        post_data = {
            'sample_names': dumps(['1.SKB1.640202']),
            'plate_comment_keywords': 'interesting boring',
            'well_comment_keywords': "",
            'operation': "UNION"
        }
        response = self.post('/plate_search', post_data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(obs_data[0], [21, 'Test plate 1'])

        # Test search by well comment keywords:
        # Add comments to some wells so can test well comment search
        plate23.get_well(1, 1).composition.notes = 'What should I write?'

        post_data = {
            'sample_names': dumps([]),
            'plate_comment_keywords': '',
            'well_comment_keywords': "write",
            'operation': "INTERSECT"
        }
        response = self.post('/plate_search', post_data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(obs_data[0], [23, 'Test 16S plate 1'])

    def test_get_plate_process_handler(self):
        response = self.get('/plate/21/process')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith('/plate?process_id=10'))

        response = self.get('/plate/22/process')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith(
                '/process/gdna_extraction?process_id=1'))

        response = self.get('/plate/23/process')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith(
                '/process/library_prep_16S?process_id=1'))

        response = self.get('/plate/24/process')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith(
                '/process/gdna_compression?process_id=1'))

        response = self.get('/plate/25/process')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith(
                '/process/normalize?process_id=1'))

        response = self.get('/plate/26/process')
        self.assertEqual(response.code, 200)
        self.assertTrue(
            response.effective_url.endswith(
                '/process/library_prep_shotgun?process_id=1'))


if __name__ == '__main__':
    main()
