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


class TestSampleHandlers(TestHandlerBase):
    def test_get_control_samples_handler(self):
        response = self.get('/sample/control')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['BLANK', 'VIBRIO', 'MOCK1']
        self.assertEqual(obs, exp)

        response = self.get('/sample/control?term=B')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['BLANK', 'VIBRIO']
        self.assertEqual(obs, exp)

        response = self.get('/sample/control?term=BL')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['BLANK']
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
