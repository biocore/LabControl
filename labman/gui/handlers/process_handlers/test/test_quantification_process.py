# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode, json_encode
import numpy as np

from labman.gui.testing import TestHandlerBase


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
        data = {'plate-id': 19,
                'concentrations': json_encode(np.random.rand(8, 12).tolist())}
        response = self.post('/process/quantify', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
