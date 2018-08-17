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


class TestPoolHandlers(TestHandlerBase):
    def test_get_plate_list_handler(self):
        response = self.get('/pool_list')
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertCountEqual(obs.keys(), ['data'])
        obs_data = obs['data']
        self.assertEqual(len(obs_data), 6)
        self.assertEqual(obs_data[0], [1, 'Test Pool from Plate 1', True, 1])
        self.assertEqual(obs_data[1], [2, 'Test sequencing pool 1', False, 2])
        self.assertEqual(obs_data[2], [3, 'Test pool from Shotgun plates 1-4',
                                       True, 3])
        self.assertEqual(obs_data[3], [4, 'Test Pool from Plate 2', True, 4])
        self.assertEqual(obs_data[4], [5, 'Test Pool from Plate 3', True, 5])
        self.assertEqual(obs_data[5], [6, 'Test Pool from Plate 4', True, 6])


if __name__ == '__main__':
    main()
