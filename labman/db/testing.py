# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import TestCase, skipIf

from labman.db.environment_manager import (
    is_test_environment, reset_test_database)
from labman.db.settings import labman_settings


class LabmanTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        if not is_test_environment():
            raise RuntimeError(
                "Working on a production environment. Not executing tests to "
                "protect the production database.")
        # Reset the test database to enforce test independence at the class
        # level
        reset_test_database()


def qiita_skip_test():
    """Decorator to use to mark tests that should be skipped when labman
    is not configured to run with Qiita
    """
    return skipIf(not labman_settings.qiita_enabled,
                  "Current labman installation is not Qiita enabled")
