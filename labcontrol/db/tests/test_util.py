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
    def test_get_pools_listing_all(self):
        exp = [
            # This is an amplicon plate pool, so
            # True for is_plate_pool and True for is_amplicon_plate_pool
            [1, 'Test Pool from Plate 1', True, True, 1],
            # This is an amplicon sequencing pool, so
            # False for is_plate_pool and False for is_amplicon_plate_pool (bc
            # is actually pool of pools, not pool of amplicon preps)
            [2, 'Test sequencing pool 1', False, False, 2],
            # This is a *shotgun* plate pool, so
            # True for is plate pool but False for is_amplicon_plate_pool
            [3, 'Test pool from Shotgun plates 1-4', True, False, 3],
            # These are amplicon plate pools
            [4, 'Test Pool from Plate 2', True, True, 4],
            [5, 'Test Pool from Plate 3', True, True, 5],
            [6, 'Test Pool from Plate 4', True, True, 6]
        ]
        obs = get_pools_listing([True, False], [True, False])
        self.assertEqual(obs, exp)

    def test_get_pools_listing_amplicon_plate_pool_only(self):
        exp = [
            # This is an amplicon plate pool, so
            # True for is_plate_pool and True for is_amplicon_plate_pool
            [1, 'Test Pool from Plate 1', True, True, 1],
            # These are amplicon plate pools
            [4, 'Test Pool from Plate 2', True, True, 4],
            [5, 'Test Pool from Plate 3', True, True, 5],
            [6, 'Test Pool from Plate 4', True, True, 6]
        ]
        obs = get_pools_listing([True], [True])
        self.assertEqual(obs, exp)

    def test_get_pools_listing_amplicon_sequencing_pool_only(self):
        exp = [
            # This is an amplicon sequencing pool, so
            # False for is_plate_pool and False for is_amplicon_plate_pool (bc
            # is actually pool of pools, not pool of amplicon preps)
            [2, 'Test sequencing pool 1', False, False, 2]
        ]
        obs = get_pools_listing([False], [False])
        self.assertEqual(obs, exp)

    def test_get_pools_listing_metagenomics_plate_pool(self):
        exp = [
            # This is a *shotgun* plate pool, so
            # True for is plate pool but False for is_amplicon_plate_pool
            [3, 'Test pool from Shotgun plates 1-4', True, False, 3]
        ]
        obs = get_pools_listing([True], [False])
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
