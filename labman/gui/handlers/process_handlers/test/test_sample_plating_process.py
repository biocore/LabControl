# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.web import HTTPError
from tornado.escape import json_decode

from labman.db import sql_connection
from labman.db.user import User
from labman.db.study import Study
from labman.db.composition import SampleComposition
from labman.gui.testing import TestHandlerBase
from labman.gui.handlers.process_handlers.sample_plating_process import (
    sample_plating_process_handler_patch_request)


class TestUtils(TestHandlerBase):
    def setUp(self):
        super().setUp()
        self.user = User('test@foo.bar')

    def test_sample_plating_process_handler_patch_request(self):
        # Test operation not supported
        regex = ('Operation add not supported. Current supported '
                 'operations: replace')
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'add', '/well/8/1/1/sample', '1.SKM8.640201',
                None)

        # Test incorrect path parameter
        regex = 'Incorrect path parameter'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/8/1/', '1.SKM8.640201', None)
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample/content',
                '1.SKM8.640201', None)

        # Test attribute not found
        regex = 'Attribute content not found'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/content/8/1/1/sample',
                '1.SKM8.640201', None)

        # Test well not found
        regex = 'Well attribute WRONG not found'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/WRONG', '1.SKM8.640201',
                None)

        # Test missing req_value
        regex = 'A new value for the well should be provided'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample', None, None)
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample', '', None)
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample', '  ', None)

    def test_patch_without_specimen_id(self):
        # Test success
        tester = SampleComposition(8)
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.21.H1')

        obs = sample_plating_process_handler_patch_request(
            self.user, 10, 'replace', '/well/8/1/1/sample', '1.SKM8.640201',
            None)
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKM8.640201')
        self.assertEqual(tester.content, '1.SKM8.640201')
        self.assertEqual(obs, {'sample_id': '1.SKM8.640201',
                               'previous_plates': [],
                               'sample_ok': True})

        obs = sample_plating_process_handler_patch_request(
            self.user, 10, 'replace', '/well/8/1/1/sample', 'Unknown', None)
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'Unknown')
        self.assertEqual(obs, {'sample_id': 'Unknown',
                               'previous_plates': [],
                               'sample_ok': False})

        obs = sample_plating_process_handler_patch_request(
            self.user, 10, 'replace', '/well/8/1/1/sample', 'blank', None)
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.21.H1')
        self.assertEqual(obs, {'sample_id': 'blank.21.H1',
                               'previous_plates': [],
                               'sample_ok': True})

        # Test commenting a well
        self.assertIsNone(tester.notes)
        obs = sample_plating_process_handler_patch_request(
            self.user, 10, 'replace', '/well/8/1/1/notes', 'New Notes', None)
        self.assertEqual(tester.notes, 'New Notes')
        obs = sample_plating_process_handler_patch_request(
            self.user, 10, 'replace', '/well/8/1/1/notes', '  ', None)
        self.assertIsNone(tester.notes)

    def test_patch_with_specimen_id(self):
        # Test success
        tester = SampleComposition(8)
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.21.H1')

        # HACK: the Study object in labman can't modify specimen_id_column
        # hence we do this directly in SQL, if a test fails the transaction
        # will rollback, otherwise we reset the column to NULL.
        sql = """UPDATE qiita.study
                 SET specimen_id_column = %s
                 WHERE study_id = 1"""
        with sql_connection.TRN as TRN:
            TRN.add(sql, ['anonymized_name'])

            print(Study(1).specimen_id_column)

            obs = sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample',
                'SKM8', None)
            self.assertEqual(tester.sample_composition_type,
                             'experimental sample')
            self.assertEqual(tester.sample_id, '1.SKM8.640201')
            self.assertEqual(tester.content, '1.SKM8.640201')
            self.assertEqual(tester.specimen_id, 'SKM8')
            self.assertEqual(obs, {'sample_id': 'SKM8',
                                   'previous_plates': [],
                                   'sample_ok': True})

            obs = sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample', 'Unknown',
                None)
            self.assertEqual(tester.sample_composition_type,
                             'experimental sample')
            self.assertIsNone(tester.sample_id)
            self.assertEqual(tester.content, 'Unknown')
            self.assertEqual(tester.specimen_id, 'Unknown')
            self.assertEqual(obs, {'sample_id': 'Unknown',
                                   'previous_plates': [],
                                   'sample_ok': False})

            obs = sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/sample', 'blank',
                None)
            self.assertEqual(tester.sample_composition_type, 'blank')
            self.assertIsNone(tester.sample_id)
            self.assertEqual(tester.content, 'blank.21.H1')
            self.assertEqual(tester.specimen_id, 'blank.21.H1')
            self.assertEqual(obs, {'sample_id': 'blank.21.H1',
                                   'previous_plates': [],
                                   'sample_ok': True})

            # Test commenting a well
            self.assertIsNone(tester.notes)
            obs = sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/notes', 'New Notes',
                None)
            self.assertEqual(tester.notes, 'New Notes')
            obs = sample_plating_process_handler_patch_request(
                self.user, 10, 'replace', '/well/8/1/1/notes', '  ', None)
            self.assertIsNone(tester.notes)

            TRN.add(sql, [None])


class TestSamplePlatingProcessHandlers(TestHandlerBase):
    def test_post_sample_plating_process_notes(self):
        data = {'process_id': 1, 'notes': 'This is a test note'}
        response = self.post('/process/sample_plating/notes', data)
        self.assertEqual(response.code, 200)

        data = {'process_id': 1, 'notes': None}
        response = self.post('/process/sample_plating/notes', data)
        self.assertEqual(response.code, 200)

    def test_post_sample_plating_process_list_handler(self):
        data = {'plate_name': 'New Plate name',
                'plate_configuration': 1}
        response = self.post('/process/sample_plating', data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        # The specific id's can change, so we just make sure that the keys
        # are what we expect
        self.assertCountEqual(obs.keys(), ['plate_id', 'process_id'])

        # Error
        data['plate_name'] = 'Test plate 1'
        response = self.post('/process/sample_plating', data)
        self.assertEqual(response.code, 500)
        self.assertNotEqual(response.body, '')

    def test_patch_sample_plating_process_handler_without_specimen_id(self):
        obs = SampleComposition(8)
        data = {'op': 'replace', 'path': '/well/8/1/1/sample',
                'value': '1.SKM8.640201'}
        response = self.patch('/process/sample_plating/10', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(obs.sample_id, '1.SKM8.640201')
        self.assertEqual(json_decode(response.body),
                         {'sample_id': '1.SKM8.640201',
                          'previous_plates': [],
                          'sample_ok': True})

    def test_patch_sample_plating_process_handler_with_specimen_id(self):
        # HACK: the Study object in labman can't modify specimen_id_column
        # hence we do this directly in SQL, if a test fails the transaction
        # will rollback, otherwise we reset the column to NULL.
        sql = """UPDATE qiita.study
                 SET specimen_id_column = %s
                 WHERE study_id = 1"""
        with sql_connection.TRN as TRN:
            TRN.add(sql, ['anonymized_name'])

            obs = SampleComposition(8)
            data = {'op': 'replace', 'path': '/well/8/1/1/sample',
                    'value': 'SKM8'}
            response = self.patch('/process/sample_plating/10', data)
            self.assertEqual(response.code, 200)
            self.assertEqual(obs.sample_id, '1.SKM8.640201')
            self.assertEqual(obs.specimen_id, 'SKM8')
            self.assertEqual(json_decode(response.body),
                             {'sample_id': 'SKM8',
                              'previous_plates': [],
                              'sample_ok': True})

            TRN.add(sql, [None])


if __name__ == '__main__':
    main()
