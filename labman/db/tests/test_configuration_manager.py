# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import TestCase, main
from tempfile import NamedTemporaryFile

from labman.db.configuration_manager import ConfigurationManager


class TestConfigurationManager(TestCase):
    def test_create(self):
        with NamedTemporaryFile() as tmp_f:
            ConfigurationManager.create(
                tmp_f.name, True, 'db_host', 'db_port', 'db_name', 'db_user',
                'db_password', 'db_admin_user', 'db_admin_password')

            with open(tmp_f.name) as obs_f:
                obs = obs_f.read()

            obs = obs.splitlines()
            exp = EXP_CONFIG_FILE.splitlines()

            # Removing the first line as it contains a date that is generated
            # when the test is run
            self.assertEqual(obs[1:], exp)


EXP_CONFIG_FILE = """
# ------------------------- MAIN SETTINGS ----------------------------------
[main]
TEST_ENVIRONMENT = True

# ----------------------- POSTGRES SETTINGS --------------------------------
[postgres]
USER = db_user
PASSWORD = db_password
ADMIN_USER = db_admin_user
ADMIN_PASSWORD = db_admin_password
DATABASE = db_name
HOST = db_host
PORT = db_port
"""


if __name__ == '__main__':
    main()
