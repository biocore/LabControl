# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labcontrol.db import sql_connection
from labcontrol.db.exceptions import LabControlUnknownIdError
from labcontrol.db.testing import LabControlTestCase
from labcontrol.db.container import Tube, Well
from labcontrol.db.study import Study
from labcontrol.db.plate import Plate
from labcontrol.db.process import (
    ReagentCreationProcess, GDNAExtractionProcess, SamplePlatingProcess)
from labcontrol.db.composition import (
    Composition, ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition, PoolComposition, PrimerComposition,
    PrimerSetComposition, NormalizedGDNAComposition, ShotgunPrimerSet,
    LibraryPrepShotgunComposition, PrimerSet, CompressedGDNAComposition)


# Most of the tests in this file are not modifying the database, and the ones
# that do, make sure to revert their changes. To avoid unnecessary DB resets
# we are going to create a single Test class, reducing the running time of
# the tests from ~12 minutes to ~2 minutes
class TestsComposition(LabControlTestCase):
    def test_composition_factory(self):
        self.assertEqual(Composition.factory(3074), ReagentComposition(2))
        self.assertEqual(Composition.factory(1538), PrimerComposition(1))
        self.assertEqual(Composition.factory(1), PrimerSetComposition(1))
        self.assertEqual(Composition.factory(3082), SampleComposition(1))
        self.assertEqual(Composition.factory(3083), GDNAComposition(1))
        self.assertEqual(Composition.factory(3084),
                         LibraryPrep16SComposition(1))
        self.assertEqual(Composition.factory(3085),
                         CompressedGDNAComposition(1))
        self.assertEqual(Composition.factory(3086),
                         NormalizedGDNAComposition(1))
        self.assertEqual(Composition.factory(3087),
                         LibraryPrepShotgunComposition(1))
        self.assertEqual(Composition.factory(3079), PoolComposition(1))

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

        # TODO 'KAPA HyperPlus Kit' should eventually be refactored into
        #  something more like 'shotgun library prep kit'
        # test that the shotgun library prep kit exists in the list of reagents
        obs = ReagentComposition.list_reagents(reagent_type='KAPA HyperPlus kit')
        exp = ['KHP1']
        self.assertEqual(obs, exp)

        obs = ReagentComposition.list_reagents(reagent_type='water', term='22')
        exp = []
        self.assertEqual(obs, exp)

    def test_reagent_composition_from_external_id(self):
        self.assertEqual(ReagentComposition.from_external_id('157022406'),
                         ReagentComposition(2))
        with self.assertRaises(LabControlUnknownIdError):
            ReagentComposition.from_external_id('Does not exist')

    def test_reagent_composition_attributes(self):
        obs = ReagentComposition(2)
        self.assertEqual(obs.upstream_process, ReagentCreationProcess(6))
        self.assertEqual(obs.container, Tube(2))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3074)
        self.assertEqual(obs.external_lot_id, '157022406')
        self.assertEqual(obs.reagent_type, 'extraction kit')
        self.assertIsNone(obs.study)

    def test_reagent_composition_get_composition_type_description(self):
        obs = ReagentComposition(2)
        self.assertEqual(obs.get_composition_type_description(), "reagent")

    def test_primer_composition_attributes(self):
        obs = PrimerComposition(1)
        self.assertEqual(obs.container, Well(1537))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        # NB: the fact that the composition id is 1538 and the well id is 1537
        # is not a mistake.  There is a placeholder composition (for "Not
        # Applicable", supporting externally extracted DNA) added in
        # db_patch_manual.sql, before populate_test_db.sql is run to create the
        # records being tested here--but that composition is "stored" in a
        # placeholder TUBE rather than a placeholder WELL, so there is no
        # analogous extra well record.
        self.assertEqual(obs.composition_id, 1538)
        self.assertEqual(obs.primer_set_composition, PrimerSetComposition(1))
        self.assertIsNone(obs.study)

    def test_primer_composition_get_composition_type_description(self):
        obs = PrimerComposition(1)
        self.assertEqual(obs.get_composition_type_description(), "primer")

    def test_primer_set_composition_attributes(self):
        obs = PrimerSetComposition(1)
        self.assertEqual(obs.container, Well(1))
        self.assertEqual(obs.total_volume, 0)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 1)
        self.assertEqual(obs.barcode, 'AGCCTTCGTCGC')
        self.assertIsNone(obs.study)

    def test_primer_set_composition_get_composition_type_description(self):
        obs = PrimerSetComposition(1)
        self.assertEqual(obs.get_composition_type_description(), "primer set")

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

    def test_sample_composition_specimen_id(self):
        obs = SampleComposition(1).specimen_id
        # returns the underlying id if no specimen_id_column is set
        self.assertEqual(obs, '1.SKB1.640202')
        # same should be true for blanks
        obs = SampleComposition(8).specimen_id
        self.assertEqual(obs, 'blank.Test.plate.1.H1')

        # HACK: the Study object in labcontrol can't modify specimen_id_column
        # hence we do this directly in SQL, if a test fails the transaction
        # will rollback, otherwise we reset the column to NULL.
        sql = """UPDATE qiita.study
                 SET specimen_id_column = %s
                 WHERE study_id = 1"""
        with sql_connection.TRN as TRN:
            TRN.add(sql, ['anonymized_name'])

            obs = SampleComposition(1).specimen_id
            self.assertEqual(obs, 'SKB1')

            obs = SampleComposition(8).specimen_id
            self.assertEqual(obs, 'blank.Test.plate.1.H1')

            TRN.add(sql, [None])

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
        self.assertEqual(obs.content, '1.SKB1.640202.Test.plate.1.A1')
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(11))
        self.assertEqual(obs.container, Well(3073))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        obs.notes = 'New Notes'
        self.assertEqual(obs.notes, 'New Notes')
        obs.notes = None
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3082)
        self.assertEqual(obs.study, Study(1))

        # Test a control sample
        obs = SampleComposition(8)
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'blank.Test.plate.1.H1')
        self.assertEqual(obs.upstream_process, SamplePlatingProcess(11))
        self.assertEqual(obs.container, Well(3115))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3124)
        self.assertIsNone(obs.study)

    def test_sample_composition_get_composition_type_description(self):
        # NB: All sample compositions have generic composition type "sample",
        # even if they are controls. For details of what kind of "sample" they
        # are, look at the external id of the individual
        # sample_composition_type records.
        obs = SampleComposition(8)
        self.assertEqual(obs.get_composition_type_description(), "sample")

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
        self.assertEqual(tester.content, 'blank.Test.plate.1.H1')

        # Update a well from CONTROL -> EXPERIMENTAL SAMPLE
        self.assertEqual(tester.update('1.SKM8.640201'),
                         ('1.SKM8.640201', True))
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKM8.640201')
        self.assertEqual(tester.content, '1.SKM8.640201')

        # This test here tests that the code automatically detects when a
        # sample is duplicated in the plate and adds the plate name and
        # well ID to all duplicates.
        t2 = SampleComposition(9)  # A2
        self.assertEqual(t2.update('1.SKM8.640201'),
                         ('1.SKM8.640201.Test.plate.1.A2', True))
        self.assertEqual(t2.sample_composition_type, 'experimental sample')
        self.assertEqual(t2.sample_id, '1.SKM8.640201')
        self.assertEqual(t2.content, '1.SKM8.640201.Test.plate.1.A2')
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKM8.640201')
        self.assertEqual(tester.content, '1.SKM8.640201.Test.plate.1.H1')

        # This test here tests that the code automatically detects when a
        # sample is no longer duplicated in the plate and removes the plate
        # name and well id from the sample content
        self.assertEqual(t2.update('blank'), ('blank.Test.plate.1.A2', True))
        self.assertEqual(tester.content, '1.SKM8.640201')

        # Update a well from EXPERIMENTAL SAMPLE -> EXPERIMENTAL SAMPLE
        self.assertEqual(tester.update('1.SKB6.640176'),
                         ('1.SKB6.640176.Test.plate.1.H1', True))
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertEqual(tester.sample_id, '1.SKB6.640176')
        self.assertEqual(tester.content, '1.SKB6.640176.Test.plate.1.H1')

        # Update a well from EXPERIMENTAL SAMPLE -> CONTROL
        self.assertEqual(tester.update('vibrio.positive.control'),
                         ('vibrio.positive.control.Test.plate.1.H1', True))
        self.assertEqual(tester.sample_composition_type,
                         'vibrio.positive.control')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content,
                         'vibrio.positive.control.Test.plate.1.H1')

        # Update a well from CONTROL -> CONTROL
        self.assertEqual(tester.update('blank'), ('blank.Test.plate.1.H1',
                                                  True))
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.Test.plate.1.H1')

        # Update a well from CONTROL -> Unknown
        self.assertEqual(tester.update('Unknown'), ('Unknown', False))
        self.assertEqual(tester.sample_composition_type, 'experimental sample')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'Unknown')

        # Update a well from Unknown -> CONTROL
        self.assertEqual(tester.update('blank'), ('blank.Test.plate.1.H1',
                                                  True))
        self.assertEqual(tester.sample_composition_type, 'blank')
        self.assertIsNone(tester.sample_id)
        self.assertEqual(tester.content, 'blank.Test.plate.1.H1')

    def test_gDNA_composition_attributes(self):
        obs = GDNAComposition(1)
        self.assertEqual(obs.sample_composition, SampleComposition(1))
        self.assertEqual(obs.upstream_process, GDNAExtractionProcess(1))
        self.assertEqual(obs.container, Well(3074))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3083)
        self.assertEqual(obs.study, Study(1))

    def test_gdna_composition_get_composition_type_description(self):
        obs = GDNAComposition(1)
        self.assertEqual(obs.get_composition_type_description(), "gDNA")

    def test_library_prep_16S_composition_attributes(self):
        obs = LibraryPrep16SComposition(1)
        self.assertEqual(obs.container, Well(3075))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.gdna_composition, GDNAComposition(1))
        self.assertEqual(obs.primer_composition, PrimerComposition(1))
        self.assertEqual(obs.composition_id, 3084)
        self.assertEqual(obs.study, Study(1))

    def test_library_prep_16S_composition_get_composition_type_description(
            self):
        obs = LibraryPrep16SComposition(1)
        self.assertEqual(obs.get_composition_type_description(),
                         "16S library prep")

    def test_compressed_gDNA_composition_attributes(self):
        obs = CompressedGDNAComposition(1)
        self.assertEqual(obs.container, Well(3076))
        self.assertEqual(obs.total_volume, 10)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.gdna_composition, GDNAComposition(1))

    def test_compressed_gdna_composition_get_composition_type_description(
            self):
        obs = CompressedGDNAComposition(1)
        self.assertEqual(obs.get_composition_type_description(),
                         "compressed gDNA")

    def test_normalized_gDNA_composition_attributes(self):
        obs = NormalizedGDNAComposition(1)
        self.assertEqual(obs.container, Well(3077))
        self.assertEqual(obs.total_volume, 3500)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.compressed_gdna_composition,
                         CompressedGDNAComposition(1))
        self.assertEqual(obs.dna_volume, 415)
        self.assertEqual(obs.water_volume, 3085)
        self.assertEqual(obs.composition_id, 3086)
        self.assertEqual(obs.study, Study(1))

    def test_normalized_gdna_composition_get_composition_type_description(
            self):
        obs = NormalizedGDNAComposition(1)
        self.assertEqual(obs.get_composition_type_description(),
                         "normalized gDNA")

    def test_library_prep_shotgun_composition_attributes(self):
        obs = LibraryPrepShotgunComposition(1)
        self.assertEqual(obs.container, Well(3078))
        self._baseAssertEqual(obs.total_volume, 4000)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.normalized_gdna_composition,
                         NormalizedGDNAComposition(1))
        self.assertEqual(obs.i5_composition, PrimerComposition(769))
        self.assertEqual(obs.i7_composition, PrimerComposition(770))
        self.assertEqual(obs.composition_id, 3087)
        self.assertEqual(obs.study, Study(1))

    def test_library_prep_shotgun_composition_get_composition_type_description(
            self):
        obs = LibraryPrepShotgunComposition(1)
        self.assertEqual(obs.get_composition_type_description(),
                         "shotgun library prep")

    def test_pool_composition_get_components_type_multiple_raises(self):
        with self.assertRaises(ValueError):
            PoolComposition.get_components_type([LibraryPrep16SComposition(1),
                                                 PoolComposition(1)])

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
        self.assertEqual(obs.container, Tube(7))
        self.assertEqual(obs.total_volume, 96)
        self.assertIsNone(obs.notes)
        self.assertEqual(obs.composition_id, 3079)
        obs_comp = obs.components
        self.assertEqual(len(obs_comp), 95)
        exp = {'composition': LibraryPrep16SComposition(1),
               'input_volume': 1.0, 'percentage_of_output': 0}
        self.assertEqual(obs_comp[0], exp)
        self.assertEqual(obs.raw_concentration, 25.0)

    def test_pool_composition_get_composition_type_description(self):
        obs = PoolComposition(1)
        self.assertEqual(obs.get_composition_type_description(), "pool")

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
               {'primer_set_id': 3, 'external_id': 'EMP 18S primer set',
                'target_name': 'Amplicon'},
               {'primer_set_id': 4, 'external_id': 'EMP ITS primer set',
                'target_name': 'Amplicon'},
               {'primer_set_id': 2, 'external_id': 'iTru shotgun primer set',
                'target_name': 'Shotgun'}]
        self.assertEqual(obs, exp)


# This tests do modify the database in a way that can't be easily reverted,
# hence allowing this to live in its own class so the DB gets reseted
class TestShotgunPrimerSet(LabControlTestCase):
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


class TestCreateControlSample(LabControlTestCase):
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
