# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import TestCase
from os.path import dirname, join
from functools import partial

from qiita_client import QiitaClient

import labcontrol


def reset_test_db():
    """Resets the test database"""
    with labcontrol.db.sql_connection.TRN as TRN:
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
        TRN.add('DROP SCHEMA IF EXISTS labcontrol CASCADE')
        TRN.execute()
    client_id = '19ndkO3oMKsoChjVVWluF7QkxHRfYhTKSFbAVt8IhK7gZgDaO4'
    client_secret = ('J7FfQ7CQdOxuKhQAf1eoGgBAE81Ns8Gu3EKaWFm3IO2JKh'
                     'AmmCWZuabe0O5Mp28s1')
    qclient = QiitaClient(
        "https://localhost:21174", client_id, client_secret,
        server_cert=labcontrol.db.settings.labcontrol_settings.qiita_server_cert)
    qclient.post("/apitest/reset/")
    # The above call resets the qiita schema. Qiita does not create the
    # labcontrol structures, so create them here
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


class LabcontrolTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        reset_test_db()
