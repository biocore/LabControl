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

    def test_get_study_search_samples_handler(self):
        response = self.get('/study/1/sample_search?term=SKB')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = [{'label': '1.SKB1.640202', 'value': '1.SKB1.640202'},
               {'label': '1.SKB2.640194', 'value': '1.SKB2.640194'},
               {'label': '1.SKB3.640195', 'value': '1.SKB3.640195'},
               {'label': '1.SKB4.640189', 'value': '1.SKB4.640189'},
               {'label': '1.SKB5.640181', 'value': '1.SKB5.640181'},
               {'label': '1.SKB6.640176', 'value': '1.SKB6.640176'},
               {'label': '1.SKB7.640196', 'value': '1.SKB7.640196'},
               {'label': '1.SKB8.640193', 'value': '1.SKB8.640193'},
               {'label': '1.SKB9.640200', 'value': '1.SKB9.640200'}]
        self.assertEqual(obs, exp)

        response = self.get('/study/1/sample_search?term=SKB1')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = [{'label': '1.SKB1.640202', 'value': '1.SKB1.640202'}]
        self.assertEqual(obs, exp)

        response = self.get('/study/1/sample_search?term=1.64')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = [{'label': '1.SKB1.640202', 'value': '1.SKB1.640202'},
               {'label': '1.SKD1.640179', 'value': '1.SKD1.640179'},
               {'label': '1.SKM1.640183', 'value': '1.SKM1.640183'}]
        self.assertEqual(obs, exp)

        # test non-existent study
        response = self.get('/study/400/sample_search')


if __name__ == '__main__':
    main()
