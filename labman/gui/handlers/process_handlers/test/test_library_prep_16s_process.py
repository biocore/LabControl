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


class TestLibraryPrep16SProcessHandlers(TestHandlerBase):
    def test_get_library_prep_16s_process_handler(self):
        response = self.get('/process/library_prep_16S')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/library_prep_16S?plate_id=18')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get(
            '/process/library_prep_16S?plate_id=18&plate_id=19')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_library_prep_16s_process_handler(self):
        data = {'master_mix': '443912', 'water': 'RNBF7110', 'robot': 6,
                'tm300_8_tool': 16, 'tm50_8_tool': 17, 'volume': 10,
                'plates': json_encode([[21, 11]])}
        response = self.post('/process/library_prep_16S', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
