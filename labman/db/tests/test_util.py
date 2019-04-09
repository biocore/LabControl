# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase

from labman.db.composition import PoolComposition
from labman.db.util import get_pools_listing


class TestUtil(LabmanTestCase):
    def test_get_pools_listing(self):
        exp = [[p.id, p.container.external_id,
                p.is_plate_pool, p.upstream_process.id]
               for p in PoolComposition.get_pools()]
        obs = get_pools_listing()
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
