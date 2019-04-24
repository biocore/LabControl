# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from bcrypt import hashpw, gensalt, checkpw

from . import base
from . import sql_connection
from . import exceptions


class User(base.LabControlObject):
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
    _table = "qiita.qiita_user"
    _id_column = "email"

    @staticmethod
    def list_users(access_only=False):
        """Return a list of user information

        Parameters
        ----------
        access_only: bool, optional
            Return only users that have access

        Returns
        -------
        list of dict {'email': str, 'name': str}
        """
        with sql_connection.TRN as TRN:
            sql_where = ''
            if access_only:
                sql_where = 'JOIN labman.labmanager_access USING (email)'
            sql = """SELECT DISTINCT email, coalesce(name, email) as name
                     FROM qiita.qiita_user
                     {}
                     ORDER BY name""".format(sql_where)
            TRN.add(sql)
            return [dict(r) for r in TRN.execute_fetchindex()]

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
        LabControlUnknownIdError
            Email is not recognized
        LabControlLoginError
            Provided password doesn't match stored password
        LabControlLoginDisabledError
            If the user doesn't have access to login into LabControl
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT password::bytea
                     FROM qiita.qiita_user
                     WHERE email = %s"""
            TRN.add(sql, [email])
            res = TRN.execute_fetchindex()

            if not res:
                # The email is not recognized
                raise exceptions.LabControlUnknownIdError('User', email)

            sql = """SELECT EXISTS(SELECT *
                                   FROM labman.labmanager_access
                                   WHERE email = %s)"""
            TRN.add(sql, [email])
            if not TRN.execute_fetchlast():
                # The user doesn't have access to login into LabControl
                raise exceptions.LabControlLoginDisabledError()

            db_pwd = res[0][0]
            # Check that the given password matches the one in the DB
            password = cls._encode_password(password)
            # The stored password is returned as a memory view, we simply need
            # to cast it to bytes so we can use it in the checkpw call
            db_pwd = bytes(db_pwd)
            if checkpw(password, db_pwd):
                # Password matches, return the new user object
                return cls(email)
            else:
                # Password didn't match, raise a Login error
                raise exceptions.LabControlLoginError()

    @property
    def name(self):
        """The name of the user"""
        name = self._get_attr('name')

        if name is None:
            return self._get_attr('email')
        else:
            return name

    @property
    def email(self):
        """The email of the user"""
        return self._get_attr('email')

    def grant_access(self):
        """Grants labmanager access to the user"""
        with sql_connection.TRN as TRN:
            sql = """INSERT INTO labman.labmanager_access (email)
                     SELECT %s
                     WHERE NOT EXISTS (SELECT *
                                       FROM labman.labmanager_access
                                       WHERE email = %s)"""
            TRN.add(sql, [self.id, self.id])
            TRN.execute()

    def revoke_access(self):
        """Revokes labmanager access from the user"""
        with sql_connection.TRN as TRN:
            sql = """DELETE FROM labman.labmanager_access
                     WHERE email = %s"""
            TRN.add(sql, [self.id])
            TRN.execute()
