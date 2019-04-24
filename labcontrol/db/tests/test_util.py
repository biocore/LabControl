# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labcontrol.db.testing import LabControlTestCase

from labcontrol.db.composition import PoolComposition
from labcontrol.db.util import get_pools_listing


class TestUtil(LabControlTestCase):
    def test_get_pools_listing(self):
        exp = [[p.id, p.container.external_id,
                p.is_plate_pool, p.upstream_process.id]
               for p in PoolComposition.get_pools()]
        obs = get_pools_listing()
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
