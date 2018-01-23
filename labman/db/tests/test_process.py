# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from datetime import date, datetime
from io import StringIO

import numpy as np
import numpy.testing as npt
import pandas as pd

from labman.db.testing import LabmanTestCase
from labman.db.container import Tube, Well
from labman.db.composition import (
    ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition, Composition, PoolComposition,
    PrimerComposition, PrimerSetComposition, LibraryPrepShotgunComposition,
    PrimerSet)
from labman.db.user import User
from labman.db.plate import Plate, PlateConfiguration
from labman.db.equipment import Equipment
from labman.db.process import (
    Process, SamplePlatingProcess, ReagentCreationProcess,
    PrimerWorkingPlateCreationProcess, GDNAExtractionProcess,
    LibraryPrep16SProcess, QuantificationProcess, PoolingProcess,
    SequencingProcess, GDNAPlateCompressionProcess, NormalizationProcess,
    LibraryPrepShotgunProcess)
from labman.db.study import Study


class TestProcess(LabmanTestCase):
    def test_factory(self):
        self.assertEqual(Process.factory(10),
                         SamplePlatingProcess(10))
        self.assertEqual(Process.factory(5),
                         ReagentCreationProcess(5))
        self.assertEqual(Process.factory(3),
                         PrimerWorkingPlateCreationProcess(1))
        self.assertEqual(Process.factory(11),
                         GDNAExtractionProcess(1))
        self.assertEqual(Process.factory(17),
                         GDNAPlateCompressionProcess(17))
        self.assertEqual(Process.factory(12),
                         LibraryPrep16SProcess(1))
        self.assertEqual(Process.factory(19),
                         NormalizationProcess(1))
        self.assertEqual(Process.factory(20),
                         LibraryPrepShotgunProcess(1))
        self.assertEqual(Process.factory(13),
                         QuantificationProcess(1))
        self.assertEqual(Process.factory(14), PoolingProcess(1))
        self.assertEqual(Process.factory(16), SequencingProcess(1))


class TestSamplePlatingProcess(LabmanTestCase):
    def test_attributes(self):
        tester = SamplePlatingProcess(10)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 10)
        self.assertEqual(tester.plate, Plate(21))

    def test_create(self):
        user = User('test@foo.bar')
        # 1 -> 96-well deep-well plate
        plate_config = PlateConfiguration(1)
        obs = SamplePlatingProcess.create(
            user, plate_config, 'Test Plate 1', 10)

        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)

        # Check that the plate has been created with the correct values
        obs_plate = obs.plate
        self.assertIsInstance(obs_plate, Plate)
        self.assertEqual(obs_plate.external_id, 'Test Plate 1')
        self.assertEqual(obs_plate.plate_configuration, plate_config)
        self.assertFalse(obs_plate.discarded)
        self.assertIsNone(obs_plate.notes)

        # Check that all the wells in the plate contain blanks
        plate_layout = obs_plate.layout
        for i, row in enumerate(plate_layout):
            for j, well in enumerate(row):
                self.assertIsInstance(well, Well)
                self.assertEqual(well.plate, obs_plate)
                self.assertEqual(well.row, i + 1)
                self.assertEqual(well.column, j + 1)
                self.assertEqual(well.latest_process, obs)
                obs_composition = well.composition
                self.assertIsInstance(obs_composition, SampleComposition)
                self.assertEqual(obs_composition.sample_composition_type,
                                 'blank')
                self.assertIsNone(obs_composition.sample_id)
                self.assertEqual(obs_composition.content,
                                 'blank.%s.%s' % (obs_plate.id, well.well_id))
                self.assertEqual(obs_composition.upstream_process, obs)
                self.assertEqual(obs_composition.container, well)
                self.assertEqual(obs_composition.total_volume, 10)

    def test_update_well(self):
        tester = SamplePlatingProcess(10)
        obs = SampleComposition(85)

        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'blank.21.H1')

        # Update a well from CONTROL -> EXPERIMENTAL SAMPLE
        self.assertEqual(
            tester.update_well(8, 1, '1.SKM8.640201'), '1.SKM8.640201')
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKM8.640201')
        self.assertEqual(obs.content, '1.SKM8.640201')

        # Update a well from EXPERIMENTAL SAMPLE -> EXPERIMENTAL SAMPLE
        self.assertEqual(
            tester.update_well(8, 1, '1.SKB6.640176'), '1.SKB6.640176')
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKB6.640176')
        self.assertEqual(obs.content, '1.SKB6.640176')

        # Update a well from EXPERIMENTAL SAMPLE -> CONTROL
        self.assertEqual(tester.update_well(8, 1, 'vibrio.positive.control'),
                         'vibrio.positive.control.21.H1')
        self.assertEqual(obs.sample_composition_type,
                         'vibrio.positive.control')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'vibrio.positive.control.21.H1')

        # Update a well from CONROL -> CONTROL
        self.assertEqual(tester.update_well(8, 1, 'blank'), 'blank.21.H1')
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'blank.21.H1')

    def test_comment_well(self):
        tester = SamplePlatingProcess(10)
        obs = SampleComposition(85)

        self.assertIsNone(obs.notes)
        tester.comment_well(8, 1, 'New notes')
        self.assertEqual(obs.notes, 'New notes')
        tester.comment_well(8, 1, None)
        self.assertIsNone(obs.notes)


class TestReagentCreationProcess(LabmanTestCase):
    def test_attributes(self):
        tester = ReagentCreationProcess(5)
        self.assertEqual(tester.date, date(2017, 10, 23))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 5)
        self.assertEqual(tester.tube, Tube(1))

    def test_create(self):
        user = User('test@foo.bar')
        obs = ReagentCreationProcess.create(user, 'Reagent external id', 10,
                                            'extraction kit')
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)

        # Check that the tube has been create with the correct values
        obs_tube = obs.tube
        self.assertIsInstance(obs_tube, Tube)
        self.assertEqual(obs_tube.external_id, 'Reagent external id')
        self.assertEqual(obs_tube.remaining_volume, 10)
        self.assertIsNone(obs_tube.notes)
        self.assertEqual(obs_tube.latest_process, obs)

        # Perform the reagent composition checks
        obs_composition = obs_tube.composition
        self.assertIsInstance(obs_composition, ReagentComposition)
        self.assertEqual(obs_composition.container, obs_tube)
        self.assertEqual(obs_composition.total_volume, 10)
        self.assertIsNone(obs_composition.notes)
        self.assertEqual(obs_composition.external_lot_id,
                         'Reagent external id')
        self.assertEqual(obs_composition.reagent_type, 'extraction kit')


class TestPrimerWorkingPlateCreationProcess(LabmanTestCase):
    def test_attributes(self):
        tester = PrimerWorkingPlateCreationProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 23))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 3)
        exp_plates = [Plate(11), Plate(12), Plate(13), Plate(14),
                      Plate(15), Plate(16), Plate(17), Plate(18)]
        self.assertEqual(tester.primer_set, PrimerSet(1))
        self.assertEqual(tester.master_set_order, 'EMP PRIMERS MSON 1')
        self.assertEqual(tester.plates, exp_plates)

    def test_create(self):
        user = User('test@foo.bar')
        primer_set = PrimerSet(1)
        obs = PrimerWorkingPlateCreationProcess.create(
            user, primer_set, 'Master Set Order 1',
            creation_date=date(2018, 1, 18))
        self.assertEqual(obs.date, date(2018, 1, 18))
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.primer_set, primer_set)
        self.assertEqual(obs.master_set_order, 'Master Set Order 1')

        obs_plates = obs.plates
        self.assertEqual(len(obs_plates), 8)
        self.assertEqual(obs_plates[0].external_id,
                         'EMP 16S V4 primer plate 1 2018-01-18')
        self.assertEqual(
            obs_plates[0].get_well(1, 1).composition.primer_set_composition,
            PrimerSetComposition(1))

        obs = PrimerWorkingPlateCreationProcess.create(
            user, primer_set, 'Master Set Order 1',
            creation_date=date(2018, 1, 18))
        self.assertTrue(obs.plates[0].external_id.startswith(
            'EMP 16S V4 primer plate 1 %s'
            % datetime.now().strftime('%Y-%m-%d')))


class TestGDNAExtractionProcess(LabmanTestCase):
    def test_attributes(self):
        tester = GDNAExtractionProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 11)
        exp_king_fisher_robots = [(Equipment(11), Plate(21))]
        self.assertEqual(tester.king_fisher_robots, exp_king_fisher_robots)
        exp_epmotion_robots = [(Equipment(5), Equipment(15), [Plate(21)])]
        self.assertEqual(tester.epmotion_robots, exp_epmotion_robots)
        exp_extraction_kits = [(ReagentComposition(1), [Plate(21)])]
        self.assertEqual(tester.extraction_kits, exp_extraction_kits)

    def test_create(self):
        user = User('test@foo.bar')
        ep_robot = Equipment(6)
        kf_robot = Equipment(11)
        tool = Equipment(15)
        kit = ReagentComposition(1)
        plate = Plate(21)
        plates_info = [(plate, kf_robot, ep_robot, tool, kit,
                        'gdna - Test plate 1')]
        obs = GDNAExtractionProcess.create(
            user, plates_info, 10, extraction_date=date(2018, 1, 1))
        self.assertEqual(obs.date, date(2018, 1, 1))
        self.assertEqual(obs.personnel, user)
        exp_king_fisher_robots = [(Equipment(11), Plate(21))]
        self.assertEqual(obs.king_fisher_robots, exp_king_fisher_robots)
        exp_epmotion_robots = [(Equipment(6), Equipment(15), [Plate(21)])]
        self.assertEqual(obs.epmotion_robots, exp_epmotion_robots)
        exp_extraction_kits = [(ReagentComposition(1), [Plate(21)])]
        self.assertEqual(obs.extraction_kits, exp_extraction_kits)

        # Check the extracted plate
        obs_plates = obs.plates
        self.assertEqual(len(obs_plates), 1)
        obs_plate = obs_plates[0]
        self.assertIsInstance(obs_plate, Plate)
        self.assertEqual(obs_plate.external_id, 'gdna - Test plate 1')
        self.assertEqual(obs_plate.plate_configuration,
                         plate.plate_configuration)
        self.assertFalse(obs_plate.discarded)

        # Check the wells in the plate
        plate_layout = obs_plate.layout
        for i, row in enumerate(plate_layout):
            for j, well in enumerate(row):
                self.assertIsInstance(well, Well)
                self.assertEqual(well.plate, obs_plate)
                self.assertEqual(well.row, i + 1)
                self.assertEqual(well.column, j + 1)
                self.assertEqual(well.latest_process, obs)
                obs_composition = well.composition
                self.assertIsInstance(obs_composition, GDNAComposition)
                self.assertEqual(obs_composition.upstream_process, obs)
                self.assertEqual(obs_composition.container, well)
                self.assertEqual(obs_composition.total_volume, 10)

        # The sample compositions of the gDNA compositions change depending on
        # the well. Spot check a few sample and controls
        self.assertEqual(
            plate_layout[0][0].composition.sample_composition.sample_id,
            '1.SKB1.640202')
        self.assertEqual(
            plate_layout[1][1].composition.sample_composition.sample_id,
            '1.SKB2.640194')
        self.assertIsNone(
            plate_layout[6][0].composition.sample_composition.sample_id)
        self.assertEqual(
            plate_layout[
                6][0].composition.sample_composition.sample_composition_type,
            'vibrio.positive.control')
        self.assertIsNone(
            plate_layout[7][0].composition.sample_composition.sample_id)
        self.assertEqual(
            plate_layout[
                7][0].composition.sample_composition.sample_composition_type,
            'blank')


class TestGDNAPlateCompressionProcess(LabmanTestCase):
    def test_attributes(self):
        tester = GDNAPlateCompressionProcess(17)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 17)
        self.assertEqual(tester.plates, [Plate(24)])

    def test_create(self):
        user = User('test@foo.bar')

        # Crate a couple of new plates so it is easy to test the interleaving
        spp = SamplePlatingProcess.create(
            user, PlateConfiguration(1), 'Compression Test 1', 1)
        spp.update_well(1, 1, '1.SKM7.640188')
        spp.update_well(1, 2, '1.SKD9.640182')
        spp.update_well(1, 3, '1.SKM8.640201')
        spp.update_well(1, 4, '1.SKB8.640193')
        spp.update_well(1, 5, '1.SKD2.640178')
        spp.update_well(1, 6, '1.SKM3.640197')
        spp.update_well(1, 7, '1.SKM4.640180')
        spp.update_well(1, 8, '1.SKB9.640200')
        spp.update_well(2, 1, '1.SKB4.640189')
        spp.update_well(2, 2, '1.SKB5.640181')
        spp.update_well(2, 3, '1.SKB6.640176')
        spp.update_well(2, 4, '1.SKM2.640199')
        spp.update_well(2, 5, '1.SKM5.640177')
        spp.update_well(2, 6, '1.SKB1.640202')
        spp.update_well(2, 7, '1.SKD8.640184')
        spp.update_well(2, 8, '1.SKD4.640185')
        plateA = spp.plates[0]

        spp = SamplePlatingProcess.create(
            user, PlateConfiguration(1), 'Compression Test 2', 1)
        spp.update_well(1, 1, '1.SKB4.640189')
        spp.update_well(1, 2, '1.SKB5.640181')
        spp.update_well(1, 3, '1.SKB6.640176')
        spp.update_well(1, 4, '1.SKM2.640199')
        spp.update_well(1, 5, '1.SKM5.640177')
        spp.update_well(1, 6, '1.SKB1.640202')
        spp.update_well(1, 7, '1.SKD8.640184')
        spp.update_well(1, 8, '1.SKD4.640185')
        spp.update_well(2, 1, '1.SKB3.640195')
        spp.update_well(2, 2, '1.SKM1.640183')
        spp.update_well(2, 3, '1.SKB7.640196')
        spp.update_well(2, 4, '1.SKD3.640198')
        spp.update_well(2, 5, '1.SKD7.640191')
        spp.update_well(2, 6, '1.SKD6.640190')
        spp.update_well(2, 7, '1.SKB2.640194')
        spp.update_well(2, 8, '1.SKM9.640192')
        plateB = spp.plates[0]

        # Extract the plates
        ep_robot = Equipment(6)
        tool = Equipment(15)
        kit = ReagentComposition(1)
        plates_info = [
            (plateA, Equipment(11), ep_robot, tool, kit, 'gdna - Test Comp 1'),
            (plateB, Equipment(12), ep_robot, tool, kit, 'gdna - Test Comp 2')]
        ep = GDNAExtractionProcess.create(user, plates_info, 10)

        obs = GDNAPlateCompressionProcess.create(
            user, ep.plates, 'Compressed plate AB')
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        obs_plates = obs.plates
        self.assertEqual(len(obs_plates), 1)
        obs_layout = obs_plates[0].layout
        exp_positions = [
            # Row 1 plate A
            (1, 1, '1.SKM7.640188'), (1, 3, '1.SKD9.640182'),
            (1, 5, '1.SKM8.640201'), (1, 7, '1.SKB8.640193'),
            (1, 9, '1.SKD2.640178'), (1, 11, '1.SKM3.640197'),
            (1, 13, '1.SKM4.640180'), (1, 15, '1.SKB9.640200'),
            # Row 1 plate B
            (1, 2, '1.SKB4.640189'), (1, 4, '1.SKB5.640181'),
            (1, 6, '1.SKB6.640176'), (1, 8, '1.SKM2.640199'),
            (1, 10, '1.SKM5.640177'), (1, 12, '1.SKB1.640202'),
            (1, 14, '1.SKD8.640184'), (1, 16, '1.SKD4.640185'),
            # Row 2 plate A
            (3, 1, '1.SKB4.640189'), (3, 3, '1.SKB5.640181'),
            (3, 5, '1.SKB6.640176'), (3, 7, '1.SKM2.640199'),
            (3, 9, '1.SKM5.640177'), (3, 11, '1.SKB1.640202'),
            (3, 13, '1.SKD8.640184'), (3, 15, '1.SKD4.640185'),
            # Row 2 plate B
            (3, 2, '1.SKB3.640195'), (3, 4, '1.SKM1.640183'),
            (3, 6, '1.SKB7.640196'), (3, 8, '1.SKD3.640198'),
            (3, 10, '1.SKD7.640191'), (3, 12, '1.SKD6.640190'),
            (3, 14, '1.SKB2.640194'), (3, 16, '1.SKM9.640192')]
        for row, col, sample_id in exp_positions:
            well = obs_layout[row - 1][col - 1]
            self.assertEqual(well.row, row)
            self.assertEqual(well.column, col)
            self.assertEqual(well.composition.sample_composition.sample_id,
                             sample_id)

        # In these positions we did not have an origin plate, do not store
        # anything, this way we can differentiate from blanks and save
        # reagents during library prep
        for col in range(0, 15):
            self.assertIsNone(obs_layout[1][col])


class TestLibraryPrep16SProcess(LabmanTestCase):
    def test_attributes(self):
        tester = LibraryPrep16SProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 12)
        self.assertEqual(tester.mastermix_lots,
                         [(ReagentComposition(2), [Plate(22)])])
        self.assertEqual(tester.water_lots,
                         [(ReagentComposition(3), [Plate(22)])])
        exp = [(Equipment(8), Equipment(16), Equipment(17), [Plate(22)])]
        self.assertEqual(tester.epmotions, exp)

    def test_create(self):
        user = User('test@foo.bar')
        master_mix = ReagentComposition(2)
        water = ReagentComposition(3)
        robot = Equipment(8)
        tm300_8_tool = Equipment(16)
        tm50_8_tool = Equipment(17)
        volume = 75
        plates = [(Plate(22), Plate(11))]
        plates_info = [(Plate(22), 'New 16S plate', Plate(11), robot,
                        tm300_8_tool, tm50_8_tool, master_mix, water)]
        obs = LibraryPrep16SProcess.create(user, plates_info, volume)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.mastermix_lots,
                         [(ReagentComposition(2), [Plate(22)])])
        self.assertEqual(obs.water_lots,
                         [(ReagentComposition(3), [Plate(22)])])
        exp = [(Equipment(8), Equipment(16), Equipment(17), [Plate(22)])]
        self.assertEqual(obs.epmotions, exp)

        # Check the generated plates
        obs_plates = obs.plates
        self.assertEqual(len(obs_plates), 1)
        obs_plate = obs_plates[0]
        self.assertIsInstance(obs_plate, Plate)
        self.assertEqual(obs_plate.external_id, 'New 16S plate')
        self.assertEqual(obs_plate.plate_configuration,
                         plates[0][0].plate_configuration)

        # Check the well in the plate
        plate_layout = obs_plate.layout
        for i, row in enumerate(plate_layout):
            for j, well in enumerate(row):
                self.assertIsInstance(well, Well)
                self.assertEqual(well.plate, obs_plate)
                self.assertEqual(well.row, i + 1)
                self.assertEqual(well.column, j + 1)
                self.assertEqual(well.latest_process, obs)
                obs_composition = well.composition
                self.assertIsInstance(obs_composition,
                                      LibraryPrep16SComposition)
                self.assertEqual(obs_composition.upstream_process, obs)
                self.assertEqual(obs_composition.container, well)
                self.assertEqual(obs_composition.total_volume, 75)

        # spot check a couple of elements
        sample_id = plate_layout[0][
            0].composition.gdna_composition.sample_composition.sample_id
        self.assertEqual(sample_id, '1.SKB1.640202')
        barcode = plate_layout[0][
            0].composition.primer_composition.primer_set_composition.barcode
        self.assertEqual(barcode, 'TCCCTTGTCTCC')


class TestNormalizationProcess(LabmanTestCase):
    def test_calculate_norm_vol(self):
        dna_concs = np.array([[2, 7.89], [np.nan, .0]])
        exp_vols = np.array([[2500., 632.5], [3500., 3500.]])
        obs_vols = NormalizationProcess._calculate_norm_vol(dna_concs)
        np.testing.assert_allclose(exp_vols, obs_vols)

    def test_attributes(self):
        tester = NormalizationProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 19)
        self.assertEqual(tester.quantification_process,
                         QuantificationProcess(2))
        self.assertEqual(tester.water_lot, ReagentComposition(3))

    def test_create(self):
        user = User('test@foo.bar')
        water = ReagentComposition(3)
        obs = NormalizationProcess.create(
            user, QuantificationProcess(2), water, 'Create-Norm plate 1')
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.quantification_process,
                         QuantificationProcess(2))
        self.assertEqual(obs.water_lot, ReagentComposition(3))

        # Check the generated plates
        obs_plates = obs.plates
        self.assertEqual(len(obs_plates), 1)
        obs_plate = obs_plates[0]
        self.assertEqual(obs_plate.external_id, 'Create-Norm plate 1')
        # Spot check some wells in the plate
        plate_layout = obs_plate.layout
        self.assertEqual(plate_layout[0][0].composition.dna_volume, 415)
        self.assertEqual(plate_layout[0][0].composition.water_volume, 3085)

    def test_format_picklist(self):
        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name\t'
            'Destination Well\n'
            'sam1\tWater\t384PP_AQ_BP2_HT\tA1\t2.0\t1000.0\tNormalizedDNA\t'
            'A1\n'
            'sam2\tWater\t384PP_AQ_BP2_HT\tA2\t7.89\t2867.5\tNormalizedDNA\t'
            'A2\n'
            'blank1\tWater\t384PP_AQ_BP2_HT\tB1\tnan\t0.0\tNormalizedDNA\tB1\n'
            'sam3\tWater\t384PP_AQ_BP2_HT\tB2\t0.0\t0.0\tNormalizedDNA\tB2\n'
            'sam1\tSample\t384PP_AQ_BP2_HT\tA1\t2.0\t2500.0\tNormalizedDNA\t'
            'A1\n'
            'sam2\tSample\t384PP_AQ_BP2_HT\tA2\t7.89\t632.5\tNormalizedDNA\t'
            'A2\n'
            'blank1\tSample\t384PP_AQ_BP2_HT\tB1\tnan\t3500.0\tNormalizedDNA\t'
            'B1\n'
            'sam3\tSample\t384PP_AQ_BP2_HT\tB2\t0.0\t3500.0\tNormalizedDNA\t'
            'B2')
        dna_vols = np.array([[2500., 632.5], [3500., 3500.]])
        water_vols = 3500 - dna_vols
        wells = np.array([['A1', 'A2'], ['B1', 'B2']])
        sample_names = np.array([['sam1', 'sam2'], ['blank1', 'sam3']])
        dna_concs = np.array([[2, 7.89], [np.nan, .0]])
        obs_picklist = NormalizationProcess._format_picklist(
            dna_vols, water_vols, wells, sample_names=sample_names,
            dna_concs=dna_concs)
        self.assertEqual(exp_picklist, obs_picklist)

        # test if switching dest wells
        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name\t'
            'Destination Well\n'
            'sam1\tWater\t384PP_AQ_BP2_HT\tA1\t2.0\t1000.0\tNormalizedDNA\t'
            'D1\n'
            'sam2\tWater\t384PP_AQ_BP2_HT\tA2\t7.89\t2867.5\tNormalizedDNA\t'
            'D2\n'
            'blank1\tWater\t384PP_AQ_BP2_HT\tB1\tnan\t0.0\tNormalizedDNA\tE1\n'
            'sam3\tWater\t384PP_AQ_BP2_HT\tB2\t0.0\t0.0\tNormalizedDNA\tE2\n'
            'sam1\tSample\t384PP_AQ_BP2_HT\tA1\t2.0\t2500.0\tNormalizedDNA\t'
            'D1\n'
            'sam2\tSample\t384PP_AQ_BP2_HT\tA2\t7.89\t632.5\tNormalizedDNA\t'
            'D2\n'
            'blank1\tSample\t384PP_AQ_BP2_HT\tB1\tnan\t3500.0\tNormalizedDNA\t'
            'E1\n'
            'sam3\tSample\t384PP_AQ_BP2_HT\tB2\t0.0\t3500.0\tNormalizedDNA\t'
            'E2')
        dna_vols = np.array([[2500., 632.5], [3500., 3500.]])
        water_vols = 3500 - dna_vols
        wells = np.array([['A1', 'A2'], ['B1', 'B2']])
        dest_wells = np.array([['D1', 'D2'], ['E1', 'E2']])
        sample_names = np.array([['sam1', 'sam2'], ['blank1', 'sam3']])
        dna_concs = np.array([[2, 7.89], [np.nan, .0]])
        obs_picklist = NormalizationProcess._format_picklist(
            dna_vols, water_vols, wells, dest_wells=dest_wells,
            sample_names=sample_names, dna_concs=dna_concs)
        self.assertEqual(exp_picklist, obs_picklist)

    def test_generate_echo_picklist(self):
        obs = NormalizationProcess(1).generate_echo_picklist()
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0],
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name'
            '\tDestination Well')
        self.assertEqual(
            obs_lines[1],
            '1.SKB1.640202\tWater\t384PP_AQ_BP2_HT\tA1\t12.068\t3085.0'
            '\tNormalizedDNA\tA1')
        self.assertEqual(
            obs_lines[384],
            'blank.21.H12\tWater\t384PP_AQ_BP2_HT\tP24\t0.342\t0.0\t'
            'NormalizedDNA\tP24')
        self.assertEqual(
            obs_lines[385],
            '1.SKB1.640202\tSample\t384PP_AQ_BP2_HT\tA1\t12.068\t415.0'
            '\tNormalizedDNA\tA1')
        self.assertEqual(
            obs_lines[-1],
            'blank.21.H12\tSample\t384PP_AQ_BP2_HT\tP24\t0.342\t3500.0\t'
            'NormalizedDNA\tP24')


class TestQuantificationProcess(LabmanTestCase):
    def test_compute_shotgun_pico_concentration(self):
        dna_vals = np.array([[10.14, 7.89, 7.9, 15.48],
                             [7.86, 8.07, 8.16, 9.64],
                             [12.29, 7.64, 7.32, 13.74]])
        obs = QuantificationProcess._compute_shotgun_pico_concentration(
            dna_vals, size=400)
        exp = np.array([[38.4090909, 29.8863636, 29.9242424, 58.6363636],
                        [29.7727273, 30.5681818, 30.9090909, 36.5151515],
                        [46.5530303, 28.9393939, 27.7272727, 52.0454545]])
        npt.assert_allclose(obs, exp)

    def test_make_2D_array(self):
        example_qpcr_df = pd.DataFrame(
            {'Sample DNA Concentration': [12, 0, 5, np.nan],
             'Well': ['A1', 'A2', 'A3', 'A4']})
        exp_cp_array = np.array([[12.0, 0.0, 5.0, np.nan]])
        obs = QuantificationProcess._make_2D_array(
            example_qpcr_df, rows=1, cols=4).astype(float)
        np.testing.assert_allclose(obs, exp_cp_array)

        example2_qpcr_df = pd.DataFrame({'Cp': [12, 0, 1, np.nan,
                                                12, 0, 5, np.nan],
                                        'Pos': ['A1', 'A2', 'A3', 'A4',
                                                'B1', 'B2', 'B3', 'B4']})
        exp2_cp_array = np.array([[12.0, 0.0, 1.0, np.nan],
                                  [12.0, 0.0, 5.0, np.nan]])
        obs = QuantificationProcess._make_2D_array(
            example2_qpcr_df, data_col='Cp', well_col='Pos', rows=2,
            cols=4).astype(float)
        np.testing.assert_allclose(obs, exp2_cp_array)

    def test_parse_pico_csv(self):
        # Test a normal sheet
        pico_csv = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t4039.000\t2.644

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        exp_pico_df = pd.DataFrame({'Well': ['A1', 'A2', 'B1', 'B2'],
                                    'Sample DNA Concentration':
                                    [3.432, 3.239, 10.016, 2.644]})
        pico_csv_f = StringIO(pico_csv)
        obs_pico_df = QuantificationProcess._parse_pico_csv(pico_csv_f)
        pd.testing.assert_frame_equal(obs_pico_df, exp_pico_df,
                                      check_like=True)

        # Test a sheet that has some ???? zero values
        pico_csv = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t\t?????

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        exp_pico_df = pd.DataFrame({'Well': ['A1', 'A2', 'B1', 'B2'],
                                    'Sample DNA Concentration':
                                    [3.432, 3.239, 10.016, np.nan]})
        pico_csv_f = StringIO(pico_csv)
        obs_pico_df = QuantificationProcess._parse_pico_csv(pico_csv_f)
        pd.testing.assert_frame_equal(obs_pico_df, exp_pico_df,
                                      check_like=True)

    def test_parse(self):
        pico_csv = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t4039.000\t2.644

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        obs = QuantificationProcess.parse(pico_csv)
        exp = np.asarray(
            [[3.432, 3.239, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [10.016, 2.644, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan],
             [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
              np.nan, np.nan, np.nan, np.nan]])
        npt.assert_allclose(obs, exp)

    def test_attributes(self):
        tester = QuantificationProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 13)
        obs = tester.concentrations
        self.assertEqual(len(obs), 96)
        self.assertEqual(obs[0], (LibraryPrep16SComposition(1), 1.5, None))
        self.assertEqual(obs[36], (LibraryPrep16SComposition(37), 1.5, None))
        self.assertEqual(obs[95], (LibraryPrep16SComposition(96), 1.5, None))

        tester = QuantificationProcess(3)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 21)
        obs = tester.concentrations
        self.assertEqual(len(obs), 384)
        self.assertEqual(
            obs[0], (LibraryPrepShotgunComposition(1), 12.068, 36.569))
        self.assertEqual(
            obs[296], (LibraryPrepShotgunComposition(297), 8.904, 26.981))
        self.assertEqual(
            obs[383], (LibraryPrepShotgunComposition(384), 0.342, 1.036))

    def test_create(self):
        user = User('test@foo.bar')
        plate = Plate(23)
        concentrations = np.around(np.random.rand(8, 12), 6)
        # Add some known values
        concentrations[0][0] = 3
        concentrations[0][1] = 4
        concentrations[0][2] = 40
        obs = QuantificationProcess.create(user, plate, concentrations)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        obs_c = obs.concentrations
        self.assertEqual(len(obs_c), 96)
        self.assertEqual(obs_c[0][0], LibraryPrep16SComposition(1))
        npt.assert_almost_equal(obs_c[0][1], concentrations[0][0])
        self.assertIsNone(obs_c[0][2])
        self.assertEqual(obs_c[12][0], LibraryPrep16SComposition(13))
        npt.assert_almost_equal(obs_c[12][1], concentrations[1][0])
        self.assertIsNone(obs_c[12][2])
        obs.compute_concentrations()
        obs_c = obs.concentrations
        # The values that we know
        npt.assert_almost_equal(obs_c[0][2], 80)
        npt.assert_almost_equal(obs_c[1][2], 60)
        npt.assert_almost_equal(obs_c[2][2], 0)
        # The rest (except last row) are 1 because np.random
        # generates numbers < 1
        for i in range(3, 84):
            npt.assert_almost_equal(obs_c[i][2], 1)
        # Last row are all 2 because they're blanks
        for i in range(84, 96):
            npt.assert_almost_equal(obs_c[i][2], 2)

        concentrations = np.around(np.random.rand(16, 24), 6)
        # Add some known values
        concentrations[0][0] = 10.14
        concentrations[0][1] = 7.89
        plate = Plate(26)
        obs = QuantificationProcess.create(user, plate, concentrations)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        obs_c = obs.concentrations
        self.assertEqual(len(obs_c), 384)
        self.assertEqual(obs_c[0][0], LibraryPrepShotgunComposition(1))
        npt.assert_almost_equal(obs_c[0][1], concentrations[0][0])
        self.assertIsNone(obs_c[0][2])
        obs.compute_concentrations(size=400)
        obs_c = obs.concentrations
        # Make sure that the known values are the ones that we expect
        npt.assert_almost_equal(obs_c[0][2], 38.4091)
        npt.assert_almost_equal(obs_c[1][2], 29.8864)

        # Test empty concentrations
        with self.assertRaises(ValueError):
            QuantificationProcess.create(user, plate, [])
        with self.assertRaises(ValueError):
            QuantificationProcess.create(user, plate, [[]])


class TestLibraryPrepShotgunProcess(LabmanTestCase):
    def test_attributes(self):
        tester = LibraryPrepShotgunProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 20)
        self.assertEqual(tester.kappa_hyper_plus_kit, ReagentComposition(4))
        self.assertEqual(tester.stub_lot, ReagentComposition(5))
        self.assertEqual(tester.normalization_process, NormalizationProcess(1))

    def test_create(self):
        user = User('test@foo.bar')
        plate = Plate(25)
        kappa = ReagentComposition(4)
        stub = ReagentComposition(5)
        obs = LibraryPrepShotgunProcess.create(
            user, plate, 'Test Shotgun Library 1', kappa, stub, 4000,
            Plate(19), Plate(20))
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.kappa_hyper_plus_kit, kappa)
        self.assertEqual(obs.stub_lot, stub)
        self.assertEqual(obs.normalization_process, NormalizationProcess(1))

        plates = obs.plates
        self.assertEqual(len(plates), 1)
        layout = plates[0].layout
        self.assertEqual(layout[0][0].composition.i5_composition,
                         PrimerComposition(769))
        self.assertEqual(layout[0][0].composition.i7_composition,
                         PrimerComposition(774))
        self.assertEqual(layout[-1][-1].composition.i5_composition,
                         PrimerComposition(1535))
        self.assertEqual(layout[-1][-1].composition.i7_composition,
                         PrimerComposition(770))

    def test_format_picklist(self):
        exp_picklist = (
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Transfer Volume\tIndex Name\tIndex Sequence\t'
            'Destination Plate Name\tDestination Well\n'
            'sam1\tiTru5_plate\t384LDV_AQ_B2_HT\tA1\t250\tiTru5_01_A\tACCGACAA'
            '\tIndexPCRPlate\tA1\n'
            'sam2\tiTru5_plate\t384LDV_AQ_B2_HT\tB1\t250\tiTru5_01_B\tAGTGGCAA'
            '\tIndexPCRPlate\tA2\n'
            'blank1\tiTru5_plate\t384LDV_AQ_B2_HT\tC1\t250\tiTru5_01_C'
            '\tCACAGACT\tIndexPCRPlate\tB1\n'
            'sam3\tiTru5_plate\t384LDV_AQ_B2_HT\tD1\t250\tiTru5_01_D\tCGACACTT'
            '\tIndexPCRPlate\tB2\n'
            'sam1\tiTru7_plate\t384LDV_AQ_B2_HT\tA1\t250\tiTru7_101_01\t'
            'ACGTTACC\tIndexPCRPlate\tA1\n'
            'sam2\tiTru7_plate\t384LDV_AQ_B2_HT\tA2\t250\tiTru7_101_02\t'
            'CTGTGTTG\tIndexPCRPlate\tA2\n'
            'blank1\tiTru7_plate\t384LDV_AQ_B2_HT\tA3\t250\tiTru7_101_03\t'
            'TGAGGTGT\tIndexPCRPlate\tB1\n'
            'sam3\tiTru7_plate\t384LDV_AQ_B2_HT\tA4\t250\tiTru7_101_04\t'
            'GATCCATG\tIndexPCRPlate\tB2')

        sample_wells = np.array(['A1', 'A2', 'B1', 'B2'])
        sample_names = np.array(['sam1', 'sam2', 'blank1', 'sam3'])
        indices = pd.DataFrame({
            'i5 name': {0: 'iTru5_01_A', 1: 'iTru5_01_B', 2: 'iTru5_01_C',
                        3: 'iTru5_01_D'},
            'i5 plate': {0: 'iTru5_plate', 1: 'iTru5_plate', 2: 'iTru5_plate',
                         3: 'iTru5_plate'},
            'i5 sequence': {0: 'ACCGACAA', 1: 'AGTGGCAA', 2: 'CACAGACT',
                            3: 'CGACACTT'},
            'i5 well': {0: 'A1', 1: 'B1', 2: 'C1', 3: 'D1'},
            'i7 name': {0: 'iTru7_101_01', 1: 'iTru7_101_02',
                        2: 'iTru7_101_03', 3: 'iTru7_101_04'},
            'i7 plate': {0: 'iTru7_plate', 1: 'iTru7_plate', 2: 'iTru7_plate',
                         3: 'iTru7_plate'},
            'i7 sequence': {0: 'ACGTTACC', 1: 'CTGTGTTG', 2: 'TGAGGTGT',
                            3: 'GATCCATG'},
            'i7 well': {0: 'A1', 1: 'A2', 2: 'A3', 3: 'A4'},
            'index combo seq': {0: 'ACCGACAAACGTTACC', 1: 'AGTGGCAACTGTGTTG',
                                2: 'CACAGACTTGAGGTGT', 3: 'CGACACTTGATCCATG'}})
        obs_picklist = LibraryPrepShotgunProcess._format_picklist(
            sample_names, sample_wells, indices)
        self.assertEqual(exp_picklist, obs_picklist)

    def test_generate_echo_picklist(self):
        obs = LibraryPrepShotgunProcess(1).generate_echo_picklist()
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0],
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Transfer Volume\tIndex Name\tIndex Sequence\t'
            'Destination Plate Name\tDestination Well')
        self.assertEqual(
            obs_lines[1],
            '1.SKB1.640202\tiTru 5 primer\t384LDV_AQ_B2_HT\tA1\t250\t'
            'iTru5_01_A\tACCGACAA\tIndexPCRPlate\tA1')
        self.assertEqual(
            obs_lines[-1],
            'blank.21.H12\tiTru 7 primer\t384LDV_AQ_B2_HT\tP24\t250\t'
            'iTru7_211_01\tGCTTCTTG\tIndexPCRPlate\tP24')


class TestPoolingProcess(LabmanTestCase):
    def test_compute_shotgun_pooling_values_eqvol(self):
        qpcr_conc = np.array(
            [[98.14626462, 487.8121413, 484.3480866, 2.183406934],
             [498.3536649, 429.0839787, 402.4270321, 140.1601735],
             [21.20533391, 582.9456031, 732.2655041, 7.545145988]])
        obs_sample_vols = PoolingProcess.compute_shotgun_pooling_values_eqvol(
            qpcr_conc, total_vol=60.0)
        exp_sample_vols = np.zeros([3, 4]) + 5000
        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

        obs_sample_vols = PoolingProcess.compute_shotgun_pooling_values_eqvol(
            qpcr_conc, total_vol=60)
        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

    def test_compute_shotgun_pooling_values_minvol(self):
        sample_concs = np.array([[1, 12, 400], [200, 40, 1]])
        exp_vols = np.array([[100, 100, 4166.6666666666],
                             [8333.33333333333, 41666.666666666, 100]])
        obs_vols = PoolingProcess.compute_shotgun_pooling_values_minvol(
            sample_concs)
        npt.assert_allclose(exp_vols, obs_vols)

    def test_compute_shotgun_pooling_values_floor(self):
        sample_concs = np.array([[1, 12, 400], [200, 40, 1]])
        exp_vols = np.array([[0, 50000, 6250], [12500, 50000, 0]])
        obs_vols = PoolingProcess.compute_shotgun_pooling_values_floor(
            sample_concs)
        npt.assert_allclose(exp_vols, obs_vols)

    def test_attributes(self):
        tester = PoolingProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 14)
        self.assertEqual(tester.quantification_process,
                         QuantificationProcess(1))
        self.assertEqual(tester.robot, Equipment(8))
        self.assertEqual(tester.destination, '1')
        self.assertEqual(tester.pool, PoolComposition(1))
        components = tester.components
        self.assertEqual(len(components), 96)
        self.assertEqual(
            components[0], (LibraryPrep16SComposition(1), 1.0))
        self.assertEqual(
            components[36], (LibraryPrep16SComposition(37), 1.0))
        self.assertEqual(
            components[95], (LibraryPrep16SComposition(96), 1.0))

    def test_create(self):
        user = User('test@foo.bar')
        quant_proc = QuantificationProcess(1)
        robot = Equipment(8)
        input_compositions = [
            {'composition': Composition.factory(1544), 'input_volume': 1,
             'percentage_of_output': 0.25},
            {'composition': Composition.factory(1547), 'input_volume': 1,
             'percentage_of_output': 0.25},
            {'composition': Composition.factory(1550), 'input_volume': 1,
             'percentage_of_output': 0.25},
            {'composition': Composition.factory(1553), 'input_volume': 1,
             'percentage_of_output': 0.25}]
        obs = PoolingProcess.create(user, quant_proc, 'New test pool name', 4,
                                    input_compositions, robot, '1')
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.quantification_process, quant_proc)
        self.assertEqual(obs.robot, robot)

    def test_format_picklist(self):
        vol_sample = np.array([[10.00, 10.00, np.nan, 5.00, 10.00, 10.00]])
        header = ['Source Plate Name,Source Plate Type,Source Well,'
                  'Concentration,Transfer Volume,Destination Plate Name,'
                  'Destination Well']
        exp_values = ['1,384LDV_AQ_B2_HT,A1,,10.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A2,,10.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A3,,0.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A4,,5.00,NormalizedDNA,A1',
                      '1,384LDV_AQ_B2_HT,A5,,10.00,NormalizedDNA,A2',
                      '1,384LDV_AQ_B2_HT,A6,,10.00,NormalizedDNA,A2']
        exp_str = '\n'.join(header + exp_values)
        obs_str = PoolingProcess._format_picklist(
            vol_sample, max_vol_per_well=26, dest_plate_shape=[16, 24])
        self.assertEqual(exp_str, obs_str)

    def test_generate_echo_picklist(self):
        obs = PoolingProcess(3).generate_echo_picklist()
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0],
            'Source Plate Name,Source Plate Type,Source Well,Concentration,'
            'Transfer Volume,Destination Plate Name,Destination Well')
        self.assertEqual(obs_lines[1],
                         '1,384LDV_AQ_B2_HT,A1,,1.00,NormalizedDNA,A1')
        self.assertEqual(obs_lines[-1],
                         '1,384LDV_AQ_B2_HT,P24,,1.00,NormalizedDNA,A1')

    def test_generate_epmotion_file(self):
        obs = PoolingProcess(1).generate_epmotion_file()
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0], 'Rack,Source,Rack,Destination,Volume,Tool')
        self.assertEqual(obs_lines[1], '1,A1,1,1,1.000,1')
        self.assertEqual(obs_lines[-1], '1,H12,1,1,1.000,1')

    def test_generate_pool_file(self):
        self.assertTrue(PoolingProcess(1).generate_pool_file().startswith(
            'Rack,Source,Rack,Destination,Volume,Tool'))
        self.assertTrue(PoolingProcess(3).generate_pool_file().startswith(
            'Source Plate Name,Source Plate Type,Source Well,Concentration,'))
        with self.assertRaises(ValueError):
            PoolingProcess(2).generate_pool_file()


class TestSequencingProcess(LabmanTestCase):
    def test_attributes(self):
        tester = SequencingProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 16)
        self.assertEqual(tester.pools, [[PoolComposition(2), 1]])
        self.assertEqual(tester.run_name, 'Test Run.1')
        self.assertEqual(tester.experiment, 'TestExperiment1')
        self.assertEqual(tester.sequencer, Equipment(18))
        self.assertEqual(tester.fwd_cycles, 151)
        self.assertEqual(tester.rev_cycles, 151)
        self.assertEqual(tester.assay, 'Amplicon')
        self.assertEqual(tester.principal_investigator, User('test@foo.bar'))
        self.assertEqual(
            tester.contacts,
            [User('admin@foo.bar'), User('demo@microbio.me'),
             User('shared@foo.bar')])

    def test_list_sequencing_runs(self):
        obs = SequencingProcess.list_sequencing_runs()

        self.assertEqual(obs[0], {'process_id': 16,
                                  'run_name': 'Test Run.1',
                                  'sequencing_process_id': 1,
                                  'experiment': 'TestExperiment1',
                                  'sequencer_id': 18,
                                  'fwd_cycles': 151,
                                  'rev_cycles': 151,
                                  'assay': 'Amplicon',
                                  'principal_investigator': 'test@foo.bar'})
        self.assertEqual(obs[1], {'process_id': 23,
                                  'run_name': 'TestShotgunRun1',
                                  'sequencing_process_id': 2,
                                  'experiment': 'TestExperimentShotgun1',
                                  'sequencer_id': 19,
                                  'fwd_cycles': 151,
                                  'rev_cycles': 151,
                                  'assay': 'Metagenomics',
                                  'principal_investigator': 'test@foo.bar'})

    def test_create(self):
        user = User('test@foo.bar')
        pool = PoolComposition(2)
        sequencer = Equipment(19)

        obs = SequencingProcess.create(
            user, [pool], 'TestCreateRun1', 'TestCreateExperiment1', sequencer,
            151, 151, user, contacts=[
                User('shared@foo.bar'), User('admin@foo.bar'),
                User('demo@microbio.me')])

        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.pools, [[PoolComposition(2), 1]])
        self.assertEqual(obs.run_name, 'TestCreateRun1')
        self.assertEqual(obs.experiment, 'TestCreateExperiment1')
        self.assertEqual(obs.sequencer, Equipment(19))
        self.assertEqual(obs.fwd_cycles, 151)
        self.assertEqual(obs.rev_cycles, 151)
        self.assertEqual(obs.assay, 'Amplicon')
        self.assertEqual(obs.principal_investigator, User('test@foo.bar'))
        self.assertEqual(
            obs.contacts,
            [User('admin@foo.bar'), User('demo@microbio.me'),
             User('shared@foo.bar')])

    def test_bcl_scrub_name(self):
        self.assertEqual(SequencingProcess._bcl_scrub_name('test.1'), 'test_1')
        self.assertEqual(SequencingProcess._bcl_scrub_name('test-1'), 'test-1')
        self.assertEqual(SequencingProcess._bcl_scrub_name('test_1'), 'test_1')

    def test_reverse_complement(self):
        self.assertEqual(
            SequencingProcess._reverse_complement('AGCCT'), 'AGGCT')

    def test_sequencer_i5_index(self):
        indices = ['AGCT', 'CGGA', 'TGCC']
        exp_rc = ['AGCT', 'TCCG', 'GGCA']

        obs_hiseq4k = SequencingProcess._sequencer_i5_index(
            'HiSeq4000', indices)
        self.assertListEqual(obs_hiseq4k, exp_rc)

        obs_hiseq25k = SequencingProcess._sequencer_i5_index(
            'HiSeq2500', indices)
        self.assertListEqual(obs_hiseq25k, indices)

        obs_nextseq = SequencingProcess._sequencer_i5_index(
            'NextSeq', indices)
        self.assertListEqual(obs_nextseq, exp_rc)

        with self.assertRaises(ValueError):
            SequencingProcess._sequencer_i5_index('foo', indices)

    def test_format_sample_sheet_data(self):
        # test that single lane works
        exp_data = (
            'Lane,Sample_ID,Sample_Name,Sample_Plate'
            ',Sample_Well,I7_Index_ID,index,I5_Index_ID'
            ',index2,Sample_Project,Description\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,example_proj,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,example_proj,\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,example_proj,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,example_proj,'
            )

        wells = ['A1', 'A2', 'B1', 'B2']
        sample_ids = ['sam1', 'sam2', 'blank1', 'sam3']
        i5_name = ['iTru5_01_A', 'iTru5_01_B', 'iTru5_01_C', 'iTru5_01_D']
        i5_seq = ['ACCGACAA', 'AGTGGCAA', 'CACAGACT', 'CGACACTT']
        i7_name = ['iTru7_101_01', 'iTru7_101_02',
                   'iTru7_101_03', 'iTru7_101_04']
        i7_seq = ['ACGTTACC', 'CTGTGTTG', 'TGAGGTGT', 'GATCCATG']
        sample_plates = ['example'] * 4

        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, wells=wells,
            sample_plates=sample_plates, sample_proj='example_proj', lanes=[1])
        self.assertEqual(obs_data, exp_data)

        # test that two lanes works
        exp_data_2 = (
            'Lane,Sample_ID,Sample_Name,Sample_Plate,'
            'Sample_Well,I7_Index_ID,index,I5_Index_ID,'
            'index2,Sample_Project,Description\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,example_proj,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,example_proj,\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,example_proj,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,example_proj,\n'
            '2,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,example_proj,\n'
            '2,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,example_proj,\n'
            '2,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT'
            ',iTru5_01_C,CACAGACT,example_proj,\n'
            '2,sam3,sam3,example,B2,iTru7_101_04,GATCCATG'
            ',iTru5_01_D,CGACACTT,example_proj,')

        obs_data_2 = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, wells=wells,
            sample_plates=sample_plates, sample_proj='example_proj',
            lanes=[1, 2])
        self.assertEqual(obs_data_2, exp_data_2)

        # test with r/c i5 barcodes
        exp_data = (
            'Lane,Sample_ID,Sample_Name,Sample_Plate'
            ',Sample_Well,I7_Index_ID,index,I5_Index_ID'
            ',index2,Sample_Project,Description\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,example_proj,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,example_proj,\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,example_proj,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,example_proj,')

        i5_seq = ['ACCGACAA', 'AGTGGCAA', 'CACAGACT', 'CGACACTT']
        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, wells=wells,
            sample_plates=sample_plates, sample_proj='example_proj', lanes=[1])
        self.assertEqual(obs_data, exp_data)

        # Test without header
        exp_data = (
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,example_proj,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,example_proj,\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,example_proj,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,example_proj,')

        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, wells=wells,
            sample_plates=sample_plates, sample_proj='example_proj', lanes=[1],
            include_header=False)
        self.assertEqual(obs_data, exp_data)

    def test_format_sample_sheet_comments(self):
        contacts = {'Test User': 'tuser@fake.com',
                    'Another User': 'anuser@fake.com',
                    'Jon Jonny': 'jonjonny@foo.com',
                    'Gregorio Orio': 'gregOrio@foo.com'}
        principal_investigator = {'Knight': 'theknight@fake.com'}
        other = None
        sep = '\t'
        exp_comment = (
            'PI\tKnight\ttheknight@fake.com\n'
            'Contact\tAnother User\tGregorio Orio'
            '\tJon Jonny\tTest User\n'
            '\tanuser@fake.com\tgregOrio@foo.com'
            '\tjonjonny@foo.com\ttuser@fake.com\n')
        obs_comment = SequencingProcess._format_sample_sheet_comments(
            principal_investigator, contacts, other, sep)
        self.assertEqual(exp_comment, obs_comment)

    def test_format_sample_sheet(self):
        exp_sample_sheet = (
            '[Header]\n'
            'IEMFileVersion\t4\n'
            'Investigator Name\tKnight\n'
            'Experiment Name\t\n'
            'Date\t2017-08-13\n'
            'Workflow\tGenerateFASTQ\n'
            'Application\tFASTQ Only\n'
            'Assay\tMetagenomics\n'
            'Description\t\n'
            'Chemistry\tDefault\n\n'
            '[Reads]\n'
            '150\n'
            '150\n\n'
            '[Settings]\n'
            'ReverseComplement\t0\n\n'
            '[Data]\n'
            'Lane\tSample_ID\tSample_Name\tSample_Plate\tSample_Well'
            '\tI7_Index_ID\tindex\tI5_Index_ID\tindex2\tSample_Project'
            '\tDescription\n'
            '1\tsam1\tsam1\texample\tA1\tiTru7_101_01\tACGTTACC\tiTru5_01_A'
            '\tACCGACAA\texample_proj\t\n'
            '1\tsam2\tsam2\texample\tA2\tiTru7_101_02\tCTGTGTTG\tiTru5_01_B'
            '\tAGTGGCAA\texample_proj\t\n'
            '1\tblank1\tblank1\texample\tB1\tiTru7_101_03\tTGAGGTGT\t'
            'iTru5_01_C\tCACAGACT\texample_proj\t\n'
            '1\tsam3\tsam3\texample\tB2\tiTru7_101_04\tGATCCATG\tiTru5_01_D'
            '\tCGACACTT\texample_proj\t')

        exp_sample_sheet_2 = (
            '# PI\tKnight\ttheknight@fake.com\t\t\n'
            '# Contact\tTest User\tAnother User\tJon Jonny\t'
            'Gregorio Orio\n'
            '# \ttuser@fake.com\tanuser@fake.com\tjonjonny@foo.com\t'
            'gregOrio@foo.com\n'
            '[Header]\n'
            'IEMFileVersion\t4\n'
            'Investigator Name\tKnight\n'
            'Experiment Name\t\n'
            'Date\t2017-08-13\n'
            'Workflow\tGenerateFASTQ\n'
            'Application\tFASTQ Only\n'
            'Assay\tMetagenomics\n'
            'Description\t\n'
            'Chemistry\tDefault\n\n'
            '[Reads]\n'
            '150\n'
            '150\n\n'
            '[Settings]\n'
            'ReverseComplement\t0\n\n'
            '[Data]\n'
            'Lane\tSample_ID\tSample_Name\tSample_Plate\t'
            'Sample_Well\tI7_Index_ID\tindex\tI5_Index_ID\t'
            'index2\tSample_Project\tDescription\n'
            '1\tsam1\tsam1\texample\tA1\tiTru7_101_01\tACGTTACC'
            '\tiTru5_01_A\tACCGACAA\texample_proj\t\n'
            '1\tsam2\tsam2\texample\tA2\tiTru7_101_02\tCTGTGTTG'
            '\tiTru5_01_B\tAGTGGCAA\texample_proj\t\n'
            '1\tblank1\tblank1\texample\tB1\tiTru7_101_03\tTGAGGTGT'
            '\tiTru5_01_C\tCACAGACT\texample_proj\t\n'
            '1\tsam3\tsam3\texample\tB2\tiTru7_101_04\tGATCCATG'
            '\tiTru5_01_D\tCGACACTT\texample_proj\t'
            )

        comment = (
            'PI\tKnight\ttheknight@fake.com\t\t\n'
            'Contact\tTest User\tAnother User\t'
            'Jon Jonny\tGregorio Orio\n'
            '\ttuser@fake.com\tanuser@fake.com\t'
            'jonjonny@foo.com\tgregOrio@foo.com\n'
            )

        data = (
            'Lane\tSample_ID\tSample_Name\tSample_Plate\tSample_Well\t'
            'I7_Index_ID\tindex\tI5_Index_ID\tindex2\tSample_Project\t'
            'Description\n'
            '1\tsam1\tsam1\texample\tA1\tiTru7_101_01\tACGTTACC\t'
            'iTru5_01_A\tACCGACAA\texample_proj\t\n'
            '1\tsam2\tsam2\texample\tA2\tiTru7_101_02\tCTGTGTTG\t'
            'iTru5_01_B\tAGTGGCAA\texample_proj\t\n'
            '1\tblank1\tblank1\texample\tB1\tiTru7_101_03\tTGAGGTGT\t'
            'iTru5_01_C\tCACAGACT\texample_proj\t\n'
            '1\tsam3\tsam3\texample\tB2\tiTru7_101_04\tGATCCATG\t'
            'iTru5_01_D\tCGACACTT\texample_proj\t'
            )

        sample_sheet_dict = {'comments': '',
                             'IEMFileVersion': '4',
                             'Investigator Name': 'Knight',
                             'Experiment Name': '',
                             'Date': '2017-08-13',
                             'Workflow': 'GenerateFASTQ',
                             'Application': 'FASTQ Only',
                             'Assay': 'Metagenomics',
                             'Description': '',
                             'Chemistry': 'Default',
                             'read1': 150,
                             'read2': 150,
                             'ReverseComplement': '0',
                             'data': data}

        obs_sample_sheet = SequencingProcess._format_sample_sheet(
            sample_sheet_dict, sep='\t')
        self.assertEqual(exp_sample_sheet, obs_sample_sheet)

        sample_sheet_dict_2 = {'comments': comment,
                               'IEMFileVersion': '4',
                               'Investigator Name': 'Knight',
                               'Experiment Name': '',
                               'Date': '2017-08-13',
                               'Workflow': 'GenerateFASTQ',
                               'Application': 'FASTQ Only',
                               'Assay': 'Metagenomics',
                               'Description': '',
                               'Chemistry': 'Default',
                               'read1': 150,
                               'read2': 150,
                               'ReverseComplement': '0',
                               'data': data}

        obs_sample_sheet_2 = SequencingProcess._format_sample_sheet(
            sample_sheet_dict_2, sep='\t')
        self.assertEqual(exp_sample_sheet_2, obs_sample_sheet_2)

    def test_generate_sample_sheet(self):
        # Sequencing run
        tester = SequencingProcess(1)
        obs = tester.generate_sample_sheet()
        exp = ('# PI,Dude,test@foo.bar\n'
               '# Contact,Admin,Demo,Shared\n'
               '# ,admin@foo.bar,demo@microbio.me,shared@foo.bar\n'
               '[Header]\n'
               'IEMFileVersion,4\n'
               'Investigator Name,Dude\n'
               'Experiment Name,TestExperiment1\n'
               'Date,2017-10-25\n'
               'Workflow,GenerateFASTQ\n'
               'Application,FASTQ Only\n'
               'Assay,Amplicon\n'
               'Description,\n'
               'Chemistry,Default\n\n'
               '[Reads]\n'
               '151\n'
               '151\n\n'
               '[Settings]\n'
               'ReverseComplement,0\n\n'
               '[Data]\n'
               'Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,'
               'index,Sample_Project,Description,,\n'
               'Test_Run_1,,,,,NNNNNNNNNNNN,,,,,\n')
        self.assertEqual(obs, exp)
        # Shotgun run
        tester = SequencingProcess(2)
        obs = tester.generate_sample_sheet().splitlines()
        exp = [
            '# PI,Dude,test@foo.bar',
            '# Contact,Demo,Shared',
            '# ,demo@microbio.me,shared@foo.bar',
            '[Header]',
            'IEMFileVersion,4',
            'Investigator Name,Dude',
            'Experiment Name,TestExperimentShotgun1',
            'Date,2017-10-25',
            'Workflow,GenerateFASTQ',
            'Application,FASTQ Only',
            'Assay,Metagenomics',
            'Description,',
            'Chemistry,Default',
            '',
            '[Reads]',
            '151',
            '151',
            '',
            '[Settings]',
            'ReverseComplement,0',
            '',
            '[Data]',
            'Lane,Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,'
            'index,I5_Index_ID,index2,Sample_Project,Description',
            '1,1_SKB1_640202,1_SKB1_640202,Test shotgun library plate 1,A1,'
            'iTru7_101_01,ACGTTACC,iTru5_01_A,TTGTCGGT,TestShotgunRun1,'
            '1.SKB1.640202']
        self.assertEqual(obs[:len(exp)], exp)
        exp = ('1,blank_21_H12,blank_21_H12,Test shotgun library plate 1,'
               'P24,iTru7_211_01,GCTTCTTG,iTru5_124_H,AAGGCGTT,'
               'TestShotgunRun1,blank.21.H12')
        self.assertEqual(obs[-1], exp)

    def test_generate_prep_information(self):
        # Sequencing run
        tester = SequencingProcess(1)
        obs = tester.generate_prep_information()
        exp = {Study(1): (
            'sample_name\texperiment\tfwd_cycles\tprincipal_investigator\t'
            'rev_cycles\trun_name\tsequencer_description\n'
            '1.SKB1.640202\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB2.640194\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB3.640195\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB4.640189\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB5.640181\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB6.640176\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB7.640196\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB8.640193\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKB9.640200\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKD1.640179\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKD2.640178\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n'
            '1.SKD3.640198\tTestExperiment1\t151\ttest@foo.bar\t151\t'
            'Test Run.1\tMiSeq\n')}
        self.assertEqual(obs, exp)

        # Shotgun run
        tester = SequencingProcess(2)
        obs = tester.generate_prep_information()
        exp = {Study(1): (
            'sample_name\texperiment\tfwd_cycles\ti5_sequence\t'
            'principal_investigator\trev_cycles\trun_name\t'
            'sequencer_description\n'
            '1.SKB1.640202\tTestExperimentShotgun1\t151\tGTCTAGGT\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB2.640194\tTestExperimentShotgun1\t151\tTGCTTGGT\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB3.640195\tTestExperimentShotgun1\t151\tCTCATCAG\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB4.640189\tTestExperimentShotgun1\t151\tCAAGTGCA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB5.640181\tTestExperimentShotgun1\t151\tGATAGCGA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB6.640176\tTestExperimentShotgun1\t151\tTGCGAACT\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB7.640196\tTestExperimentShotgun1\t151\tTTGTGTGC\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB8.640193\tTestExperimentShotgun1\t151\tGTGTGACA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKB9.640200\tTestExperimentShotgun1\t151\tGGTACTAC\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKD1.640179\tTestExperimentShotgun1\t151\tTGTAGCCA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKD2.640178\tTestExperimentShotgun1\t151\tCTTACAGC\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            '1.SKD3.640198\tTestExperimentShotgun1\t151\tTACATCGG\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H1\tTestExperimentShotgun1\t151\tCGTACGAA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H10\tTestExperimentShotgun1\t151\tCTGACACA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H11\tTestExperimentShotgun1\t151\tTGGTACAG\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H12\tTestExperimentShotgun1\t151\tGCTTCTTG\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H2\tTestExperimentShotgun1\t151\tCGACGTTA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H3\tTestExperimentShotgun1\t151\tCGTCAATG\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H4\tTestExperimentShotgun1\t151\tACGACAGA\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H5\tTestExperimentShotgun1\t151\tCGTAGGTT\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H6\tTestExperimentShotgun1\t151\tTGCTCATG\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H7\tTestExperimentShotgun1\t151\tGTCCACAT\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H8\tTestExperimentShotgun1\t151\tTAAGTGGC\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'blank.21.H9\tTestExperimentShotgun1\t151\tTCTCGTGT\t'
            'test@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G1\tTestExperimentShotgun1\t151\t'
            'GTGAGCTT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G10\tTestExperimentShotgun1\t151\t'
            'CCTCAGTT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G11\tTestExperimentShotgun1\t151\t'
            'GGTCAGAT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G12\tTestExperimentShotgun1\t151\t'
            'GAATCGTG\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G2\tTestExperimentShotgun1\t151\t'
            'CGACCATT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G3\tTestExperimentShotgun1\t151\t'
            'ATACTCCG\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G4\tTestExperimentShotgun1\t151\t'
            'AGCGTGTT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G5\tTestExperimentShotgun1\t151\t'
            'ACCTGACT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G6\tTestExperimentShotgun1\t151\t'
            'TCTAACGC\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G7\tTestExperimentShotgun1\t151\t'
            'GAGCTTGT\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G8\tTestExperimentShotgun1\t151\t'
            'AGCAGATG\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n'
            'vibrio.positive.control.21.G9\tTestExperimentShotgun1\t151\t'
            'GATGAGAC\ttest@foo.bar\t151\tTestShotgunRun1\tHiSeq4000\n')}
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
