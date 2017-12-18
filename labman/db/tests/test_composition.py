# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.container import Tube, Well
from labman.db.process import (
    ReagentCreationProcess, GDNAExtractionProcess, SamplePlatingProcess)
from labman.db.composition import (
    Composition, ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition, PoolComposition)
# PrimerComposition, PrimerSetComposition, LibraryPrepShotgunComposition,
# NormalizedGDNAComposition,


class TestComposition(LabmanTestCase):
    def test_factory(self):
        self.assertEqual(Composition.factory(1537), ReagentComposition(1))
        # TODO:
        # self.assertEqual(Composition.factory(769), PrimerComposition(1))
        # self.assertEqual(Composition.factory(1), PrimerSetComposition(1))
        self.assertEqual(Composition.factory(1542), SampleComposition(1))
        self.assertEqual(Composition.factory(1543), GDNAComposition(1))
        self.assertEqual(Composition.factory(1544),
                         LibraryPrep16SComposition(1))
        # TODO:
        # self.assertEqual(Composition.factory(), NormalizedGDNAComposition())
        # self.assertEqual(Composition.factory(),
        #                  LibraryPrepShotgunComposition())
        self.assertEqual(Composition.factory(1540), PoolComposition(1))


class TestReagentComposition(LabmanTestCase):
    def test_attributes(self):
        obs = ReagentComposition(1)
        self.assertEqual(obs.upstream_process, ReagentCreationProcess(3))
        self.assertEqual(obs.container, Tube(1))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.external_lot_id, '157022406')
        self.assertEqual(obs.reagent_type, 'extraction kit')


class TestPrimerComposition(LabmanTestCase):
    pass


class TestPrimerSetComposition(LabmanTestCase):
    pass


class TestSampleComposition(LabmanTestCase):
    def test_attributes(self):
        # Test a sample
        obs = SampleComposition(1)
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKB1.640202')
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(6))
        self.assertEqual(obs.container, Well(1537))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)

        # Test a control sample
        obs = SampleComposition(85)
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(6))
        self.assertEqual(obs.container, Well(1789))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)


class TestGDNAComposition(LabmanTestCase):
    def test_attributes(self):
        obs = GDNAComposition(1)
        self.assertEqual(obs.sample_composition, SampleComposition(1))
        self.assertEqual(obs.upstream_process, GDNAExtractionProcess(1))
        self.assertEqual(obs.container, Well(1538))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)


class TestLibraryPrep16SComposition(LabmanTestCase):
    pass


class TestNormalizedGDNAComposition(LabmanTestCase):
    pass


class TestLibraryPrepShotgunComposition(LabmanTestCase):
    pass


class TestPoolComposition(LabmanTestCase):
    pass


class TestPrimerSet(LabmanTestCase):
    pass


if __name__ == '__main__':
    main()
