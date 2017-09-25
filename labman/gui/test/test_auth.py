# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.gui.testing import TestHandlerBase


class TestAuthHandlers(TestHandlerBase):
    def test_login_handler_get(self):
        response = self.get('/auth/login/')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, "")

    def test_login_handler_post(self):
        # Test Success
        data = {'username': 'test@foo.bar',
                'password': 'password'}
        response = self.post('/auth/login/', data)
        self.assertEqual(response.code, 200)
        self.assertNotIn(b'Unknown user name', response.body)
        self.assertNotIn(b'Incorrect password', response.body)

        # Test unknown user
        data = {'username': 'unknown@user.foo',
                'password': 'password'}
        response = self.post('/auth/login/', data)
        self.assertEqual(response.code, 200)
        self.assertIn(b'Unknown user name', response.body)

        # Test incorrect password
        data = {'username': 'test@foo.bar',
                'password': 'wrongpwd'}
        response = self.post('/auth/login/', data)
        self.assertEqual(response.code, 200)
        self.assertIn(b'Incorrect password', response.body)

    def test_logout_handler_get(self):
        response = self.get('/auth/logout/')
        self.assertEqual(response.code, 200)


if __name__ == '__main__':
    main()
