# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.configuration_manager import ConfigurationManager

# Singleton pattern, create the configuration object for the entire system
labman_settings = ConfigurationManager()
