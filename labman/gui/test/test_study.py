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


class TestStudyListHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/study_list')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'data': [
            [1, 'Identification of the Microbiomes for Cannabis Soils',
             'Cannabis Soils', 'test@foo.bar', 27]]}
        self.assertEqual(obs, exp)


class TestStudyHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/study/1/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'study_id': 1,
               'study_title': 'Identification of the Microbiomes for '
                              'Cannabis Soils',
               'total_samples': 27}
        self.assertEqual(obs, exp)

        # Test non-existend study
        response = self.get('/study/400/')
        self.assertEqual(response.code, 404)

if __name__ == '__main__':
    main()
