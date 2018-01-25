# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from tornado.escape import json_encode, json_decode

from labman.gui.testing import TestHandlerBase


class TestGDNAPlateCompressionProcessHandlers(TestHandlerBase):
    def test_get_gdna_plate_compression_process_handler(self):
        response = self.get('/process/gdna_compression')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_compression?plate_id=21')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_compression?plate_id=21'
                            '&plate_id=22')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_get_gdna_plate_compression_valid_process_id(self):
        response = self.get('/process/gdna_compression?process_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_compression?process_id=1'
                            '&plate_id=21')
        self.assertEqual(response.code, 400)
        self.assertNotEqual(response.body, '')

    def test_get_gdna_plate_compression_invalid_process_id(self):
        response = self.get('/process/gdna_compression?process_id=1123123123')
        self.assertEqual(response.code, 404)
        self.assertNotEqual(response.body, '')

    def test_post_gdna_plate_compression_process_handler(self):
        data = {'plates': json_encode(['24', '24']),
                'plate_ext_id': 'test_plate_id'}
        response = self.post('/process/gdna_compression', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
