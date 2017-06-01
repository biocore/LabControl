# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from bcrypt import hashpw, gensalt, checkpw

from labman.db.settings import labman_settings
from labman.db.sql_connection import TRN
from labman.db.base import LabmanObject
from labman.db.exceptions import (LabmanUnknownIdError, LabmanDuplicateError,
                                  LabmanLoginError)


class User(LabmanObject):
    """User object

    Attributes
    ----------
    id
    name
    email
    access_level

    Methods
    -------
    create
    """
    _table = "users.user"
    _id_column = "user_id"

    @staticmethod
    def _encode_password(password):
        return password if isinstance(password, bytes) \
            else password.encode('utf-8')

    @staticmethod
    def _hash_password(password, hashed_pwd=None):
        """Hashes password

        Parameters
        ----------
        password : str
            The password to be hashed
        hashed_pwd : str, optional
            Previously hashed password to pull salt from. If not provided,
            a new salt will be generated

        Returns
        -------
        str
            The hashed password
        """
        # bcrypt requires password to be bytes
        password = User._encode_password(password)
        hashed_pwd = hashed_pwd if hashed_pwd is not None else gensalt()
        return hashpw(password, hashed_pwd)

    @classmethod
    def create(cls, email, name, password):
        """Creates a new user in the system

        Parameters
        ----------
        email : str
            The email of the user
        name : str
            The name of the user
        password : str
            The password of the user
        qiita_user : str, optional
            The user id

        Returns
        -------
        User
            The newly created user
        """
        with TRN:
            # Check if the email is unique or not
            if cls._attr_exists('email', email):
                raise LabmanDuplicateError('User', [('email', email)])

            # Check if labman is configured with Qiita
            if labman_settings.qiita_enabled:
                # Check if the qiita email exists in Qiita
                # TODO: Currently, there is no way of checking if a given user
                # id exists in Qiita or not. Commented is the pseudocode to
                # implement this. Change exist_qiita_user for the actual check
                # against Qiita
                # if not exist_qiita_user():
                #     raise LabmanUnknownIdError('Qiita User',
                #                                [('email', email)])
                pass
            # Hash password
            password = cls._hash_password(password)
            # Insert in the DB
            sql = """INSERT INTO users.user (email, name, password)
                        VALUES (%s, %s, %s)
                        RETURNING user_id"""
            TRN.add(sql, [email, name, password])
            user_id = TRN.execute_fetchlast()
            # Return new object
            return cls(user_id)

    @classmethod
    def from_email(cls, email):
        """Instantiates the user object from the given email

        Parameters
        ----------
        email : str
            The user email

        Raises
        ------
        LabmanUnknownIdError
            Email is not recognized
        """
        with TRN:
            sql = "SELECT user_id FROM users.user WHERE email = %s"
            TRN.add(sql, [email])
            user_id = TRN.execute_fetchlast()
            if not user_id:
                # The email is not recognized
                raise LabmanUnknownIdError('User', [('email', email)])
            return cls(user_id)

    @classmethod
    def login(cls, email, password):
        """Logs a user into the system

        Parameters
        ----------
        email : str
            The user email
        password: str
            The password of the user

        Returns
        -------
        User
            The User object corresponding to the login information

        Raises
        ------
        LabmanUnknownIdError
            Email is not recognized
        LabmanLoginError
            Provided password doesn't match stored password
        """
        with TRN:
            sql = "SELECT password FROM users.user WHERE email = %s"
            TRN.add(sql, [email])
            db_pwd = TRN.execute_fetchlast()
            if not db_pwd:
                # The email is not recognized
                raise LabmanUnknownIdError('User', [('email', email)])
            # Check that the given password matches the one in the DB
            password = cls._encode_password(password)
            # The stored password is returned as a memory view, we simply need
            # to cast it to bytes so we can use it in the checkpw call
            db_pwd = bytes(db_pwd)
            if checkpw(password, db_pwd):
                # Password matches, return the new user object
                return cls.from_email(email)
            else:
                # Password didn't match, raise a Login error
                raise LabmanLoginError()

    @property
    def name(self):
        """The name of the user"""
        with TRN:
            sql = "SELECT name FROM users.user WHERE user_id = %s"
            TRN.add(sql, [self._id])
            return TRN.execute_fetchlast()

    @property
    def email(self):
        """The email of the user"""
        with TRN:
            sql = "SELECT email FROM users.user WHERE user_id = %s"
            TRN.add(sql, [self._id])
            return TRN.execute_fetchlast()

    @property
    def access_levels(self):
        """The access levels of the user"""
        with TRN:
            sql = """SELECT access_level
                     FROM users.access_level
                        JOIN users.user_access_level USING (access_level_id)
                     WHERE user_id = %s"""
            TRN.add(sql, [self._id])
            return TRN.execute_fetchflatten()
