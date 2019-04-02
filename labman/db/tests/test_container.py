# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.container import Well, Tube, Container
from labman.db.plate import Plate
from labman.db.process import SamplePlatingProcess, PoolingProcess
from labman.db.composition import PoolComposition, SampleComposition


class TestContainer(LabmanTestCase):
    def test_factory(self):
        self.assertEqual(Container.factory(3077), Tube(5))
        self.assertEqual(Container.factory(1825), Well(1824))


class TestTube(LabmanTestCase):
    # The creation of a tube is always linked to a Process, we are going to
    # test the creation of a tube on those processes rather than here
    def test_properties(self):
        tester = Tube(7)
        self.assertEqual(tester.external_id, 'Test Pool from Plate 1')
        self.assertFalse(tester.discarded)
        self.assertEqual(tester.remaining_volume, 96)
        self.assertIsNone(tester.notes)
        self.assertEqual(tester.latest_process, PoolingProcess(1))
        self.assertEqual(tester.container_id, 3079)
        self.assertEqual(tester.composition, PoolComposition(1))

    def test_discarded(self):
        tester = Tube(8)
        self.assertFalse(tester.discarded)
        tester.discard()
        self.assertTrue(tester.discarded)
        regex = "Can't discard tube 8: it's already discarded."
        self.assertRaisesRegex(ValueError, regex, tester.discard)


class TestWell(LabmanTestCase):
    # The creation of a well is always linked to a Process, we are going to
    # test the creation of a well on those processes rather than here
    def test_properties(self):
        tester = Well(3073)
        self.assertEqual(tester.plate, Plate(21))
        self.assertEqual(tester.row, 1)
        self.assertEqual(tester.column, 1)
        self.assertEqual(tester.remaining_volume, 10)
        self.assertIsNone(tester.notes)
        self.assertEqual(tester.latest_process, SamplePlatingProcess(11))
        self.assertEqual(tester.container_id, 3082)
        self.assertEqual(tester.composition, SampleComposition(1))

    def test_well_id(self):
        self.assertEqual(Well(1).well_id, 'A1')
        self.assertEqual(Well(2).well_id, 'A2')
        self.assertEqual(Well(3).well_id, 'A3')
        self.assertEqual(Well(13).well_id, 'B1')
        self.assertEqual(Well(54).well_id, 'E6')
        self.assertEqual(Well(96).well_id, 'H12')


if __name__ == '__main__':
    main()
