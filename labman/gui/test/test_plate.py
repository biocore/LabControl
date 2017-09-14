# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.gui.testing import TestHandlerBase


class TestPlateHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/plate')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')


class TestPlateNameHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/platename')
        # It is missing the parameter
        self.assertEqual(response.code, 400)
        # It doesn't exist
        response = self.get('/platename?new-name=something')
        self.assertEqual(response.code, 404)
        # It exists
        response = self.get('/platename?new-name=exists')
        self.assertEqual(response.code, 200)
        # Error
        response = self.get('/platename?new-name=error')
        self.assertEqual(response.code, 500)
        self.assertNotEqual(response.body, '')


if __name__ == '__main__':
    main()
