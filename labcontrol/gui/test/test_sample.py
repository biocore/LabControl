# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode

from labcontrol.gui.testing import TestHandlerBase
from labcontrol.db.composition import SampleComposition


class TestSampleHandlers(TestHandlerBase):
    def test_get_control_samples_handler(self):
        response = self.get('/sample/control')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['blank', 'empty', 'vibrio.positive.control', 'zymo.mock']
        self.assertEqual(obs, exp)

        response = self.get('/sample/control?term=B')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['blank', 'vibrio.positive.control']
        self.assertEqual(obs, exp)

        response = self.get('/sample/control?term=BL')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = ['blank']
        self.assertEqual(obs, exp)


class TestManageControlsHandler(TestHandlerBase):
    def test_get_manage_controls_handler(self):
        response = self.get('/sample/manage_controls')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_manage_controls_handler(self):
        response = self.post(
            '/sample/manage_controls', {'external_id': 'zzTestControl',
                                        'description': 'A test control'})
        self.assertEqual(response.code, 200)
        obs = SampleComposition.get_control_sample_types_description()
        exp = [
            {'external_id': 'blank',
             'description': 'gDNA extraction blanks. Represents an empty '
                            'extraction well.'},
            {'external_id': 'empty',
             'description': 'Empty well. Represents an empty well that should '
                            'not be included in library preparation.'},
            {'external_id': 'vibrio.positive.control',
             'description': 'Bacterial isolate control (Vibrio fischeri ES114)'
                            '. Represents an extraction well loaded with '
                            'Vibrio.'},
            {'external_id': 'zymo.mock',
             'description': 'Bacterial community control (Zymo Mock D6306). '
                            'Represents an extraction well loaded with Zymo '
                            'Mock community.'},
            {'external_id': 'zzTestControl', 'description': 'A test control'}]
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
