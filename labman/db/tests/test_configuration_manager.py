# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from tempfile import NamedTemporaryFile

from labman.db.configuration_manager import ConfigurationManager
from labman.db.testing import LabmanTestCase


class TestConfigurationManager(LabmanTestCase):
    def test_create(self):
        with NamedTemporaryFile() as tmp_f:
            ConfigurationManager.create(
                tmp_f.name, True, 'db_host', 'db_port', 'db_name', 'db_user',
                'db_password', 'db_admin_user', 'db_admin_password', False)

            with open(tmp_f.name) as obs_f:
                obs = obs_f.read()

            obs = obs.splitlines()
            exp = EXP_CONFIG_FILE.splitlines()

            # Removing the first line as it contains a date that is generated
            # when the test is run
            self.assertEqual(obs[1:], exp)

    def test_create_qiita(self):
        with NamedTemporaryFile() as tmp_f:
            ConfigurationManager.create(
                tmp_f.name, True, 'db_host', 'db_port', 'db_name', 'db_user',
                'db_password', 'db_admin_user', 'db_admin_password', True,
                'https://localhost:21174', 'client_id', 'client_secret',
                'server_cert')

            with open(tmp_f.name) as obs_f:
                obs = obs_f.read()

            obs = obs.splitlines()
            exp = EXP_CONFIG_FILE_QIITA.splitlines()

            # Removing the first line as it contains a date that is generated
            # when the test is run
            self.assertEqual(obs[1:], exp)


EXP_CONFIG_FILE = """
# ------------------------- MAIN SETTINGS ----------------------------------
[main]
TEST_ENVIRONMENT=True

# ----------------------- POSTGRES SETTINGS --------------------------------
[postgres]
USER=db_user
PASSWORD=db_password
ADMIN_USER=db_admin_user
ADMIN_PASSWORD=db_admin_password
DATABASE=db_name
HOST=db_host
PORT=db_port

# ------------------------- QIITA SETTINGS ----------------------------------
[qiita]
ENABLE_QIITA=False
HOST=
CLIENT_ID=
CLIENT_SECRET=
SERVER_CERT=
"""

EXP_CONFIG_FILE_QIITA = """
# ------------------------- MAIN SETTINGS ----------------------------------
[main]
TEST_ENVIRONMENT=True

# ----------------------- POSTGRES SETTINGS --------------------------------
[postgres]
USER=db_user
PASSWORD=db_password
ADMIN_USER=db_admin_user
ADMIN_PASSWORD=db_admin_password
DATABASE=db_name
HOST=db_host
PORT=db_port

# ------------------------- QIITA SETTINGS ----------------------------------
[qiita]
ENABLE_QIITA=True
HOST=https://localhost:21174
CLIENT_ID=client_id
CLIENT_SECRET=client_secret
SERVER_CERT=server_cert
"""


if __name__ == '__main__':
    main()
