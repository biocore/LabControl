# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from tornado.escape import json_encode, json_decode

from labcontrol.gui.testing import TestHandlerBase


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

        response = self.get(
            '/process/library_prep_16S?process_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get(
            '/process/library_prep_16S?process_id=10000')
        self.assertEqual(response.code, 404)

    def test_post_library_prep_16s_process_handler(self):
        data = {'preparation_date': '01/20/2018', 'volume': 75,
                'plates_info': json_encode(
                    [[22, 'New Plate', 11, 6, 16, 17, '443912', 'RNBF7110']])}
        response = self.post('/process/library_prep_16S', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['processes'])


if __name__ == '__main__':
    main()
