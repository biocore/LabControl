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


class TestSequenceRunListHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/sequence_run_list')

        self.assertEqual(response.code, 200)
        obs = json_decode(response.body)
        exp = {'data': [[18,
                         'Test Run.1',
                         'TestExperiment1',
                         'Amplicon',
                         'test@foo.bar',
                         1],
                        [25,
                         'TestShotgunRun1',
                         'TestExperimentShotgun1',
                         'Metagenomics',
                         'test@foo.bar',
                         2],
                        [26,
                         'TestNewRun1',
                         'TestExperimentNew1',
                         'NewKindOfAssay',
                         'test@foo.bar',
                         3],
                        ]}
        self.assertEqual(obs, exp)


class TestSequenceRunListingHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/sequence_runs')

        self.assertEqual(response.code, 200)
        self.assertIn('Sequence run id', response.body.decode('utf8'))


if __name__ == '__main__':
    main()
