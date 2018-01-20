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
        data = {'run_name': 'test_run', 'experiment': 'test_experiment',
                'sequencer_id': 19, 'pools': json_encode([[1, 2, 3]]),
                'fwd_cycles': 0, 'rev_cycles': 0, 'pi': 'admin@foo.bar',
                'contacts': json_encode([['demo@microbio.me',
                                          'shared@foo.bar']])}
        response = self.post('/process/sequencing', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


class TestDownloadSampleSheetHandler(TestHandlerBase):
    def test_get_download_sample_sheet_handler(self):
        print('x')
        # not sure what this function does and how to test it.


if __name__ == '__main__':
    main()
