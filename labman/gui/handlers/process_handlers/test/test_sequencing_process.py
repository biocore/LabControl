# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import zipfile

from io import BytesIO
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
        # amplicon sequencing process
        response = self.get('/process/sequencing/1/sample_sheet')
        self.assertNotEqual(response.body, '')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.startswith(b'# PI,Dude,test@foo.bar\n'))
        self.assertEqual(response.headers['Content-Disposition'],
                         "attachment; filename=2017-10-25_samplesheet"
                         "_Test_Run.1.csv")

        # shotgun sequencing process
        response = self.get('/process/sequencing/2/sample_sheet')
        self.assertNotEqual(response.body, '')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.startswith(b'# PI,Dude,test@foo.bar\n'))
        self.assertEqual(response.headers['Content-Disposition'],
                         "attachment; filename=2017-10-25_samplesheet_"
                         "TestShotgunRun1_TestExperimentShotgun1.csv")

    def test_get_download_preparation_sheet_handler(self):
        response = self.get('/process/sequencing/1/preparation_sheets')
        self.assertNotEqual(response.body, '')
        self.assertEqual(response.code, 200)

        self.assertEqual(response.headers['Content-Type'], 'application/zip')
        self.assertEqual(response.headers['Expires'], '0')
        self.assertEqual(response.headers['Cache-Control'], 'no-cache')
        self.assertEqual(response.headers['Content-Disposition'],
                         'attachment; filename=2017-10-25_preps'
                         '_Test_Run.1.zip')

        expected_files = ['2017-10-25_prep_Test_Run.1_1.txt',
                          '2017-10-25_prep_Test_Run.1_controls.txt']
        archive = zipfile.ZipFile(BytesIO(response.body), 'r')
        self.assertEqual(archive.namelist(), expected_files)

        # NB: All the below does is test that the files in the archive have
        # SOME non-empty content--it doesn't check what that content IS.
        for curr_file_name in expected_files:
            contents = archive.open(curr_file_name).read()
            self.assertNotEqual(contents, '')


if __name__ == '__main__':
    main()
