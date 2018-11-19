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

        response = self.get('/process/gdna_extraction?process_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/gdna_extraction?process_id=1000')
        self.assertEqual(response.code, 404)

    def test_post_gdna_extraction_process_handler(self):
        data = {'extraction_date': '01/20/2018', 'volume': 10,
                'plates_info': json_encode(
                    [['21', False, 11, 6, 15, '157022406',
                      'new gdna plate', None]])}
        response = self.post('/process/gdna_extraction', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['processes'])

        data = {'extraction_date': '01/20/2018', 'volume': 10,
                'plates_info': json_encode(
                    [['21', True, None, None, None, None,
                      'externally extracted gdna plate',
                      'Extracted externally']])}
        response = self.post('/process/gdna_extraction', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['processes'])


if __name__ == '__main__':
    main()
