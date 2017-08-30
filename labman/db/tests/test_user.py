# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.exceptions import LabmanUnknownIdError, LabmanLoginError
from labman.db.testing import LabmanTestCase
from labman.db.user import User


class TestUser(LabmanTestCase):
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

    def test_exist(self):
        self.assertFalse(User.exists('does@not.exist'))
        self.assertTrue(User.exists('test@foo.bar'))

    def test_attributes(self):
        tester = User('test@foo.bar')
        self.assertEqual(tester.name, 'Dude')
        self.assertEqual(tester.email, 'test@foo.bar')


if __name__ == '__main__':
    main()
