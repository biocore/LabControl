# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import TestCase
from os.path import dirname, join
from functools import partial

from qiita_client import QiitaClient

import labman
from labman.db.environment import patch_database


def reset_test_db():
    """Resets the test database"""
    with labman.db.sql_connection.TRN as TRN:
        TRN.add("SELECT test FROM settings")
        if not TRN.execute_fetchlast():
            raise RuntimeError(
                "Working on a production environment. Not executing "
                "tests to protect the production database.")
    # Reset the test database to enforce test independence at the class
    # level. The client id and client secret are hardcoded because these
    # should only be used in the test environment. If this fails, it would
    # mean that the Qiita installation is not a test installation
    with TRN:
        TRN.add('DROP SCHEMA IF EXISTS labman CASCADE')
        TRN.execute()
    client_id = '19ndkO3oMKsoChjVVWluF7QkxHRfYhTKSFbAVt8IhK7gZgDaO4'
    client_secret = ('J7FfQ7CQdOxuKhQAf1eoGgBAE81Ns8Gu3EKaWFm3IO2JKh'
                     'AmmCWZuabe0O5Mp28s1')
    qclient = QiitaClient(
        "https://localhost:8383", client_id, client_secret,
        server_cert=labman.db.settings.labman_settings.qiita_server_cert)
    qclient.post("/apitest/reset/")
    # The above call resets the qiita schema. Qiita does not create the
    # labman structures, so create them here
    path_builder = partial(join, dirname(__file__), 'support_files')
    db_patch = path_builder('db_patch.sql')
    db_patch_manual = path_builder('db_patch_manual.sql')
    db_test = path_builder('populate_test_db.sql')
    with TRN:
        with open(db_patch, 'r') as f:
            TRN.add(f.read())
        with open(db_patch_manual, 'r') as f:
            TRN.add(f.read())
        with open(db_test, 'r') as f:
            TRN.add(f.read())
        TRN.execute()

    patch_database(verbose=False)


class LabmanTestCase(TestCase):
    _perform_reset = True

    def do_not_reset_at_teardown(self):
        self.__class__._perform_reset = False

    @classmethod
    def tearDownClass(cls):
        if cls._perform_reset:
            reset_test_db()
        else:
            cls._perform_reset = True
