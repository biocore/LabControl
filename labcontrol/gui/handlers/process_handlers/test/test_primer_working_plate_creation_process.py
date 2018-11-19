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


class TestPrimerWorkingPlateCreationProcessHandlers(TestHandlerBase):
    def test_get_primer_working_plate_creation_process_handler(self):
        response = self.get('/process/working_primers')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_post_primer_working_plate_creation_process_handler(self):
        data = {'primer_set': 1, 'master_set_order': 'Some text',
                'plate_name_suffix': 'Something else',
                'creation_date': '01/20/2018'}
        response = self.post('/process/working_primers', data)
        self.assertEqual(response.code, 200)
        self.assertCountEqual(json_decode(response.body), ['process'])


if __name__ == '__main__':
    main()
