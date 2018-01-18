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


class TestNormalizationHandlers(TestHandlerBase):
    def test_normalization_handler(self):
        response = self.get('/process/normalize?plate_id=23')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/normalize?plate_id=21&plate_id=23')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/normalize')
        self.assertEqual(response.code, 400)
        self.assertNotEqual(response.body, '')

    def test_post_normalization_handler(self):
        data = {'plate_id': 23, 'water': 'RNBF7110', 'plate_name': '157022406',
                'total_vol': 3500, 'ng': 5, 'min_vol': 2.5, 'max_vol': 3500,
                'resolution': 2.5, 'reformat': False}
        response = self.post('/process/normalize', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


class TestDownloadNormalizationProcessHandler(TestHandlerBase):
    def test_download(self):
        data = {'plate_id': 23, 'water': 'RNBF7110', 'plate_name': '157022406',
                'total_vol': 3500, 'ng': 5, 'min_vol': 2.5, 'max_vol': 3500,
                'resolution': 2.5, 'reformat': False}
        response = self.post('/process/normalize', data)
        process_id = json_decode(response.body)['process']
        response = self.get(
            '/process/normalize/%d/echo_pick_list' % process_id)


if __name__ == '__main__':
    main()
