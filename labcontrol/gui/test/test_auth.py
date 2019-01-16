# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labcontrol.gui.testing import TestHandlerBase
from labcontrol.db.user import User
from labcontrol.db.exceptions import LabmanLoginDisabledError


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

    def test_access_handler_get(self):
        response = self.get('/auth/access/')
        self.assertEqual(response.code, 200)
        self.assertNotEqual(response.body, '')

    def test_access_handler_post(self):
        tester = User('shared@foo.bar')
        response = self.post('/auth/access/', {'email': 'shared@foo.bar',
                                               'operation': 'grant'})
        self.assertEqual(response.code, 200)
        self.assertEqual(User.login('shared@foo.bar', 'password'), tester)

        response = self.post('/auth/access/', {'email': 'shared@foo.bar',
                                               'operation': 'revoke'})
        self.assertEqual(response.code, 200)
        with self.assertRaises(LabmanLoginDisabledError):
            User.login('shared@foo.bar', 'password')

        response = self.post('/auth/access/', {'email': 'shared@foo.bar',
                                               'operation': 'unknown'})
        self.assertEqual(response.code, 400)


if __name__ == '__main__':
    main()
