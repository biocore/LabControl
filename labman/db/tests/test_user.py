# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.exceptions import (LabmanDuplicateError, LabmanUnknownIdError,
                                  LabmanLoginError)
from labman.db.testing import LabmanTestCase, qiita_skip_test
from labman.db.user import User


class TestUser(LabmanTestCase):
    def test_init(self):
        with self.assertRaises(LabmanUnknownIdError):
            User(10000)

    def test_hash_password(self):
        obs = User._hash_password('password')
        self.assertNotEqual(obs, 'password')
        self.assertEqual(User._hash_password('password', obs), obs)

    def test_create(self):
        obs = User.create('create@test.foo', 'Test User', 'Password')
        self.assertEqual(obs.email, 'create@test.foo')
        self.assertEqual(obs.name, 'Test User')
        self.assertEqual(obs.access_levels, [])

        with self.assertRaises(LabmanDuplicateError):
            User.create('create@test.foo', 'Same email as before', 'Password')

    @qiita_skip_test()
    def test_create_qiita(self):
        obs = User.create('test@foo.bar', 'Test User', 'Password')
        self.assertEqual(obs.email, 'test@foo.bar')

        # TODO: Uncomment this test once the connection with qiita is
        # established. The given email doesn't exist in Qiita so it should fail
        # with self.assertRaises(LabmanUnknownIdError):
        #     User.create('does@not.exist', 'Test User', 'Password')

    def test_from_email(self):
        exp = User.create('from@email.foo', 'Test user', 'password')
        obs = User.from_email('from@email.foo')
        self.assertEqual(obs, exp)

        with self.assertRaises(LabmanUnknownIdError):
            User.from_email('does@not.exist')

    def test_login(self):
        exp = User.create('login@foo.bar', 'Login user', 'password')
        obs = User.login('login@foo.bar', 'password')
        self.assertEqual(obs, exp)

        with self.assertRaises(LabmanUnknownIdError):
            User.login('does@not.exist', 'password')

        with self.assertRaises(LabmanLoginError):
            User.login('login@foo.bar', 'wrongpassword')

    def test_exist(self):
        self.assertFalse(User.exists(10000))
        obs = User.create('exist@foo.bar', 'exist user', 'password')
        self.assertTrue(User.exists(obs.id))


if __name__ == '__main__':
    main()
