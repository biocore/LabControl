# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.exceptions import (
    LabmanUnknownIdError, LabmanLoginError, LabmanLoginDisabledError)
from labman.db.testing import LabmanTestCase
from labman.db.user import User


class TestUser(LabmanTestCase):
    def test_list_users(self):
        exp = [{'email': 'admin@foo.bar', 'name': 'Admin'},
               {'email': 'demo@microbio.me', 'name': 'Demo'},
               {'email': 'test@foo.bar', 'name': 'Dude'},
               {'email': 'LabmanSystem@labman.com',
                'name': 'LabmanSystem@labman.com'},
               {'email': 'shared@foo.bar', 'name': 'Shared'}]
        self.assertEqual(User.list_users(), exp)

        exp = [{'email': 'admin@foo.bar', 'name': 'Admin'},
               {'email': 'demo@microbio.me', 'name': 'Demo'},
               {'email': 'test@foo.bar', 'name': 'Dude'},
               {'email': 'LabmanSystem@labman.com',
                'name': 'LabmanSystem@labman.com'}]
        self.assertEqual(User.list_users(access_only=True), exp)

    def test_init(self):
        with self.assertRaises(LabmanUnknownIdError):
            User('Dude')

    def test_hash_password(self):
        obs = User._hash_password('password')
        self.assertNotEqual(obs, 'password')
        self.assertEqual(User._hash_password('password', obs), obs)

    def test_login(self):
        exp = User('test@foo.bar')
        obs = User.login('test@foo.bar', 'password')
        self.assertEqual(obs, exp)

        with self.assertRaises(LabmanUnknownIdError):
            User.login('does@not.exist', 'password')

        with self.assertRaises(LabmanLoginError):
            User.login('test@foo.bar', 'wrongpassword')

        with self.assertRaises(LabmanLoginDisabledError):
            User.login('shared@foo.bar', 'password')

    def test_exist(self):
        self.assertFalse(User.exists('does@not.exist'))
        self.assertTrue(User.exists('test@foo.bar'))

    def test_attributes(self):
        tester = User('test@foo.bar')
        self.assertEqual(tester.name, 'Dude')
        self.assertEqual(tester.email, 'test@foo.bar')

    def test_grant_revoke_access(self):
        tester = User('shared@foo.bar')
        with self.assertRaises(LabmanLoginDisabledError):
            User.login('shared@foo.bar', 'password')

        tester.grant_access()
        obs = User.login('shared@foo.bar', 'password')
        self.assertEqual(obs, tester)

        tester.revoke_access()
        with self.assertRaises(LabmanLoginDisabledError):
            User.login('shared@foo.bar', 'password')


if __name__ == '__main__':
    main()
