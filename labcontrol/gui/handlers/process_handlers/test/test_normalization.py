# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from tornado.escape import json_decode, json_encode

from labcontrol.gui.testing import TestHandlerBase


class TestNormalizationHandlers(TestHandlerBase):
    def test_normalization_handler(self):
        response = self.get('/process/normalize?plate_id=23')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/normalize?plate_id=21&plate_id=23')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/normalize')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/normalize?process_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/normalize?process_id=1000')
        self.assertEqual(response.code, 404)

    def test_post_normalization_handler(self):
        data = {'plates_info': json_encode([[23, '157022406', 1]]),
                'water': 'RNBF7110', 'total_vol': 3500, 'ng': 5,
                'min_vol': 2.5, 'max_vol': 3500, 'resolution': 2.5,
                'reformat': False}
        response = self.post('/process/normalize', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['processes'])

    def test_get_download_normalization_process_handler(self):
        response = self.get('/process/normalize/1/echo_pick_list')
        self.assertNotEqual(response.body, '')
        self.assertTrue(response.body.startswith(
            b'Sample\tSource Plate Name\t'))
        self.assertEqual(response.headers['Content-Type'], "text/csv")
        self.assertEqual(response.headers['Expires'], "0")
        self.assertEqual(response.headers['Cache-Control'], "no-cache")
        self.assertEqual(response.headers['Content-Disposition'],
                         "attachment; filename=2017-10-25_"
                         "Test_compressed_gDNA_plates_1-4_input_norm.txt")


if __name__ == '__main__':
    main()
