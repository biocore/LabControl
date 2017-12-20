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

from labman.db.user import User
from labman.db.composition import SampleComposition
from labman.gui.testing import TestHandlerBase
from labman.gui.handlers.process_handlers.sample_plating_process import (
    sample_plating_process_handler_patch_request)


class TestUtils(TestHandlerBase):
    def test_sample_plating_process_handler_patch_request(self):
        user = User('test@foo.bar')
        # Test operation not supported
        regex = ('Operation add not supported. Current supported '
                 'operations: replace')
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'add', '/well/8/1/', '1.SKM8.640201', None)

        # Test incorrect path parameter
        regex = 'Incorrect path parameter'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'replace', '/8/1/', '1.SKM8.640201', None)
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'replace', '/well/8/1/content', '1.SKM8.640201', None)

        # Test attribute not found
        regex = 'Attribute content not found'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'replace', '/content/8/1/', '1.SKM8.640201', None)

        # Test missing req_value
        regex = 'A new value for the well should be provided'
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'replace', '/well/8/1/', None, None)
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'replace', '/well/8/1/', '', None)
        with self.assertRaisesRegex(HTTPError, regex):
            sample_plating_process_handler_patch_request(
                user, 6, 'replace', '/well/8/1/', '  ', None)

        # Test success
        obs = SampleComposition(85)
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)

        sample_plating_process_handler_patch_request(
            user, 6, 'replace', '/well/8/1/', '1.SKM8.640201', None)
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKM8.640201')

        sample_plating_process_handler_patch_request(
            user, 6, 'replace', '/well/8/1/', 'blank', None)
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)


class TestSamplePlatingProcessHandlers(TestHandlerBase):
    def test_post_sample_plating_process_list_handler(self):
        data = {'plate_name': 'New Plate name',
                'plate_configuration': 1,
                'volume': 10}
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

    def test_patch_sample_plateing_process_handler(self):
        data = {'op': 'add', 'path': '/well/8/1/', 'value': '1.SKM8.640201'}
        response = self.patch('/process/sample_plating/6', data)
        self.assertEqual(response.code, 400)
        self.assertNotEqual(response.body, '')


if __name__ == '__main__':
    main()
