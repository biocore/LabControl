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

from labman.db.settings import labman_settings
from labman.db.sql_connection import TRN


class LabmanTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        with TRN:
            TRN.add("SELECT test FROM settings")
            if not TRN.execute_fetchlast():
                raise RuntimeError(
                    "Working on a production environment. Not executing "
                    "tests to protect the production database.")
        # Reset the test database to enforce test independence at the class
        # level. The client id and client secret are hardcoded because these
        # should only be used in the test environment. If this fails, it would
        # mean that the Qiita installation is not a test installation
        client_id = '19ndkO3oMKsoChjVVWluF7QkxHRfYhTKSFbAVt8IhK7gZgDaO4'
        client_secret = ('J7FfQ7CQdOxuKhQAf1eoGgBAE81Ns8Gu3EKaWFm3IO2JKh'
                         'AmmCWZuabe0O5Mp28s1')
        qclient = QiitaClient(
            "https://localhost:21174", client_id, client_secret,
            server_cert=labman_settings.qiita_server_cert)
        qclient.post("/apitest/reset/")
        # The above call resets the qiita schema. Qiita does not create the
        # labman structures, so create them here
        path_builder = partial(join, dirname(__file__), 'support_files')
        db_patch = path_builder('db_patch.sql')
        db_patch_manual = path_builder('db_patch_manual.sql')
        with TRN:
            with open(db_patch, 'r') as f:
                TRN.add(f.read())
            with open(db_patch_manual, 'r') as f:
                TRN.add(f.read())
            TRN.execute()
