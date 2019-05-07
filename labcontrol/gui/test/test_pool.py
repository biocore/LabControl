# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------


from unittest import main
from tornado.escape import json_decode
from labcontrol.gui.testing import TestHandlerBase


class TestPoolHandlers(TestHandlerBase):
    def test_get_pool_list_handler_all(self):
        response = self.get('/pool_list/all/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 6)
        self.assertEqual(obs_data[0], [1, 'Test Pool from Plate 1',
                                       True, True, 1])
        self.assertEqual(obs_data[1], [2, 'Test sequencing pool 1',
                                       False, False, 2])
        self.assertEqual(obs_data[2], [3, 'Test pool from Shotgun plates 1-4',
                                       True, False, 3])
        self.assertEqual(obs_data[3], [4, 'Test Pool from Plate 2',
                                       True, True, 4])
        self.assertEqual(obs_data[4], [5, 'Test Pool from Plate 3',
                                       True, True, 5])
        self.assertEqual(obs_data[5], [6, 'Test Pool from Plate 4',
                                       True, True, 6])

    def test_get_pool_list_handler_amplicon_plate(self):
        response = self.get('/pool_list/amplicon_plate/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 4)
        self.assertEqual(obs_data[0], [1, 'Test Pool from Plate 1',
                                       True, True, 1])
        self.assertEqual(obs_data[1], [4, 'Test Pool from Plate 2',
                                       True, True, 4])
        self.assertEqual(obs_data[2], [5, 'Test Pool from Plate 3',
                                       True, True, 5])
        self.assertEqual(obs_data[3], [6, 'Test Pool from Plate 4',
                                       True, True, 6])

    def test_get_pool_list_handler_amplicon_sequencing(self):
        response = self.get('/pool_list/amplicon_sequencing/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(obs_data[0], [2, 'Test sequencing pool 1',
                                       False, False, 2])

    def test_get_pool_list_handler_shotgun_plate(self):
        response = self.get('/pool_list/shotgun_plate/')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 1)
        self.assertEqual(obs_data[0], [3, 'Test pool from Shotgun plates 1-4',
                                       True, False, 3])

    def test_get_pool_list_handler_unknown(self):
        response = self.get('/pool_list/minipcr/')
        self.assertEqual(response.code, 500)


if __name__ == '__main__':
    main()
