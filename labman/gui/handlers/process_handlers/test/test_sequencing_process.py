# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from tornado.escape import json_encode, json_decode

from labman.gui.testing import TestHandlerBase


class TestSequencingProcessHandler(TestHandlerBase):
    def test_get_sequencing_process_handler(self):
        response = self.get('/process/sequencing')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_sequencing_process_handler(self):
        data = {'pools': json_encode([1, 2]), 'run_name': 'test_run',
                'experiment': 'test_experiment',
                'sequencer': 19, 'fwd_cycles': 150, 'rev_cycles': 150,
                'principal_investigator': 'admin@foo.bar',
                'additional_contacts': json_encode(
                    ['demo@microbio.me', 'shared@foo.bar'])}
        response = self.post('/process/sequencing', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])

    def test_get_download_sample_sheet_handler(self):
        response = self.get('/process/sequencing/1/sample_sheet')
        self.assertNotEqual(response.body, '')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.startswith(b'# PI,Dude,test@foo.bar\n'))

    def test_get_download_preparation_sheet_handler(self):
        response = self.get('process/sequencing/1/preparation_sheets')
        self.assertNotEqual(response.body, '')
        self.assertEqual(response.code, 200)

        self.assertEqual(response.headers['Content-Type'], 'application/zip')
        self.assertEqual(response.headers['Expires'], '0')
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')
        self.assertEqual(response.headers['Content-Disposition'],
                         'attachment; filename=')


if __name__ == '__main__':
    main()
