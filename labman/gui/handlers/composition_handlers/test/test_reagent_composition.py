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


class TestReagentCompositionHandlers(TestHandlerBase):
    def test_get_reagent_composition_list_handler(self):
        response = self.get('/composition/reagent')
        self.assertEqual(response.code, 200)
        self.assertEqual(json_decode(response.body)[:5],
                         ['157022406', '443912', 'KHP1', 'RNBF7110', 'STUBS1'])

        response = self.get('/composition/reagent?reagent_type=water')
        self.assertEqual(response.code, 200)
        self.assertEqual(json_decode(response.body), ['RNBF7110'])

        response = self.get('/composition/reagent?term=2')
        self.assertEqual(response.code, 200)
        self.assertEqual(json_decode(response.body), ['157022406', '443912'])

        response = self.get(
            '/composition/reagent?reagent_type=extraction%20kit&term=2')
        self.assertEqual(response.code, 200)
        self.assertEqual(json_decode(response.body), ['157022406'])

    def test_post_reagent_composition_list_handler(self):
        data = {'external_id': 'ZZZZTEST', 'volume': '10',
                'reagent_type': 'extraction kit'}
        response = self.post('/composition/reagent', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])

        response = self.get('/composition/reagent')
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json_decode(response.body),
            ['157022406', '443912', 'KHP1', 'RNBF7110', 'STUBS1', 'ZZZZTEST'])


if __name__ == '__main__':
    main()
