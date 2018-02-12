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


class TestStudyHandlers(TestHandlerBase):
    def test_get_study_list_handler(self):
        response = self.get('/study_list')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'data': [
            [1, 'Identification of the Microbiomes for Cannabis Soils',
             'Cannabis Soils', 'test@foo.bar', 27]]}
        self.assertEqual(obs, exp)

    def test_get_study_handler(self):
        response = self.get('/study/1/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'study_id': 1,
               'study_title': 'Identification of the Microbiomes for '
                              'Cannabis Soils',
               'total_samples': 27}
        self.assertEqual(obs, exp)

        # Test non-existent study
        response = self.get('/study/400/')
        self.assertEqual(response.code, 404)

    def test_get_study_samples_handler(self):
        response = self.get('/study/1/samples')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
               '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
               '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
               '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
               '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
               '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
               '1.SKM1.640183', '1.SKM2.640199']
        self.assertEqual(obs, exp)

        response = self.get('/study/1/samples?term=SKB')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
               '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
               '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200']
        self.assertEqual(obs, exp)

        response = self.get('/study/1/samples?term=SKB1')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKB1.640202']
        self.assertEqual(obs, exp)

        response = self.get('/study/1/samples?term=1.64')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKB1.640202', '1.SKD1.640179', '1.SKM1.640183']
        self.assertEqual(obs, exp)

        # test non-existent study
        response = self.get('/study/400/sample_search')

    def test_get_study_summary_handler(self):
        response = self.get('/study/1/summary')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/study/1000/summary')
        self.assertEqual(response.code, 404)

    def test_get_download_plate_maps_handler(self):
        response = self.get('/study/1/plate_maps')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')
        self.assertTrue(response.body.startswith(
            b'Plate "Test plate 1" (ID: 21)\n'))

        response = self.get('/study/1000/plate_maps')
        self.assertEqual(response.code, 404)


if __name__ == '__main__':
    main()
