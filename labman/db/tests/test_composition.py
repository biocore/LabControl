# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.exceptions import LabmanUnknownIdError
from labman.db.testing import LabmanTestCase
from labman.db.container import Tube, Well
from labman.db.process import (
    ReagentCreationProcess, GDNAExtractionProcess, SamplePlatingProcess)
from labman.db.composition import (
    Composition, ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition, PoolComposition, PrimerComposition,
    PrimerSetComposition)
# LibraryPrepShotgunComposition,
# NormalizedGDNAComposition,


class TestComposition(LabmanTestCase):
    def test_factory(self):
        self.assertEqual(Composition.factory(1537), ReagentComposition(1))
        self.assertEqual(Composition.factory(769), PrimerComposition(1))
        self.assertEqual(Composition.factory(1), PrimerSetComposition(1))
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
    def test_list_reagents(self):
        obs = ReagentComposition.list_reagents()
        exp = ['157022406', '443912', 'RNBF7110']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(term='39')
        exp = ['443912']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='extraction kit')
        exp = ['157022406']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='water', term='BF')
        exp = ['RNBF7110']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='water', term='22')
        exp = []
        self.assertEqual(obs, exp)

    def test_from_external_id(self):
        self.assertEqual(ReagentComposition.from_external_id('157022406'),
                         ReagentComposition(1))
        with self.assertRaises(LabmanUnknownIdError):
            ReagentComposition.from_external_id('Does not exist')

    def test_attributes(self):
        obs = ReagentComposition(1)
        self.assertEqual(obs.upstream_process, ReagentCreationProcess(3))
        self.assertEqual(obs.container, Tube(1))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1537)
        self.assertEqual(obs.external_lot_id, '157022406')
        self.assertEqual(obs.reagent_type, 'extraction kit')


class TestPrimerComposition(LabmanTestCase):
    def test_attributes(self):
        obs = PrimerComposition(1)
        self.assertEqual(obs.container, Well(769))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 769)
        self.assertEqual(obs.primer_set_composition, PrimerSetComposition(1))


class TestPrimerSetComposition(LabmanTestCase):
    def test_attributes(self):
        obs = PrimerSetComposition(1)
        self.assertEqual(obs.container, Well(1))
        self.assertEqual(obs.total_volume, 0)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1)
        self.assertEqual(obs.barcode, 'TCCCTTGTCTCC')


class TestSampleComposition(LabmanTestCase):
    def test_get_control_samples(self):
        self.assertEqual(SampleComposition.get_control_samples(),
                         ['blank', 'vibrio positive control'])
        self.assertEqual(SampleComposition.get_control_samples('l'),
                         ['blank', 'vibrio positive control'])
        self.assertEqual(SampleComposition.get_control_samples('bla'),
                         ['blank'])
        self.assertEqual(SampleComposition.get_control_samples('posit'),
                         ['vibrio positive control'])
        self.assertEqual(SampleComposition.get_control_samples('vib'),
                         ['vibrio positive control'])
        self.assertEqual(SampleComposition.get_control_samples('TrOL'),
                         ['vibrio positive control'])

    def test_attributes(self):
        # Test a sample
        obs = SampleComposition(1)
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKB1.640202')
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(6))
        self.assertEqual(obs.container, Well(1537))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1542)

        # Test a control sample
        obs = SampleComposition(85)
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(6))
        self.assertEqual(obs.container, Well(1789))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)

    def test_get_sample_composition_type_id(self):
        self.assertEqual(
            SampleComposition._get_sample_composition_type_id(
                'experimental sample'), 1)
        self.assertEqual(
            SampleComposition._get_sample_composition_type_id('blank'), 2)
        self.assertEqual(
            SampleComposition._get_sample_composition_type_id(
                'vibrio positive control'), 3)

    def test_update(self):
        tester = SampleComposition(85)

        # Make sure that the sample composition that we are working with
        # is a control sample
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)

        # Update a well from CONTROL -> EXPERIMENTAL SAMPLE
        tester.update('1.SKM8.640201')
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKM8.640201')

        # Update a well from EXPERIMENTAL SAMPLE -> EXPERIMENTAL SAMPLE
        tester.update('1.SKB6.640176')
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKB6.640176')

        # Update a well from EXPERIMENTAL SAMPLE -> CONTROL
        tester.update('vibrio positive control')
        self.assertEqual(tester.sample_composition_type,
                         'vibrio positive control')
        self.assertIsNone(tester.sample_id)

        # Update a well from CONROL -> CONTROL
        tester.update('blank')
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)


class TestGDNAComposition(LabmanTestCase):
    def test_attributes(self):
        obs = GDNAComposition(1)
        self.assertEqual(obs.sample_composition, SampleComposition(1))
        self.assertEqual(obs.upstream_process, GDNAExtractionProcess(1))
        self.assertEqual(obs.container, Well(1538))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1543)


class TestLibraryPrep16SComposition(LabmanTestCase):
    def test_attributes(self):
        obs = LibraryPrep16SComposition(1)
        self.assertEqual(obs.container, Well(1539))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.gdna_composition, GDNAComposition(1))
        self.assertEqual(obs.primer_composition, PrimerComposition(1))
        self.assertEqual(obs.composition_id, 1544)


class TestNormalizedGDNAComposition(LabmanTestCase):
    pass


class TestLibraryPrepShotgunComposition(LabmanTestCase):
    pass


class TestPoolComposition(LabmanTestCase):
    def test_pools(self):
        obs = PoolComposition.list_pools()
        exp = [{'pool_composition_id': 1,
                'external_id': 'Test Pool from Plate 1'},
               {'pool_composition_id': 2,
                'external_id': 'Test sequencing pool 1'}]
        self.assertEqual(obs, exp)

    def test_attributes(self):
        obs = PoolComposition(1)
        self.assertEqual(obs.container, Tube(4))
        self.assertEqual(obs.total_volume, 96)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1540)
        obs_comp = obs.components
        self.assertEqual(len(obs_comp), 96)
        exp = {'composition': LibraryPrep16SComposition(1),
               'input_volume': 1.0, 'percentage_of_output': 0}
        self.assertEqual(obs_comp[0], exp)


class TestPrimerSet(LabmanTestCase):
    pass


if __name__ == '__main__':
    main()
