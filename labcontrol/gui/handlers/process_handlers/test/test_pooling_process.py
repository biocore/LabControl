# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from tornado.escape import json_decode, json_encode

from labcontrol.gui.testing import TestHandlerBase
from labcontrol.gui.handlers.process_handlers.pooling_process import (
    POOL_FUNCS, HTML_POOL_PARAMS_16S, HTML_POOL_PARAMS_SHOTGUN)


class TestPoolingProcessHandlers(TestHandlerBase):
    def test_html_backend_pairing_16S(self):
        for key, vals in POOL_FUNCS.items():
            pyparams = [html_prefix for _, html_prefix in vals['parameters']]
            htmlpfx = [v['prefix'] for v in HTML_POOL_PARAMS_16S[key]]
            self.assertCountEqual(pyparams, htmlpfx)

    def test_html_backend_pairing_shotgun(self):
        for key, vals in POOL_FUNCS.items():
            pyparams = [html_prefix for _, html_prefix in vals['parameters']]
            htmlpfx = [v['prefix'] for v in HTML_POOL_PARAMS_SHOTGUN[key]]
            self.assertCountEqual(pyparams, htmlpfx)

    def test_get_pool_pool_process_handler(self):
        response = self.get('/process/poolpools')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/poolpools?pool_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/poolpools?process_id=2')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/poolpools?process_id=20000')
        self.assertEqual(response.code, 404)

    def test_post_pool_pool_process_handler(self):
        data = {'pool_name': 'Test pool pool',
                'pools_info': json_encode([
                    {'pool_id': 1, 'concentration': 2.2,
                     'volume': 5, 'percentage': 100}])}
        response = self.post('/process/poolpools', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])

        data = {'pools_info': json_encode([
                    {'pool_id': 1, 'concentration': 2.2,
                     'volume': 5, 'percentage': 100}])}
        response = self.post('/process/poolpools', data)
        self.assertEqual(response.code, 400)

        data = {'pool_name': 'Test pool pool',
                'pools_info': json_encode([])}
        self.assertEqual(response.code, 400)

    def test_get_library_pool_process_handler(self):
        response = self.get('/process/poollibraries')
        self.assertEqual(response.code, 404)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/poollibraries/amplicon_sequencing/')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/poollibraries/shotgun_plate/')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        # plate_id=23 is an amplicon plate, so this should process normally
        response = self.get('/process/poollibraries/amplicon_sequencing/'
                            '?plate_id=23')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        # plate_id=23 is an amplicon plate, so this should process normally
        response = self.get('/process/poollibraries/amplicon_sequencing/'
                            '?plate_id=26')
        self.assertEqual(response.code, 400)
        self.assertRegexpMatches(response.body, rb'Plate type does not match')

        # plate_id=26 is a shotgun plate, so this should process normally
        response = self.get('/process/poollibraries/shotgun_plate/'
                            '?plate_id=26')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        # should get a 400 error from having plates of different type
        response = self.get('/process/poollibraries/amplicon_sequencing/'
                            '?plate_id=23&plate_id=26')
        self.assertEqual(response.code, 400)
        self.assertRegexpMatches(response.body, rb'Plates contain different')
        response = self.get('/process/poollibraries/shotgun_plate/'
                            '?plate_id=23&plate_id=26')
        self.assertEqual(response.code, 400)
        self.assertRegexpMatches(response.body, rb'Plates contain different')

        # process_id=1 corresponds to an amplicon plate, so this retrieve
        # the info
        response = self.get('/process/poollibraries/amplicon_sequencing/'
                            '?process_id=1')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        # process_id=1 corresponds to an amplicon plate, so this should
        # raise an error
        response = self.get('/process/poollibraries/shotgun_plate/'
                            '?process_id=1')
        self.assertEqual(response.code, 400)
        self.assertRegexpMatches(response.body, rb'process type does not '
                                                rb'match')

        # this process id does not exist
        response = self.get('/process/poollibraries/amplicon_sequencing/'
                            '?process_id=10000')
        self.assertEqual(response.code, 404)

        # this process id does not exist
        response = self.get('/process/poollibraries/shotgun_plate/'
                            '?process_id=10000')
        self.assertEqual(response.code, 404)

    def test_post_library_pool_process_handler(self):

        # TODO may want to include test to make sure it is not able to post
        #  plates with the wrong type
        # Shotgun test
        data = {'plates-info': json_encode([{
            'plate-id': 26, 'pool-func': 'equal',
            'plate-type': 'shotgun library prep', 'volume-26': 200,
            'lib-size-26': 500, 'robot-26': 10, 'dest-tube-26': 1,
            'blank-vol-26': '', 'blank-number-26': '',
            'quant-process-id': 5}])}

        response = self.post('/process/poollibraries/shotgun_plate/', data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertEqual(len(obs), 1)
        self.assertCountEqual(obs[0], ['plate-id', 'process-id'])

        # Amplicon test
        data = {'plates-info': json_encode([{
            'plate-id': 23, 'pool-func': 'min',
            'plate-type': '16S library prep',
            'total-23': 240, 'floor-vol-23': 2, 'floor-conc-23': 16,
            'lib-size-23': 500, 'robot-23': 10, 'dest-tube-23': 1,
            'blank-vol-23': 5, 'blank-number-23': 2,
            'quant-process-id': 1}])}
        response = self.post('/process/poollibraries/amplicon_sequencing/',
                             data)
        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        self.assertEqual(len(obs), 1)
        self.assertCountEqual(obs[0], ['plate-id', 'process-id'])

        # Failure amplicon: missing dest-tube-
        data = {'plates-info': json_encode([{
            'plate-id': 23, 'pool-func': 'min',
            'plate-type': '16S library prep',
            'total-23': 240, 'floor-vol-23': 2, 'floor-conc-23': 16,
            'robot-23': 10, 'quant-process-id': 1,
            'blank-vol-23': '', 'blank-number-23': ''}])}
        response = self.post('/process/poollibraries/amplicon_sequencing/',
                             data)
        self.assertEqual(response.code, 400)

        # Failure shotgun: missing lib-size-
        data = {'plates-info': json_encode([{
            'plate-id': 26, 'pool-func': 'equal',
            'plate-type': 'shotgun library prep',
            'quant-process-id': 5,
            'robot-23': 10, 'dest-tube-23': 1, 'volume-26': 200,
            'blank-vol-23': '', 'blank-number-23': ''}])}
        response = self.post('/process/poollibraries/shotgun_plate/', data)
        self.assertEqual(response.code, 400)

    def test_post_compute_library_pool_values_handler(self):
        data = {'plate-info': json_encode({
            'plate-id': 23, 'pool-func': 'min',
            'plate-type': '16S library prep',
            'total-23': 240, 'floor-vol-23': 2, 'floor-conc-23': 16,
            'lib-size-23': 500, 'robot-23': 10, 'dest-tube-23': 1,
            'blank-vol-23': 5, 'blank-number-23': 2,
            'quant-process-id': 1})}
        response = self.post('/process/compute_pool', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body),
                              ['plate_id', 'pool_vals', 'pool_blanks',
                               'plate_names', 'destination', 'robot',
                               'blank_vol', 'blank_num',
                               'total_vol', 'total_conc',
                               'quant-process-id'])

        data = {'plate-info': json_encode({
            'plate-id': 23, 'pool-func': 'min',
            'plate-type': '16S library prep',
            'total-23': 240, 'floor-vol-23': 2, 'floor-conc-23': 16,
            'robot-23': 10, 'quant-process-id': 1,
            'blank-vol-23': 5, 'blank-number-23': 2})}

        response = self.post('/process/compute_pool', data)
        self.assertEqual(response.code, 400)

    def test_get_download_pool_file_handler(self):
        response = self.get("/process/poollibraries/1/pool_file")
        self.assertNotEqual(response.body, '')
        self.assertTrue(response.body.startswith(
            b'Rack,Source,Rack,Destination,Volume,Tool'))
        self.assertEqual(response.headers['Content-Disposition'],
                         "attachment; filename=2017-10-25_"
                         "Test_16S_plate_1_normpool.csv")

        response = self.get("/process/poollibraries/3/pool_file")
        self.assertNotEqual(response.body, '')
        self.assertTrue(response.body.startswith(
            b'Source Plate Name,Source Plate Type,Source Well,Concentration,'))
        self.assertEqual(response.headers['Content-Disposition'],
                         "attachment; filename=2017-10-25_"
                         "Test_shotgun_library_plates_1-4_normpool.csv")

        response = self.get("/process/poollibraries/3000/pool_file")
        self.assertEqual(response.code, 404)


if __name__ == '__main__':
    main()
