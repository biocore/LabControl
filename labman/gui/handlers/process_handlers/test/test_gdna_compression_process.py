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

        response = self.get('/process/gdna_compression?process_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_compression?process_id=10000')
        self.assertEqual(response.code, 404)

    def test_post_gdna_plate_compression_process_handler(self):
        data = {'plates': json_encode(['22', '22']),
                'plate_ext_id': 'test_plate_id',
                'robot': '1'}
        response = self.post('/process/gdna_compression', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
