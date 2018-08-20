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
from labman.db.study import Study
from labman.db.plate import Plate
from labman.db.process import (
    ReagentCreationProcess, GDNAExtractionProcess, SamplePlatingProcess)
from labman.db.composition import (
    Composition, ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition, PoolComposition, PrimerComposition,
    PrimerSetComposition, NormalizedGDNAComposition, ShotgunPrimerSet,
    LibraryPrepShotgunComposition, PrimerSet, CompressedGDNAComposition)


# Most of the tests in this file are not modifying the database, and the ones
# that do, make sure to revert their changes. To avoid unnecessary DB resets
# we are going to create a single Test class, reducing the running time of
# the tests from ~12 minutes to ~2 minutes
class TestsComposition(LabmanTestCase):
    def test_composition_factory(self):
        self.assertEqual(Composition.factory(3073), ReagentComposition(1))
        self.assertEqual(Composition.factory(1537), PrimerComposition(1))
        self.assertEqual(Composition.factory(1), PrimerSetComposition(1))
        self.assertEqual(Composition.factory(3081), SampleComposition(1))
        self.assertEqual(Composition.factory(3082), GDNAComposition(1))
        self.assertEqual(Composition.factory(3083),
                         LibraryPrep16SComposition(1))
        self.assertEqual(Composition.factory(3084),
                         CompressedGDNAComposition(1))
        self.assertEqual(Composition.factory(3085),
                         NormalizedGDNAComposition(1))
        self.assertEqual(Composition.factory(3086),
                         LibraryPrepShotgunComposition(1))
        self.assertEqual(Composition.factory(3078), PoolComposition(1))

    def test_reagent_composition_list_reagents(self):
        obs = ReagentComposition.list_reagents()
        exp = ['157022406', '443912', 'KHP1', 'Not applicable',
               'RNBF7110', 'STUBS1']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(term='39')
        exp = ['443912']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='extraction kit')
        exp = ['157022406', 'Not applicable']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='water', term='BF')
        exp = ['RNBF7110']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='water', term='22')
        exp = []
        self.assertEqual(obs, exp)

    def test_reagent_composition_from_external_id(self):
        self.assertEqual(ReagentComposition.from_external_id('157022406'),
                         ReagentComposition(1))
        with self.assertRaises(LabmanUnknownIdError):
            ReagentComposition.from_external_id('Does not exist')

    def test_reagent_composition_attributes(self):
        obs = ReagentComposition(1)
        self.assertEqual(obs.upstream_process, ReagentCreationProcess(5))
        self.assertEqual(obs.container, Tube(1))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3073)
        self.assertEqual(obs.external_lot_id, '157022406')
        self.assertEqual(obs.reagent_type, 'extraction kit')
        self.assertIsNone(obs.study)

    def test_primer_composition_attributes(self):
        obs = PrimerComposition(1)
        self.assertEqual(obs.container, Well(1537))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1537)
        self.assertEqual(obs.primer_set_composition, PrimerSetComposition(1))
        self.assertIsNone(obs.study)

    def test_primer_set_composition_attributes(self):
        obs = PrimerSetComposition(1)
        self.assertEqual(obs.container, Well(1))
        self.assertEqual(obs.total_volume, 0)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1)
        self.assertEqual(obs.barcode, 'TCCCTTGTCTCC')
        self.assertIsNone(obs.study)

    def test_sample_composition_get_control_samples(self):
        self.assertEqual(
            SampleComposition.get_control_samples(),
            ['blank', 'empty', 'vibrio.positive.control', 'zymo.mock'])
        self.assertEqual(SampleComposition.get_control_samples('l'),
                         ['blank', 'vibrio.positive.control'])
        self.assertEqual(SampleComposition.get_control_samples('bla'),
                         ['blank'])
        self.assertEqual(SampleComposition.get_control_samples('posit'),
                         ['vibrio.positive.control'])
        self.assertEqual(SampleComposition.get_control_samples('vib'),
                         ['vibrio.positive.control'])
        self.assertEqual(SampleComposition.get_control_samples('TrOL'),
                         ['vibrio.positive.control'])

    def test_sample_composition_get_control_sample_types_description(self):
        obs = SampleComposition.get_control_sample_types_description()
        exp = [
            {'external_id': 'blank',
             'description': 'gDNA extraction blanks. Represents an empty '
                            'extraction well.'},
            {'external_id': 'empty',
             'description': 'Empty well. Represents an empty well that should '
                            'not be included in library preparation.'},
            {'external_id': 'vibrio.positive.control',
             'description': 'Bacterial isolate control (Vibrio fischeri ES114)'
                            '. Represents an extraction well loaded with '
                            'Vibrio.'},
            {'external_id': 'zymo.mock',
             'description': 'Bacterial community control (Zymo Mock D6306). '
                            'Represents an extraction well loaded with Zymo '
                            'Mock community.'}]
        self.assertEqual(obs, exp)

    def test_sample_composition_attributes(self):
        # Test a sample
        obs = SampleComposition(1)
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKB1.640202')
        self.assertEqual(obs.content, '1.SKB1.640202.21.A1')
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(10))
        self.assertEqual(obs.container, Well(3073))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        obs.notes = 'New Notes'
        self.assertEqual(obs.notes, 'New Notes')
        obs.notes = None
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3081)
        self.assertEqual(obs.study, Study(1))

        # Test a control sample
        obs = SampleComposition(8)
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'blank.21.H1')
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(10))
        self.assertEqual(obs.container, Well(3115))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3123)
        self.assertIsNone(obs.study)

    def test_sample_composition_get_sample_composition_type_id(self):
        self.assertEqual(
            SampleComposition._get_sample_composition_type_id(
                'experimental sample'), 1)
        self.assertEqual(
            SampleComposition._get_sample_composition_type_id('blank'), 2)
        self.assertEqual(
            SampleComposition._get_sample_composition_type_id(
                'vibrio.positive.control'), 3)

    def test_sample_composition_update(self):
        tester = SampleComposition(8)  # H1

        # Make sure that the sample composition that we are working with
        # is a control sample
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.21.H1')

        # Update a well from CONTROL -> EXPERIMENTAL SAMPLE
        self.assertEqual(tester.update('1.SKM8.640201'),
                         ('1.SKM8.640201', True))
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKM8.640201')
        self.assertEqual(tester.content, '1.SKM8.640201')

        # This test here tests that the code automatically detects when a
        # sample is duplicated in the plate and adds the plate ID and
        # well ID to all duplicates.
        t2 = SampleComposition(9)  # A2
        self.assertEqual(t2.update('1.SKM8.640201'),
                         ('1.SKM8.640201.21.A2', True))
        self.assertEqual(t2.sample_composition_type, 'experimental sample')
        self.assertEqual(t2.sample_id, '1.SKM8.640201')
        self.assertEqual(t2.content, '1.SKM8.640201.21.A2')
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKM8.640201')
        self.assertEqual(tester.content, '1.SKM8.640201.21.H1')

        # This test here tests that the code automatically detects when a
        # sample is no longer duplicated in the plate and removes the plate
        # id and well id from the sample content
        self.assertEqual(t2.update('blank'), ('blank.21.A2', True))
        self.assertEqual(tester.content, '1.SKM8.640201')

        # Update a well from EXPERIMENTAL SAMPLE -> EXPERIMENTAL SAMPLE
        self.assertEqual(tester.update('1.SKB6.640176'),
                         ('1.SKB6.640176.21.H1', True))
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKB6.640176')
        self.assertEqual(tester.content, '1.SKB6.640176.21.H1')

        # Update a well from EXPERIMENTAL SAMPLE -> CONTROL
        self.assertEqual(tester.update('vibrio.positive.control'),
                         ('vibrio.positive.control.21.H1', True))
        self.assertEqual(tester.sample_composition_type,
                         'vibrio.positive.control')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'vibrio.positive.control.21.H1')

        # Update a well from CONROL -> CONTROL
        self.assertEqual(tester.update('blank'), ('blank.21.H1', True))
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.21.H1')

        # Update a well from CONROL -> Unknown
        self.assertEqual(tester.update('Unknown'), ('Unknown', False))
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'Unknown')

        # Update a well from Unknown -> CONTROL
        self.assertEqual(tester.update('blank'), ('blank.21.H1', True))
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.21.H1')

    def test_gDNA_composition_attributes(self):
        obs = GDNAComposition(1)
        self.assertEqual(obs.sample_composition, SampleComposition(1))
        self.assertEqual(obs.upstream_process, GDNAExtractionProcess(1))
        self.assertEqual(obs.container, Well(3074))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3082)
        self.assertEqual(obs.study, Study(1))

    def test_library_prep_16S_composition_attributes(self):
        obs = LibraryPrep16SComposition(1)
        self.assertEqual(obs.container, Well(3075))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.gdna_composition, GDNAComposition(1))
        self.assertEqual(obs.primer_composition, PrimerComposition(1))
        self.assertEqual(obs.composition_id, 3083)
        self.assertEqual(obs.study, Study(1))

    def test_compressed_gDNA_composition_attributes(self):
        obs = CompressedGDNAComposition(1)
        self.assertEqual(obs.container, Well(3076))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.gdna_composition, GDNAComposition(1))

    def test_normalized_gDNA_composition_attributes(self):
        obs = NormalizedGDNAComposition(1)
        self.assertEqual(obs.container, Well(3077))
        self.assertEqual(obs.total_volume, 3500)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.compressed_gdna_composition,
                         CompressedGDNAComposition(1))
        self.assertEqual(obs.dna_volume, 415)
        self.assertEqual(obs.water_volume, 3085)
        self.assertEqual(obs.composition_id, 3085)
        self.assertEqual(obs.study, Study(1))

    def test_library_prep_shotgun_composition_attributes(self):
        obs = LibraryPrepShotgunComposition(1)
        self.assertEqual(obs.container, Well(3078))
        self._baseAssertEqual(obs.total_volume, 4000)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.normalized_gdna_composition,
                         NormalizedGDNAComposition(1))
        self.assertEqual(obs.i5_composition, PrimerComposition(769))
        self.assertEqual(obs.i7_composition, PrimerComposition(770))
        self.assertEqual(obs.composition_id, 3086)
        self.assertEqual(obs.study, Study(1))

    def test_pool_composition_get_components_type(self):
        obs1 = PoolComposition.get_components_type([PoolComposition(1)])
        self.assertEqual(obs1, PoolComposition)
        obs2 = PoolComposition.get_components_type(
            [LibraryPrep16SComposition(1)])
        self.assertEqual(obs2, LibraryPrep16SComposition)

    def test_pool_composition_pools(self):
        obs = PoolComposition.get_pools()
        obs_ids = [x.id for x in obs]
        exp_ids = [1, 2, 3, 4, 5, 6]
        self.assertEqual(obs_ids, exp_ids)

    def test_pool_composition_attributes(self):
        obs = PoolComposition(1)
        self.assertEqual(obs.container, Tube(6))
        self.assertEqual(obs.total_volume, 96)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3078)
        obs_comp = obs.components
        self.assertEqual(len(obs_comp), 95)
        exp = {'composition': LibraryPrep16SComposition(1),
               'input_volume': 1.0, 'percentage_of_output': 0}
        self.assertEqual(obs_comp[0], exp)
        self.assertEqual(obs.raw_concentration, 25.0)

    def test_pool_composition_attributes_is_plate_pool(self):
        obs1 = PoolComposition(1)  # of 16s
        self.assertTrue(obs1.is_plate_pool)
        obs2 = PoolComposition(2)  # of pools
        self.assertFalse(obs2.is_plate_pool)
        obs3 = PoolComposition(3)  # of shotgun
        self.assertTrue(obs3.is_plate_pool)

    def test_primer_set_attributes(self):
        obs = PrimerSet(1)
        self.assertEqual(obs.external_id, 'EMP 16S V4 primer set')
        self.assertEqual(obs.target_name, 'Amplicon')
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.plates, [Plate(1), Plate(2), Plate(3), Plate(4),
                                      Plate(5), Plate(6), Plate(7), Plate(8)])

    def test_primer_set_list(self):
        obs = PrimerSet.list_primer_sets()
        exp = [{'primer_set_id': 1, 'external_id': 'EMP 16S V4 primer set',
                'target_name': 'Amplicon'},
               {'primer_set_id': 2, 'external_id': 'iTru shotgun primer set',
                'target_name': 'Shotgun'}]
        self.assertEqual(obs, exp)


# This tests do modify the database in a way that can't be easily reverted,
# hence allowing this to live in its own class so the DB gets reseted
class TestShotgunPrimerSet(LabmanTestCase):
    def test_attributes(self):
        tester = ShotgunPrimerSet(1)
        self.assertEqual(tester.external_id, 'iTru combos December 2017')

    def test_get_next_combos(self):
        tester = ShotgunPrimerSet(1)
        # NOTE: 380 instead of 384 because the test sample plate contains 1
        # empty well. When the plate is collapsed 4 times into a 384-well plate
        # this results with 4 empty wells not included in library prep
        self.assertEqual(tester.current_combo_index, 380)
        with self.assertRaises(ValueError):
            tester.get_next_combos(0)

        with self.assertRaises(ValueError):
            tester.get_next_combos(150000)

        obs = tester.get_next_combos(5)
        self.assertEqual(tester.current_combo_index, 385)
        self.assertEqual(len(obs), 5)
        exp = [(PrimerSetComposition(1146), PrimerSetComposition(1530)),
               (PrimerSetComposition(1148), PrimerSetComposition(1532)),
               (PrimerSetComposition(1150), PrimerSetComposition(1534)),
               (PrimerSetComposition(1152), PrimerSetComposition(1536)),
               (PrimerSetComposition(769), PrimerSetComposition(1155))]
        self.assertEqual(obs, exp)


class TestCreateControlSample(LabmanTestCase):
    def test_create_control_sample_type(self):
        SampleComposition.create_control_sample_type(
            'testing.control', 'A test')
        obs = SampleComposition.get_control_sample_types_description()
        exp = [
            {'external_id': 'blank',
             'description': 'gDNA extraction blanks. Represents an empty '
                            'extraction well.'},
            {'external_id': 'empty',
             'description': 'Empty well. Represents an empty well that should '
                            'not be included in library preparation.'},
            {'external_id': 'testing.control',
             'description': 'A test'},
            {'external_id': 'vibrio.positive.control',
             'description': 'Bacterial isolate control (Vibrio fischeri ES114)'
                            '. Represents an extraction well loaded with '
                            'Vibrio.'},
            {'external_id': 'zymo.mock',
             'description': 'Bacterial community control (Zymo Mock D6306). '
                            'Represents an extraction well loaded with Zymo '
                            'Mock community.'}]
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
