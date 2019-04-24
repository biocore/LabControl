# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode, json_encode
import numpy as np

from labcontrol.gui.testing import TestHandlerBase


class TestQuantificationProcessHandlers(TestHandlerBase):
    def test_get_quantification_process_parse_handler(self):
        response = self.get('/process/parse_quantify')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/parse_quantify?plate_id=19')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_quantification_process_parse_handler(self):
        # In this test we should be uploading a file - but I couldn't
        # find how to emulate this
        pass

    def test_post_quantification_process_handler(self):
        plates_info = [{'plate_id': 22, 'plate_name': 'Test gDNA plate 1',
                        'concentrations': np.random.rand(8, 12).tolist()}]
        data = {'plates-info': json_encode(plates_info)}
        response = self.post('/process/quantify', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['processes'])

    def test_get_quantification_process_view_handler(self):
        plate = 26
        response = self.get('/process/view_quants/%s' % plate)

        self.assertEqual(response.code, 200)


if __name__ == '__main__':
    main()
