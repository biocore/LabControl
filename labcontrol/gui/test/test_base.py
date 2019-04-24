# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labcontrol.gui.testing import TestHandlerBase


class TestIndexHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')


class TestNotFoundHandler(TestHandlerBase):
    def test_get(self):
        response = self.get('/TRIGGER404/')
        self.assertEqual(response.code, 404)
        self.assertIn(b'404: Page not found!', response.body)


if __name__ == '__main__':
    main()
