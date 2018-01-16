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


class TestGDNAExtractionProcessHandlers(TestHandlerBase):
    def test_get_gdna_extraction_process_handler(self):
        response = self.get('/process/gdna_extraction')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_extraction?plate_id=21')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_extraction?plate_id=21&plate_id=22')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_gdna_extraction_process_handler(self):
        data = {'robot': 1, 'tool': 15, 'kit': '157022406', 'volume': 10,
                'plates': json_encode(['21'])}
        response = self.post('/process/gdna_extraction', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
