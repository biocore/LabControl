# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode,json_encode

from labman.gui.testing import TestHandlerBase


class TestPoolingProcessHandlers(TestHandlerBase):
    def test_get_pool_pool_process_handler(self):
        response = self.get('/process/poolpools')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/poolpools?pool_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_pool_pool_process_handler(self):
        data = {'pool_name': 'Test pool pool',
                'pools_info': json_encode([
                    {'pool_id': 1, 'concentration': 2.2,
                     'volume': 5, 'percentage': 100}])}
        response = self.post('/process/poolpools', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
