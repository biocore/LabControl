# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode

from labcontrol.gui.testing import TestHandlerBase


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
        all_s1_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                          '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                          '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                          '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                          '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                          '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                          '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                          '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                          '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        self.assertEqual(obs, all_s1_samples)

        # Using a "limit" imposes a cutoff on the number of samples returned,
        # if needed. 20 is the limit used in autocomplete_search_samples() in
        # the front-end code.
        response = self.get('/study/1/samples?limit=20')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        lim20_s1_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                            '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                            '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                            '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                            '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                            '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                            '1.SKM1.640183', '1.SKM2.640199']
        self.assertEqual(obs, lim20_s1_samples)

        # Using a limit of greater than the number of samples in this study (in
        # this case, 27) doesn't alter the output
        response = self.get('/study/1/samples?limit=50')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertEqual(obs, all_s1_samples)

        # Try some invalid limits
        response = self.get('/study/1/samples?limit=0')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=0.1')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=1.0')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=-1')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=27.0')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=000')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=abcdefg')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=None')
        self.assertEqual(response.code, 400)
        response = self.get('/study/1/samples?limit=abcdefg&term=skm')
        self.assertEqual(response.code, 400)

        # Using a "term" filters samples to just those that contain that term
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

        # "limit" and "term" should be usable together
        response = self.get('/study/1/samples?term=S&limit=20')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertEqual(obs, lim20_s1_samples)

        response = self.get('/study/1/samples?term=SKM&limit=1')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKM1.640183']
        self.assertEqual(obs, exp)

        response = self.get('/study/1/samples?term=SKM&limit=2')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKM1.640183', '1.SKM2.640199']
        self.assertEqual(obs, exp)

        response = self.get('/study/1/samples?term=SKM&limit=30')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
               '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
               '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        self.assertEqual(obs, exp)

        # test non-existent study
        response = self.get('/study/400/sample_search')
        self.assertEqual(response.code, 404)

    def test_get_study_summary_handler(self):
        response = self.get('/study/1/summary')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/study/1000/summary')
        self.assertEqual(response.code, 404)


if __name__ == '__main__':
    main()
