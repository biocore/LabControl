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


class TestLibraryPrepShotgunProcessHandler(TestHandlerBase):
    def test_get_library_prep_shotgun_process_handler(self):
        response = self.get('/process/library_prep_shotgun?plate_id=25')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get(
            '/process/library_prep_shotgun?plate_id=18&plate_id=25')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

        response = self.get('/process/library_prep_shotgun')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_library_prep_shotgun_process_handler(self):
        data = {'plate_name': 'my new plate', 'volume': 50, 'plate': 25,
                'i5_plate': 19, 'i7_plate': 20, 'kappa_hyper_plus_kit': 'KHP1',
                'stub_lot': 'STUBS1'}
        response = self.post('/process/library_prep_shotgun', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


class TestDownloadLibraryPrepShotgunProcessHandler(TestHandlerBase):
    def test_download(self):
        response = self.get(
            '/process/library_prep_shotgun/%d/echo_pick_list' % 1)
        self.assertNotEqual(response.body, '')
        self.assertTrue(response.body.startswith(
            b'Sample\tSource Plate Name\t'))


if __name__ == '__main__':
    main()
