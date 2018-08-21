# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from datetime import datetime, timezone
from io import StringIO
from re import escape, search

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


def _help_compare_timestamps(input_datetime):
    # can't really check that the timestamp is an exact value,
    # so instead check that current time (having just created process)
    # is within 60 seconds of time at which process was created.
    # This is a heuristic--may fail if you e.g. put a breakpoint
    # between create call and assertLess call.
    time_diff = datetime.now(timezone.utc) - input_datetime
    is_close = time_diff.total_seconds() < 60
    return is_close


def _help_make_datetime(input_datetime_str):
    # input_datetime_str should be in format '2017-10-25 19:10:25-0700'
    return datetime.strptime(input_datetime_str, '%Y-%m-%d %H:%M:%S%z')


def _help_format_datetime(input_datetime):
    # output datetime_str will be in format '2017-10-25 19:10'
    return datetime.strftime(input_datetime, Process.get_date_format())


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
        self.assertEqual(Process.factory(18),
                         GDNAPlateCompressionProcess(1))
        self.assertEqual(Process.factory(12),
                         LibraryPrep16SProcess(1))
        self.assertEqual(Process.factory(20),
                         NormalizationProcess(1))
        self.assertEqual(Process.factory(21),
                         LibraryPrepShotgunProcess(1))
        self.assertEqual(Process.factory(13),
                         QuantificationProcess(1))
        self.assertEqual(Process.factory(14),
                         QuantificationProcess(2))
        self.assertEqual(Process.factory(15), PoolingProcess(1))
        self.assertEqual(Process.factory(17), SequencingProcess(1))


class TestSamplePlatingProcess(LabmanTestCase):
    def test_attributes(self):
        tester = SamplePlatingProcess(10)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 10)
        self.assertEqual(tester.plate, Plate(21))

    def test_create(self):
        user = User('test@foo.bar')
        # 1 -> 96-well deep-well plate
        plate_config = PlateConfiguration(1)
        obs = SamplePlatingProcess.create(
            user, plate_config, 'Test Plate 1', 10)

        self.assertTrue(_help_compare_timestamps(obs.date))
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
        obs = SampleComposition(8)

        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'blank.21.H1')

        # Update a well from CONTROL -> EXPERIMENTAL SAMPLE
        self.assertEqual(
            tester.update_well(8, 1, '1.SKM8.640201'), ('1.SKM8.640201', True))
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKM8.640201')
        self.assertEqual(obs.content, '1.SKM8.640201')

        # Update a well from EXPERIMENTAL SAMPLE -> EXPERIMENTAL SAMPLE
        self.assertEqual(
            tester.update_well(8, 1, '1.SKB6.640176'),
            ('1.SKB6.640176.21.H1', True))
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKB6.640176')
        self.assertEqual(obs.content, '1.SKB6.640176.21.H1')

        # Update a well from EXPERIMENTAL SAMPLE -> CONTROL
        self.assertEqual(tester.update_well(8, 1, 'vibrio.positive.control'),
                         ('vibrio.positive.control.21.H1', True))
        self.assertEqual(obs.sample_composition_type,
                         'vibrio.positive.control')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'vibrio.positive.control.21.H1')

        # Update a well from CONROL -> CONTROL
        self.assertEqual(tester.update_well(8, 1, 'blank'),
                         ('blank.21.H1', True))
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)
        self.assertEqual(obs.content, 'blank.21.H1')

    def test_comment_well(self):
        tester = SamplePlatingProcess(10)
        obs = SampleComposition(8)

        self.assertIsNone(obs.notes)
        tester.comment_well(8, 1, 'New notes')
        self.assertEqual(obs.notes, 'New notes')
        tester.comment_well(8, 1, None)
        self.assertIsNone(obs.notes)

    def test_notes(self):
        tester = SamplePlatingProcess(10)

        self.assertIsNone(tester.notes)
        tester.notes = 'This note was set in a test'
        self.assertEqual(tester.notes, 'This note was set in a test')


class TestReagentCreationProcess(LabmanTestCase):
    def test_attributes(self):
        tester = ReagentCreationProcess(5)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-23 09:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 5)
        self.assertEqual(tester.tube, Tube(1))

    def test_create(self):
        user = User('test@foo.bar')
        obs = ReagentCreationProcess.create(user, 'Reagent external id', 10,
                                            'extraction kit')
        self.assertTrue(_help_compare_timestamps(obs.date))
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
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-23 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 3)
        exp_plates = [Plate(11), Plate(12), Plate(13), Plate(14),
                      Plate(15), Plate(16), Plate(17), Plate(18)]
        self.assertEqual(tester.primer_set, PrimerSet(1))
        self.assertEqual(tester.master_set_order, 'EMP PRIMERS MSON 1')
        self.assertEqual(tester.plates, exp_plates)

    def test_create(self):
        test_date = _help_make_datetime('2018-01-18 00:00:00-0700')
        user = User('test@foo.bar')
        primer_set = PrimerSet(1)
        obs = PrimerWorkingPlateCreationProcess.create(
            user, primer_set, 'Master Set Order 1',
            creation_date=test_date)
        self.assertEqual(obs.date, test_date)
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.primer_set, primer_set)
        self.assertEqual(obs.master_set_order, 'Master Set Order 1')

        obs_plates = obs.plates
        obs_date_str = _help_format_datetime(obs.date)  # checked good above
        self.assertEqual(len(obs_plates), 8)
        self.assertEqual(obs_plates[0].external_id,
                         'EMP 16S V4 primer plate 1 ' + obs_date_str)
        self.assertEqual(
            obs_plates[0].get_well(1, 1).composition.primer_set_composition,
            PrimerSetComposition(1))

        # This tests the edge case in which a plate already exists that has
        # the external id that would usually be generated by the create
        # process, in which case a 4-digit random number is added as a
        # disambiguator.
        obs = PrimerWorkingPlateCreationProcess.create(
            user, primer_set, 'Master Set Order 1',
            creation_date=test_date)
        obs_ext_id_str = obs.plates[0].external_id
        regex = r'EMP 16S V4 primer plate 1 ' + escape(obs_date_str) + \
                ' \d\d\d\d$'
        matches = search(regex, obs_ext_id_str)
        self.assertIsNotNone(matches)


class TestGDNAExtractionProcess(LabmanTestCase):
    def test_attributes(self):
        tester = GDNAExtractionProcess(1)

        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 11)
        self.assertEqual(tester.kingfisher, Equipment(11))
        self.assertEqual(tester.epmotion, Equipment(5))
        self.assertEqual(tester.epmotion_tool, Equipment(15))
        self.assertEqual(tester.extraction_kit, ReagentComposition(1))
        self.assertEqual(tester.sample_plate.id, 21)
        self.assertEqual(tester.volume, 10)
        self.assertEqual(tester.notes, None)

    def test_create(self):
        test_date = _help_make_datetime('2018-01-01 00:00:01-0700')
        user = User('test@foo.bar')
        ep_robot = Equipment(6)
        kf_robot = Equipment(11)
        tool = Equipment(15)
        kit = ReagentComposition(1)
        plate = Plate(21)
        notes = 'test note'
        obs = GDNAExtractionProcess.create(
            user, plate, kf_robot, ep_robot, tool, kit, 10,
            'gdna - Test plate 1',
            extraction_date=test_date, notes=notes)
        self.assertEqual(obs.date, test_date)
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.kingfisher, Equipment(11))
        self.assertEqual(obs.epmotion, Equipment(6))
        self.assertEqual(obs.epmotion_tool, Equipment(15))
        self.assertEqual(obs.extraction_kit, ReagentComposition(1))
        self.assertEqual(obs.sample_plate, Plate(21))
        self.assertEqual(obs.volume, 10)
        self.assertEqual(obs.notes, 'test note')

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
                if i == 7 and j == 11:
                    # The last well of the plate is an empty well
                    self.assertIsNone(well)
                else:
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
        tester = GDNAPlateCompressionProcess(1)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 18)
        self.assertEqual(tester.plates, [Plate(24)])
        self.assertEqual(tester.robot, Equipment(1))
        self.assertEqual(tester.gdna_plates, [Plate(22), Plate(28), Plate(31),
                                              Plate(34)])

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
        ep1 = GDNAExtractionProcess.create(
            user, plateA, Equipment(11), ep_robot, tool, kit, 100,
            'gdna - Test Comp 1')
        ep2 = GDNAExtractionProcess.create(
            user, plateB, Equipment(12), ep_robot, tool, kit, 100,
            'gdna - Test Comp 2')

        obs = GDNAPlateCompressionProcess.create(
            user, [ep1.plates[0], ep2.plates[0]], 'Compressed plate AB',
            Equipment(1))
        self.assertTrue(_help_compare_timestamps(obs.date))
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
            self.assertEqual(
                well.composition.gdna_composition.sample_composition.sample_id,
                sample_id)

        # In these positions we did not have an origin plate, do not store
        # anything, this way we can differentiate from blanks and save
        # reagents during library prep
        for col in range(0, 15):
            self.assertIsNone(obs_layout[1][col])

        self.assertEqual(obs.robot, Equipment(1))
        self.assertEqual(obs.gdna_plates, [ep1.plates[0], ep2.plates[0]])


class TestLibraryPrep16SProcess(LabmanTestCase):
    def test_attributes(self):
        tester = LibraryPrep16SProcess(1)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 02:10:25-0200'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 12)
        self.assertEqual(tester.mastermix, ReagentComposition(2))
        self.assertEqual(tester.water_lot, ReagentComposition(3))
        self.assertEqual(tester.epmotion, Equipment(8))
        self.assertEqual(tester.epmotion_tm300_tool, Equipment(16))
        self.assertEqual(tester.epmotion_tm50_tool, Equipment(17))
        self.assertEqual(tester.gdna_plate.id, 22) # Plate(22))
        self.assertEqual(tester.primer_plate, Plate(11))
        self.assertEqual(tester.volume, 10)

    def test_create(self):
        user = User('test@foo.bar')
        master_mix = ReagentComposition(2)
        water = ReagentComposition(3)
        robot = Equipment(8)
        tm300_8_tool = Equipment(16)
        tm50_8_tool = Equipment(17)
        volume = 75
        plates = [(Plate(22), Plate(11))]
        obs = LibraryPrep16SProcess.create(
            user, Plate(22), Plate(11), 'New 16S plate', robot,
            tm300_8_tool, tm50_8_tool, master_mix, water, volume)
        self.assertTrue(_help_compare_timestamps(obs.date))
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.mastermix, ReagentComposition(2))
        self.assertEqual(obs.water_lot, ReagentComposition(3))
        self.assertEqual(obs.epmotion, Equipment(8))
        self.assertEqual(obs.epmotion_tm300_tool, Equipment(16))
        self.assertEqual(obs.epmotion_tm50_tool, Equipment(17))
        self.assertEqual(obs.gdna_plate, Plate(22))
        self.assertEqual(obs.primer_plate, Plate(11))
        self.assertEqual(obs.volume, 75)

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
                if i == 7 and j == 11:
                    self.assertIsNone(well)
                else:
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
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 20)
        self.assertEqual(tester.quantification_process,
                         QuantificationProcess(3))
        self.assertEqual(tester.water_lot, ReagentComposition(3))
        exp = {'function': 'default',
               'parameters' : {'total_volume': 3500, 'target_dna': 5,
                               'min_vol': 2.5, 'max_volume': 3500,
                               'resolution': 2.5, 'reformat': False}}
        self.assertEqual(tester.normalization_function_data, exp)
        self.assertEqual(tester.compressed_plate, Plate(24))

    def test_create(self):
        user = User('test@foo.bar')
        water = ReagentComposition(3)
        obs = NormalizationProcess.create(
            user, QuantificationProcess(3), water, 'Create-Norm plate 1')
        self.assertTrue(_help_compare_timestamps(obs.date))
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.quantification_process,
                         QuantificationProcess(3))
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
        obs = NormalizationProcess(2).generate_echo_picklist()
        self.assertEqual(obs, NORM_PROCESS_PICKLIST)


class TestQuantificationProcess(LabmanTestCase):
    def test_compute_pico_concentration(self):
        dna_vals = np.array([[10.14, 7.89, 7.9, 15.48],
                             [7.86, 8.07, 8.16, 9.64],
                             [12.29, 7.64, 7.32, 13.74]])
        obs = QuantificationProcess._compute_pico_concentration(
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

    def test_rationalize_pico_csv_string(self):
        pico_csv = ('Results					\r'
                    '					\r'
                    'Well ID\tWell\t[Blanked-RFU]\t[Concentration]		\r'
                    'SPL1\tA1\t<0.000\t3.432		\r'
                    'SPL2\tA2\t4949.000\t3.239		\r'
                    'SPL3\tB1\t>15302.000\t10.016		\r'
                    'SPL4\tB2\t4039.000\t2.644		\r'
                    '					\r'
                    'Curve2 Fitting Results					\r'
                    '					\r'
                    'Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob\r'
                    'Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????')

        expected_output = (
            'Results					\n'
            '					\n'
            'Well ID\tWell\t[Blanked-RFU]\t[Concentration]		\n'
            'SPL1\tA1\t0.000\t3.432		\n'
            'SPL2\tA2\t4949.000\t3.239		\n'
            'SPL3\tB1\t15302.000\t10.016		\n'
            'SPL4\tB2\t4039.000\t2.644		\n'
            '					\n'
            'Curve2 Fitting Results					\n'
            '					\n'
            'Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob\n'
            'Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????')
        output = QuantificationProcess._rationalize_pico_csv_string(pico_csv)
        self.assertEqual(output, expected_output)

    def test_parse_pico_csv(self):
        # Test a normal sheet
        pico_csv1 = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t4039.000\t2.644 

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        exp_pico_df1 = pd.DataFrame({'Well': ['A1', 'A2', 'B1', 'B2'],
                                    'Sample DNA Concentration':
                                        [3.432, 3.239, 10.016, 2.644]})
        obs_pico_df1 = QuantificationProcess._parse_pico_csv(pico_csv1)
        pd.testing.assert_frame_equal(obs_pico_df1, exp_pico_df1,
                                      check_like=True)

        # Test a sheet that has some ????, <, and > values
        pico_csv2 = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t>3.432
        SPL2\tA2\t4949.000\t<0.000
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t\t?????

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        exp_pico_df2 = pd.DataFrame({'Well': ['A1', 'A2', 'B1', 'B2'],
                                    'Sample DNA Concentration':
                                        [3.432, 0.000, 10.016, 10.016]})
        obs_pico_df2 = QuantificationProcess._parse_pico_csv(pico_csv2)
        pd.testing.assert_frame_equal(obs_pico_df2, exp_pico_df2,
                                      check_like=True)

        # Test a sheet that has unexpected value that can't be converted to #
        pico_csv3 = '''Results

        Well ID\tWell\t[Blanked-RFU]\t[Concentration]
        SPL1\tA1\t5243.000\t3.432
        SPL2\tA2\t4949.000\t3.239
        SPL3\tB1\t15302.000\t10.016
        SPL4\tB2\t\tfail

        Curve2 Fitting Results

        Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob
        Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????
        '''
        with self.assertRaises(ValueError):
            QuantificationProcess._parse_pico_csv(pico_csv3)

    def test_parse(self):
        # Test a normal sheet
        # Note that the pico output file appears to have \r (NOT \r\n)
        # line endings
        pico_csv = ('Results					\r'
                    '					\r'
                    'Well ID\tWell\t[Blanked-RFU]\t[Concentration]		\r'
                    'SPL1\tA1\t5243.000\t3.432		\r'
                    'SPL2\tA2\t4949.000\t3.239		\r'
                    'SPL3\tB1\t15302.000\t10.016		\r'
                    'SPL4\tB2\t4039.000\t2.644		\r'
                    '					\r'
                    'Curve2 Fitting Results					\r'
                    '					\r'
                    'Curve Name\tCurve Formula\tA\tB\tR2\tFit F Prob\r'
                    'Curve2\tY=A*X+B\t1.53E+003\t0\t0.995\t?????')

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
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:05-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 13)
        self.assertEqual(tester.notes,None)
        obs = tester.concentrations
        # 380 because quantified 4 96-well plates in one process (and each
        # plate has one empty well, hence 380 rather than 384)
        self.assertEqual(len(obs), 380)
        self.assertEqual(obs[0],
                         (LibraryPrep16SComposition(1), 20.0, 60.606))
        self.assertEqual(obs[36],
                         (LibraryPrep16SComposition(37), 20.0, 60.606))
        self.assertEqual(obs[7],
                         (LibraryPrep16SComposition(8), 1.0, 3.0303))  # blank

        tester = QuantificationProcess(4)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 22)
        self.assertEqual(tester.notes,None)
        obs = tester.concentrations
        self.assertEqual(len(obs), 380)
        self.assertEqual(  # experimental sample
            obs[0], (LibraryPrepShotgunComposition(1), 12.068, 36.569))
        self.assertEqual(  # vibrio
            obs[6], (LibraryPrepShotgunComposition(7), 8.904, 26.981))
        self.assertEqual(  # blank
            obs[7], (LibraryPrepShotgunComposition(8), 0.342, 1.036))

        tester = QuantificationProcess(5)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-26 03:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 26)
        self.assertEqual(tester.notes,"Requantification--oops")
        obs = tester.concentrations
        self.assertEqual(len(obs), 380)
        self.assertEqual(
            obs[0], (LibraryPrepShotgunComposition(1), 13.068, 38.569))
        self.assertEqual(
            obs[6], (LibraryPrepShotgunComposition(7), 9.904, 28.981))
        self.assertEqual(
            obs[7], (LibraryPrepShotgunComposition(8), 1.342, 3.036))

    def test_create(self):
        user = User('test@foo.bar')
        plate = Plate(23)
        concentrations = np.around(np.random.rand(8, 12), 6)

        # Add some known values for DNA concentration
        concentrations[0][0] = 3
        concentrations[0][1] = 4
        concentrations[0][2] = 40
        # Set blank wells to zero DNA concentrations
        concentrations[7] = np.zeros_like(concentrations[7])

        # add DNA concentrations to plate and check for sanity
        obs = QuantificationProcess.create(user, plate, concentrations)
        self.assertTrue(_help_compare_timestamps(obs.date))
        self.assertEqual(obs.personnel, user)
        obs_c = obs.concentrations
        self.assertEqual(len(obs_c), 95)
        self.assertEqual(obs_c[0][0], LibraryPrep16SComposition(1))
        npt.assert_almost_equal(obs_c[0][1], concentrations[0][0])
        self.assertIsNone(obs_c[0][2])
        self.assertEqual(obs_c[12][0], LibraryPrep16SComposition(2))  # B1
        npt.assert_almost_equal(obs_c[12][1], concentrations[1][0])
        self.assertIsNone(obs_c[12][2])

        # compute library concentrations (nM) from DNA concentrations (ng/uL)
        obs.compute_concentrations()
        obs_c = obs.concentrations
        # Check the values that we know
        npt.assert_almost_equal(obs_c[0][2], 9.09091)
        npt.assert_almost_equal(obs_c[1][2], 12.1212)
        npt.assert_almost_equal(obs_c[2][2], 121.212)
        # Last row are all 0 because they're blanks
        for i in range(84, 95):
            npt.assert_almost_equal(obs_c[i][2], 0)

        note = "a test note"
        concentrations = np.around(np.random.rand(16, 24), 6)
        # Add some known values
        concentrations[0][0] = 10.14
        concentrations[0][1] = 7.89
        plate = Plate(26)
        obs = QuantificationProcess.create(user, plate, concentrations, note)
        self.assertTrue(_help_compare_timestamps(obs.date))
        self.assertEqual(obs.personnel, user)
        obs_c = obs.concentrations
        self.assertEqual(len(obs_c), 380)
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
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 21)
        self.assertEqual(tester.kappa_hyper_plus_kit, ReagentComposition(4))
        self.assertEqual(tester.stub_lot, ReagentComposition(5))
        self.assertEqual(tester.normalization_process, NormalizationProcess(1))
        self.assertEqual(tester.normalized_plate, Plate(25))
        self.assertEqual(tester.i5_primer_plate, Plate(19))
        self.assertEqual(tester.i7_primer_plate, Plate(20))
        self.assertEqual(tester.volume, 4000)

    def test_create(self):
        user = User('test@foo.bar')
        plate = Plate(25)
        kappa = ReagentComposition(4)
        stub = ReagentComposition(5)
        obs = LibraryPrepShotgunProcess.create(
            user, plate, 'Test Shotgun Library 1', kappa, stub, 4000,
            Plate(19), Plate(20))
        self.assertTrue(_help_compare_timestamps(obs.date))
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.kappa_hyper_plus_kit, kappa)
        self.assertEqual(obs.stub_lot, stub)
        self.assertEqual(obs.normalization_process, NormalizationProcess(1))
        self.assertEqual(obs.normalized_plate, Plate(25))
        self.assertEqual(obs.i5_primer_plate, Plate(19))
        self.assertEqual(obs.i7_primer_plate, Plate(20))
        self.assertEqual(obs.volume, 4000)

        plates = obs.plates
        self.assertEqual(len(plates), 1)
        layout = plates[0].layout
        self.assertEqual(layout[0][0].composition.i5_composition,
                         PrimerComposition(1523))
        self.assertEqual(layout[0][0].composition.i7_composition,
                         PrimerComposition(1524))
        self.assertIsNone(layout[-1][-1])

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
            '1.SKB1.640202.21.A1\tiTru 5 primer\t384LDV_AQ_B2_HT\tA1\t250\t'
            'iTru5_01_A\tACCGACAA\tIndexPCRPlate\tA1')
        self.assertEqual(
            obs_lines[-1],
            'blank.33.H11\tiTru 7 primer\t384LDV_AQ_B2_HT\tP2\t250\t'
            'iTru7_115_01\tCAAGGTCT\tIndexPCRPlate\tP22')


class TestPoolingProcess(LabmanTestCase):
    def test_compute_pooling_values_eqvol(self):
        qpcr_conc = np.array(
            [[98.14626462, 487.8121413, 484.3480866, 2.183406934],
             [498.3536649, 429.0839787, 402.4270321, 140.1601735],
             [21.20533391, 582.9456031, 732.2655041, 7.545145988]])
        obs_sample_vols = PoolingProcess.compute_pooling_values_eqvol(
            qpcr_conc, total_vol=60.0)
        exp_sample_vols = np.zeros([3, 4]) + 5000
        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

        obs_sample_vols = PoolingProcess.compute_pooling_values_eqvol(
            qpcr_conc, total_vol=60)
        npt.assert_allclose(obs_sample_vols, exp_sample_vols)

    def test_compute_pooling_values_minvol(self):
        sample_concs = np.array([[1, 12, 400], [200, 40, 1]])
        exp_vols = np.array([[100, 100, 4166.6666666666],
                             [8333.33333333333, 41666.666666666, 100]])
        obs_vols = PoolingProcess.compute_pooling_values_minvol(
            sample_concs, total=.01, floor_vol=100, floor_conc=40,
            total_each=False, vol_constant=10**9)
        npt.assert_allclose(exp_vols, obs_vols)

    def test_compute_pooling_values_minvol_amplicon(self):
        sample_concs = np.array([[1, 12, 40], [200, 40, 1]])
        exp_vols = np.array([[2, 2, 6],
                             [1.2, 6, 2]])
        obs_vols = PoolingProcess.compute_pooling_values_minvol(
            sample_concs)
        npt.assert_allclose(exp_vols, obs_vols)

    def test_adjust_blank_vols(self):
        pool_vols = np.array([[2, 2, 6],
                              [1.2, 6, 2]])

        pool_blanks = np.array([[True, False, False],
                                [False, False, True]])

        blank_vol = 1

        exp_vols = np.array([[1, 2, 6],
                              [1.2, 6, 1]])

        obs_vols = PoolingProcess.adjust_blank_vols(pool_vols,
                                                    pool_blanks,
                                                    blank_vol)

        npt.assert_allclose(obs_vols, exp_vols)

    def test_select_blanks(self):
        pool_vols = np.array([[2, 2, 6],
                              [1.2, 6, 2]])

        pool_concs = np.array([[3, 2, 6],
                               [1.2, 6, 2]])

        pool_blanks = np.array([[True, False, False],
                                [False, False, True]])

        exp_vols1 = np.array([[2, 2, 6],
                              [1.2, 6, 0]])

        obs_vols1 = PoolingProcess.select_blanks(pool_vols,
                                                pool_concs,
                                                pool_blanks,
                                                1)

        npt.assert_allclose(obs_vols1, exp_vols1)

        exp_vols2 = np.array([[2, 2, 6],
                              [1.2, 6, 2]])

        obs_vols2 = PoolingProcess.select_blanks(pool_vols,
                                                pool_concs,
                                                pool_blanks,
                                                2)

        npt.assert_allclose(obs_vols2, exp_vols2)


        exp_vols0 = np.array([[0, 2, 6],
                              [1.2, 6, 0]])

        obs_vols0 = PoolingProcess.select_blanks(pool_vols,
                                                pool_concs,
                                                pool_blanks,
                                                0)

        npt.assert_allclose(obs_vols0, exp_vols0)

    def test_select_blanks_num_errors(self):
        pool_vols = np.array([[2, 2, 6],
                              [1.2, 6, 2]])

        pool_concs = np.array([[3, 2, 6],
                               [1.2, 6, 2]])

        pool_blanks = np.array([[True, False, False],
                                [False, False, True]])

        with self.assertRaisesRegex(ValueError, "(passed: -1)"):
            PoolingProcess.select_blanks(pool_vols,
                                         pool_concs,
                                         pool_blanks,
                                         -1)

    def test_select_blanks_shape_errors(self):
        pool_vols = np.array([[2, 2, 6],
                              [1.2, 6, 2],
                              [1.2, 6, 2]])

        pool_concs = np.array([[3, 2, 6],
                               [1.2, 6, 2]])

        pool_blanks = np.array([[True, False, False],
                                [False, False, True]])

        with self.assertRaisesRegex(ValueError, "all input arrays"):
            PoolingProcess.select_blanks(pool_vols,
                                         pool_concs,
                                         pool_blanks,
                                         2)

    def test_attributes(self):
        tester = PoolingProcess(1)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 15)
        self.assertEqual(tester.quantification_process,
                         QuantificationProcess(1))
        self.assertEqual(tester.robot, Equipment(8))
        self.assertEqual(tester.destination, '1')
        self.assertEqual(tester.pool, PoolComposition(1))
        components = tester.components
        self.assertEqual(len(components), 95)
        self.assertEqual(
            components[0], (LibraryPrep16SComposition(1), 1.0))
        self.assertEqual(
            components[36], (LibraryPrep16SComposition(37), 1.0))
        self.assertEqual(
            components[94], (LibraryPrep16SComposition(95), 1.0))

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
        func_data = {"function": "amplicon",
                     "parameters": {"dna_amount": 240, "min_val": 1,
                                    "max_val": 15, "blank_volume": 2}}
        obs = PoolingProcess.create(user, quant_proc, 'New test pool name', 4,
                                    input_compositions, func_data, robot, '1')
        self.assertTrue(_help_compare_timestamps(obs.date))
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.quantification_process, quant_proc)
        self.assertEqual(obs.robot, robot)
        self.assertEqual(obs.pooling_function_data, func_data)

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
                         '1,384LDV_AQ_B2_HT,P24,,0.00,NormalizedDNA,A1')

    def test_generate_epmotion_file(self):
        obs = PoolingProcess(1).generate_epmotion_file()
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0], 'Rack,Source,Rack,Destination,Volume,Tool')
        self.assertEqual(obs_lines[1], '1,A1,1,1,1.000,1')
        self.assertEqual(obs_lines[-1], '1,G12,1,1,1.000,1')

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
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 17)
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

        self.assertEqual(obs[0], {'process_id': 17,
                                  'run_name': 'Test Run.1',
                                  'sequencing_process_id': 1,
                                  'experiment': 'TestExperiment1',
                                  'sequencer_id': 18,
                                  'fwd_cycles': 151,
                                  'rev_cycles': 151,
                                  'assay': 'Amplicon',
                                  'principal_investigator': 'test@foo.bar'})
        self.assertEqual(obs[1], {'process_id': 24,
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

        self.assertTrue(_help_compare_timestamps(obs.date))
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
            ',index2,Sample_Project,Well_Description\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,,\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,labperson1_pi1_studyId1,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,labperson1_pi1_studyId1,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,labperson1_pi1_studyId1,'
            )

        wells = ['A1', 'A2', 'B1', 'B2']
        sample_ids = ['sam1', 'sam2', 'blank1', 'sam3']
        sample_projs = ["labperson1_pi1_studyId1", "labperson1_pi1_studyId1",
                        "", "labperson1_pi1_studyId1"]
        i5_name = ['iTru5_01_A', 'iTru5_01_B', 'iTru5_01_C', 'iTru5_01_D']
        i5_seq = ['ACCGACAA', 'AGTGGCAA', 'CACAGACT', 'CGACACTT']
        i7_name = ['iTru7_101_01', 'iTru7_101_02',
                   'iTru7_101_03', 'iTru7_101_04']
        i7_seq = ['ACGTTACC', 'CTGTGTTG', 'TGAGGTGT', 'GATCCATG']
        sample_plates = ['example'] * 4

        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, sample_projs,
            wells=wells, sample_plates=sample_plates, lanes=[1])
        self.assertEqual(obs_data, exp_data)

        # test that two lanes works
        exp_data_2 = (
            'Lane,Sample_ID,Sample_Name,Sample_Plate,'
            'Sample_Well,I7_Index_ID,index,I5_Index_ID,'
            'index2,Sample_Project,Well_Description\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,,\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,labperson1_pi1_studyId1,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,labperson1_pi1_studyId1,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,labperson1_pi1_studyId1,\n'
            '2,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT'
            ',iTru5_01_C,CACAGACT,,\n'
            '2,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,labperson1_pi1_studyId1,\n'
            '2,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,labperson1_pi1_studyId1,\n'
            '2,sam3,sam3,example,B2,iTru7_101_04,GATCCATG'
            ',iTru5_01_D,CGACACTT,labperson1_pi1_studyId1,')

        obs_data_2 = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, sample_projs, wells=wells,
            sample_plates=sample_plates,
            lanes=[1, 2])
        self.assertEqual(obs_data_2, exp_data_2)

        # test with r/c i5 barcodes
        exp_data = (
            'Lane,Sample_ID,Sample_Name,Sample_Plate'
            ',Sample_Well,I7_Index_ID,index,I5_Index_ID'
            ',index2,Sample_Project,Well_Description\n'
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,,\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,labperson1_pi1_studyId1,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,labperson1_pi1_studyId1,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,labperson1_pi1_studyId1,')

        i5_seq = ['ACCGACAA', 'AGTGGCAA', 'CACAGACT', 'CGACACTT']
        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, sample_projs, wells=wells,
            sample_plates=sample_plates, lanes=[1])
        self.assertEqual(obs_data, exp_data)

        # Test without header
        exp_data = (
            '1,blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,,\n'
            '1,sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,labperson1_pi1_studyId1,\n'
            '1,sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,labperson1_pi1_studyId1,\n'
            '1,sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,labperson1_pi1_studyId1,')

        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, sample_projs, wells=wells,
            sample_plates=sample_plates, lanes=[1],
            include_header=False)
        self.assertEqual(obs_data, exp_data)

        # Test without lane index (for single-lane sequencers)
        exp_data = (
            'Sample_ID,Sample_Name,Sample_Plate'
            ',Sample_Well,I7_Index_ID,index,I5_Index_ID'
            ',index2,Sample_Project,Well_Description\n'
            'blank1,blank1,example,B1,iTru7_101_03,TGAGGTGT,'
            'iTru5_01_C,CACAGACT,,\n'
            'sam1,sam1,example,A1,iTru7_101_01,ACGTTACC,'
            'iTru5_01_A,ACCGACAA,labperson1_pi1_studyId1,\n'
            'sam2,sam2,example,A2,iTru7_101_02,CTGTGTTG,'
            'iTru5_01_B,AGTGGCAA,labperson1_pi1_studyId1,\n'
            'sam3,sam3,example,B2,iTru7_101_04,GATCCATG,'
            'iTru5_01_D,CGACACTT,labperson1_pi1_studyId1,')

        obs_data = SequencingProcess._format_sample_sheet_data(
            sample_ids, i7_name, i7_seq, i5_name, i5_seq, sample_projs, wells=wells,
            sample_plates=sample_plates, lanes=[1],
            include_lane=False)
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
            'Contact emails\tanuser@fake.com\tgregOrio@foo.com'
            '\tjonjonny@foo.com\ttuser@fake.com\n')
        obs_comment = SequencingProcess._format_sample_sheet_comments(
            principal_investigator, contacts, other, sep)
        self.assertEqual(exp_comment, obs_comment)

    def test_format_sample_sheet(self):
        tester2 = SequencingProcess(2)
        tester2_date_str = _help_format_datetime(tester2.date)
        # Note: cannot hard-code the date in the below known-good text
        # because date string representation is specific to time-zone in
        # which system running the tests is located!
        exp2 = (
            '# PI,Dude,test@foo.bar',
            '# Contact,Demo,Shared',
            '# Contact emails,demo@microbio.me,shared@foo.bar',
            '[Header]',
            'IEMFileVersion\t4',
            'Investigator Name\tDude',
            'Experiment Name\tTestExperimentShotgun1',
            'Date\t' + tester2_date_str,
            'Workflow\tGenerateFASTQ',
            'Application\tFASTQ Only',
            'Assay\tMetagenomics',
            'Description\t',
            'Chemistry\tDefault',
            '',
            '[Reads]',
            '151',
            '151',
            '',
            '[Settings]',
            'ReverseComplement\t0',
            '',
            '[Data]\n'
            'Sample_ID\tSample_Name\tSample_Plate\tSample_Well'
            '\tI7_Index_ID\tindex\tI5_Index_ID\tindex2\tSample_Project'
            '\tWell_Description',
            'sam1\tsam1\texample\tA1\tiTru7_101_01\tACGTTACC\tiTru5_01_A'
            '\tACCGACAA\texample_proj\t',
            'sam2\tsam2\texample\tA2\tiTru7_101_02\tCTGTGTTG\tiTru5_01_B'
            '\tAGTGGCAA\texample_proj\t',
            'blank1\tblank1\texample\tB1\tiTru7_101_03\tTGAGGTGT\t'
            'iTru5_01_C\tCACAGACT\texample_proj\t',
            'sam3\tsam3\texample\tB2\tiTru7_101_04\tGATCCATG\tiTru5_01_D'
            '\tCGACACTT\texample_proj\t')

        data = (
            'Sample_ID\tSample_Name\tSample_Plate\tSample_Well\t'
            'I7_Index_ID\tindex\tI5_Index_ID\tindex2\tSample_Project\t'
            'Well_Description\n'
            'sam1\tsam1\texample\tA1\tiTru7_101_01\tACGTTACC\t'
            'iTru5_01_A\tACCGACAA\texample_proj\t\n'
            'sam2\tsam2\texample\tA2\tiTru7_101_02\tCTGTGTTG\t'
            'iTru5_01_B\tAGTGGCAA\texample_proj\t\n'
            'blank1\tblank1\texample\tB1\tiTru7_101_03\tTGAGGTGT\t'
            'iTru5_01_C\tCACAGACT\texample_proj\t\n'
            'sam3\tsam3\texample\tB2\tiTru7_101_04\tGATCCATG\t'
            'iTru5_01_D\tCGACACTT\texample_proj\t'
            )

        exp_sample_sheet = "\n".join(exp2)
        obs_sample_sheet = tester2._format_sample_sheet(data, sep='\t')
        self.assertEqual(exp_sample_sheet, obs_sample_sheet)

    def test_generate_sample_sheet(self):
        # Amplicon run, single lane
        tester = SequencingProcess(1)
        tester_date_str = _help_format_datetime(tester.date)
        # Note: cannot hard-code the date in the below known-good text
        # because date string representation is specific to time-zone in
        # which system running the tests is located!
        obs = tester.generate_sample_sheet()
        exp = ('# PI,Dude,test@foo.bar\n'
               '# Contact,Admin,Demo,Shared\n'
               '# Contact emails,admin@foo.bar,demo@microbio.me,'
               'shared@foo.bar\n'
               '[Header]\n'
               'IEMFileVersion,4\n'
               'Investigator Name,Dude\n'
               'Experiment Name,TestExperiment1\n'
               'Date,' + tester_date_str + '\n'
               'Workflow,GenerateFASTQ\n'
               'Application,FASTQ Only\n'
               'Assay,TruSeq HT\n'
               'Description,\n'
               'Chemistry,Amplicon\n\n'
               '[Reads]\n'
               '151\n'
               '151\n\n'
               '[Settings]\n'
               'ReverseComplement,0\n'
               'Adapter,AGATCGGAAGAGCACACGTCTGAACTCCAGTCA\n'
               'AdapterRead2,AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGT\n\n'
               '[Data]\n'
               'Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,'
               'index,I5_Index_ID,index2,Sample_Project,Well_Description,,\n'
               'Test_sequencing_pool_1,,,,,NNNNNNNNNNNN,,,,3079,,,')
        self.assertEqual(obs, exp)

        # Amplicon run, multiple lane
        user = User('test@foo.bar')
        tester = SequencingProcess.create(
            user, [PoolComposition(1), PoolComposition(2)], 'TestRun2',
            'TestExperiment2', Equipment(19), 151, 151, user,
            contacts=[User('shared@foo.bar')])
        tester_date_str = _help_format_datetime(tester.date)
        obs = tester.generate_sample_sheet()
        exp = ('# PI,Dude,test@foo.bar\n'
               '# Contact,Shared\n'
               '# Contact emails,shared@foo.bar\n'
               '[Header]\n'
               'IEMFileVersion,4\n'
               'Investigator Name,Dude\n'
               'Experiment Name,TestExperiment2\n'
               'Date,' + tester_date_str + '\n'
               'Workflow,GenerateFASTQ\n'
               'Application,FASTQ Only\n'
               'Assay,TruSeq HT\n'
               'Description,\n'
               'Chemistry,Amplicon\n\n'
               '[Reads]\n'
               '151\n'
               '151\n\n'
               '[Settings]\n'
               'ReverseComplement,0\n'
               'Adapter,AGATCGGAAGAGCACACGTCTGAACTCCAGTCA\n'
               'AdapterRead2,AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGT\n\n'
               '[Data]\n'
               'Lane,Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,'
               'index,I5_Index_ID,index2,Sample_Project,Well_Description,,\n'
               '1,Test_Pool_from_Plate_1,,,,,NNNNNNNNNNNN,,,,3078,,,\n'
               '2,Test_sequencing_pool_1,,,,,NNNNNNNNNNNN,,,,3079,,,')
        self.assertEqual(obs, exp)

        # Shotgun run
        tester = SequencingProcess(2)
        tester_date_str = _help_format_datetime(tester.date)
        obs = tester.generate_sample_sheet().splitlines()
        exp = [
            '# PI,Dude,test@foo.bar',
            '# Contact,Demo,Shared',
            '# Contact emails,demo@microbio.me,shared@foo.bar',
            '[Header]',
            'IEMFileVersion,4',
            'Investigator Name,Dude',
            'Experiment Name,TestExperimentShotgun1',
            'Date,' + tester_date_str,
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
            'index,I5_Index_ID,index2,Sample_Project,Well_Description',
            '1,1_SKB1_640202_21_A1,1_SKB1_640202_21_A1,'
            'Test shotgun library plates 1-4,A1,iTru7_101_01,ACGTTACC,iTru5_01_A,'
            'TTGTCGGT,LabDude_PIDude_1,1.SKB1.640202.21.A1']
        self.assertEqual(obs[:len(exp)], exp)
        exp = ('1,vibrio_positive_control_33_G9,vibrio_positive_control_33_G9,'
               'Test shotgun library plates 1-4,N18,iTru7_401_08,CGTAGGTT,'
               'iTru5_120_F,CATGAGGA,Controls,'
               'vibrio.positive.control.33.G9')
        self.assertEqual(obs[-1], exp)

        # unrecognized assay type
        tester = SequencingProcess(3)
        with self.assertRaises(ValueError):
            obs = tester.generate_sample_sheet()

    # This needs to be in it's own class so we know that the DB is fresh
    # and the data hasn't changed due other tests.
    def test_generate_prep_information(self):
        # Sequencing run
        tester = SequencingProcess(1)
        obs = tester.generate_prep_information()
        exp = {Study(1): TARGET_EXAMPLE}
        self.assertEqual(obs[Study(1)], exp[Study(1)])

        # Shotgun run
        tester = SequencingProcess(2)
        obs = tester.generate_prep_information()
        exp = {Study(1): SHOTGUN_EXAMPLE}
        self.assertEqual(obs[Study(1)], exp[Study(1)])

# flake8: noqa
NORM_PROCESS_PICKLIST = 'Sample\tSource Plate Name\tSource Plate Type\tSource Well\tConcentration\tTransfer Volume\tDestination Plate Name\tDestination Well\n1.SKB1.640202.21.A1\tWater\t384PP_AQ_BP2_HT\tA1\t12.068\t3085.0\tNormalizedDNA\tA1\n1.SKB2.640194.21.B1\tWater\t384PP_AQ_BP2_HT\tC1\t12.068\t3085.0\tNormalizedDNA\tC1\n1.SKB3.640195.21.C1\tWater\t384PP_AQ_BP2_HT\tE1\t12.068\t3085.0\tNormalizedDNA\tE1\n1.SKB4.640189.21.D1\tWater\t384PP_AQ_BP2_HT\tG1\t12.068\t3085.0\tNormalizedDNA\tG1\n1.SKB5.640181.21.E1\tWater\t384PP_AQ_BP2_HT\tI1\t12.068\t3085.0\tNormalizedDNA\tI1\n1.SKB6.640176.21.F1\tWater\t384PP_AQ_BP2_HT\tK1\t12.068\t3085.0\tNormalizedDNA\tK1\nvibrio.positive.control.21.G1\tWater\t384PP_AQ_BP2_HT\tM1\t6.089\t2680.0\tNormalizedDNA\tM1\nblank.21.H1\tWater\t384PP_AQ_BP2_HT\tO1\t0.342\t0.0\tNormalizedDNA\tO1\n1.SKB1.640202.21.A2\tWater\t384PP_AQ_BP2_HT\tA3\t12.068\t3085.0\tNormalizedDNA\tA3\n1.SKB2.640194.21.B2\tWater\t384PP_AQ_BP2_HT\tC3\t12.068\t3085.0\tNormalizedDNA\tC3\n1.SKB3.640195.21.C2\tWater\t384PP_AQ_BP2_HT\tE3\t12.068\t3085.0\tNormalizedDNA\tE3\n1.SKB4.640189.21.D2\tWater\t384PP_AQ_BP2_HT\tG3\t12.068\t3085.0\tNormalizedDNA\tG3\n1.SKB5.640181.21.E2\tWater\t384PP_AQ_BP2_HT\tI3\t12.068\t3085.0\tNormalizedDNA\tI3\n1.SKB6.640176.21.F2\tWater\t384PP_AQ_BP2_HT\tK3\t12.068\t3085.0\tNormalizedDNA\tK3\nvibrio.positive.control.21.G2\tWater\t384PP_AQ_BP2_HT\tM3\t6.089\t2680.0\tNormalizedDNA\tM3\nblank.21.H2\tWater\t384PP_AQ_BP2_HT\tO3\t0.342\t0.0\tNormalizedDNA\tO3\n1.SKB1.640202.21.A3\tWater\t384PP_AQ_BP2_HT\tA5\t12.068\t3085.0\tNormalizedDNA\tA5\n1.SKB2.640194.21.B3\tWater\t384PP_AQ_BP2_HT\tC5\t12.068\t3085.0\tNormalizedDNA\tC5\n1.SKB3.640195.21.C3\tWater\t384PP_AQ_BP2_HT\tE5\t12.068\t3085.0\tNormalizedDNA\tE5\n1.SKB4.640189.21.D3\tWater\t384PP_AQ_BP2_HT\tG5\t12.068\t3085.0\tNormalizedDNA\tG5\n1.SKB5.640181.21.E3\tWater\t384PP_AQ_BP2_HT\tI5\t12.068\t3085.0\tNormalizedDNA\tI5\n1.SKB6.640176.21.F3\tWater\t384PP_AQ_BP2_HT\tK5\t12.068\t3085.0\tNormalizedDNA\tK5\nvibrio.positive.control.21.G3\tWater\t384PP_AQ_BP2_HT\tM5\t6.089\t2680.0\tNormalizedDNA\tM5\nblank.21.H3\tWater\t384PP_AQ_BP2_HT\tO5\t0.342\t0.0\tNormalizedDNA\tO5\n1.SKB1.640202.21.A4\tWater\t384PP_AQ_BP2_HT\tA7\t12.068\t3085.0\tNormalizedDNA\tA7\n1.SKB2.640194.21.B4\tWater\t384PP_AQ_BP2_HT\tC7\t12.068\t3085.0\tNormalizedDNA\tC7\n1.SKB3.640195.21.C4\tWater\t384PP_AQ_BP2_HT\tE7\t12.068\t3085.0\tNormalizedDNA\tE7\n1.SKB4.640189.21.D4\tWater\t384PP_AQ_BP2_HT\tG7\t12.068\t3085.0\tNormalizedDNA\tG7\n1.SKB5.640181.21.E4\tWater\t384PP_AQ_BP2_HT\tI7\t12.068\t3085.0\tNormalizedDNA\tI7\n1.SKB6.640176.21.F4\tWater\t384PP_AQ_BP2_HT\tK7\t12.068\t3085.0\tNormalizedDNA\tK7\nvibrio.positive.control.21.G4\tWater\t384PP_AQ_BP2_HT\tM7\t6.089\t2680.0\tNormalizedDNA\tM7\nblank.21.H4\tWater\t384PP_AQ_BP2_HT\tO7\t0.342\t0.0\tNormalizedDNA\tO7\n1.SKB1.640202.21.A5\tWater\t384PP_AQ_BP2_HT\tA9\t12.068\t3085.0\tNormalizedDNA\tA9\n1.SKB2.640194.21.B5\tWater\t384PP_AQ_BP2_HT\tC9\t12.068\t3085.0\tNormalizedDNA\tC9\n1.SKB3.640195.21.C5\tWater\t384PP_AQ_BP2_HT\tE9\t12.068\t3085.0\tNormalizedDNA\tE9\n1.SKB4.640189.21.D5\tWater\t384PP_AQ_BP2_HT\tG9\t12.068\t3085.0\tNormalizedDNA\tG9\n1.SKB5.640181.21.E5\tWater\t384PP_AQ_BP2_HT\tI9\t12.068\t3085.0\tNormalizedDNA\tI9\n1.SKB6.640176.21.F5\tWater\t384PP_AQ_BP2_HT\tK9\t12.068\t3085.0\tNormalizedDNA\tK9\nvibrio.positive.control.21.G5\tWater\t384PP_AQ_BP2_HT\tM9\t6.089\t2680.0\tNormalizedDNA\tM9\nblank.21.H5\tWater\t384PP_AQ_BP2_HT\tO9\t0.342\t0.0\tNormalizedDNA\tO9\n1.SKB1.640202.21.A6\tWater\t384PP_AQ_BP2_HT\tA11\t12.068\t3085.0\tNormalizedDNA\tA11\n1.SKB2.640194.21.B6\tWater\t384PP_AQ_BP2_HT\tC11\t12.068\t3085.0\tNormalizedDNA\tC11\n1.SKB3.640195.21.C6\tWater\t384PP_AQ_BP2_HT\tE11\t12.068\t3085.0\tNormalizedDNA\tE11\n1.SKB4.640189.21.D6\tWater\t384PP_AQ_BP2_HT\tG11\t12.068\t3085.0\tNormalizedDNA\tG11\n1.SKB5.640181.21.E6\tWater\t384PP_AQ_BP2_HT\tI11\t12.068\t3085.0\tNormalizedDNA\tI11\n1.SKB6.640176.21.F6\tWater\t384PP_AQ_BP2_HT\tK11\t12.068\t3085.0\tNormalizedDNA\tK11\nvibrio.positive.control.21.G6\tWater\t384PP_AQ_BP2_HT\tM11\t6.089\t2680.0\tNormalizedDNA\tM11\nblank.21.H6\tWater\t384PP_AQ_BP2_HT\tO11\t0.342\t0.0\tNormalizedDNA\tO11\n1.SKB1.640202.21.A7\tWater\t384PP_AQ_BP2_HT\tA13\t12.068\t3085.0\tNormalizedDNA\tA13\n1.SKB2.640194.21.B7\tWater\t384PP_AQ_BP2_HT\tC13\t12.068\t3085.0\tNormalizedDNA\tC13\n1.SKB3.640195.21.C7\tWater\t384PP_AQ_BP2_HT\tE13\t12.068\t3085.0\tNormalizedDNA\tE13\n1.SKB4.640189.21.D7\tWater\t384PP_AQ_BP2_HT\tG13\t12.068\t3085.0\tNormalizedDNA\tG13\n1.SKB5.640181.21.E7\tWater\t384PP_AQ_BP2_HT\tI13\t12.068\t3085.0\tNormalizedDNA\tI13\n1.SKB6.640176.21.F7\tWater\t384PP_AQ_BP2_HT\tK13\t12.068\t3085.0\tNormalizedDNA\tK13\nvibrio.positive.control.21.G7\tWater\t384PP_AQ_BP2_HT\tM13\t6.089\t2680.0\tNormalizedDNA\tM13\nblank.21.H7\tWater\t384PP_AQ_BP2_HT\tO13\t0.342\t0.0\tNormalizedDNA\tO13\n1.SKB1.640202.21.A8\tWater\t384PP_AQ_BP2_HT\tA15\t12.068\t3085.0\tNormalizedDNA\tA15\n1.SKB2.640194.21.B8\tWater\t384PP_AQ_BP2_HT\tC15\t12.068\t3085.0\tNormalizedDNA\tC15\n1.SKB3.640195.21.C8\tWater\t384PP_AQ_BP2_HT\tE15\t12.068\t3085.0\tNormalizedDNA\tE15\n1.SKB4.640189.21.D8\tWater\t384PP_AQ_BP2_HT\tG15\t12.068\t3085.0\tNormalizedDNA\tG15\n1.SKB5.640181.21.E8\tWater\t384PP_AQ_BP2_HT\tI15\t12.068\t3085.0\tNormalizedDNA\tI15\n1.SKB6.640176.21.F8\tWater\t384PP_AQ_BP2_HT\tK15\t12.068\t3085.0\tNormalizedDNA\tK15\nvibrio.positive.control.21.G8\tWater\t384PP_AQ_BP2_HT\tM15\t6.089\t2680.0\tNormalizedDNA\tM15\nblank.21.H8\tWater\t384PP_AQ_BP2_HT\tO15\t0.342\t0.0\tNormalizedDNA\tO15\n1.SKB1.640202.21.A9\tWater\t384PP_AQ_BP2_HT\tA17\t12.068\t3085.0\tNormalizedDNA\tA17\n1.SKB2.640194.21.B9\tWater\t384PP_AQ_BP2_HT\tC17\t12.068\t3085.0\tNormalizedDNA\tC17\n1.SKB3.640195.21.C9\tWater\t384PP_AQ_BP2_HT\tE17\t12.068\t3085.0\tNormalizedDNA\tE17\n1.SKB4.640189.21.D9\tWater\t384PP_AQ_BP2_HT\tG17\t12.068\t3085.0\tNormalizedDNA\tG17\n1.SKB5.640181.21.E9\tWater\t384PP_AQ_BP2_HT\tI17\t12.068\t3085.0\tNormalizedDNA\tI17\n1.SKB6.640176.21.F9\tWater\t384PP_AQ_BP2_HT\tK17\t12.068\t3085.0\tNormalizedDNA\tK17\nvibrio.positive.control.21.G9\tWater\t384PP_AQ_BP2_HT\tM17\t6.089\t2680.0\tNormalizedDNA\tM17\nblank.21.H9\tWater\t384PP_AQ_BP2_HT\tO17\t0.342\t0.0\tNormalizedDNA\tO17\n1.SKB1.640202.21.A10\tWater\t384PP_AQ_BP2_HT\tA19\t12.068\t3085.0\tNormalizedDNA\tA19\n1.SKB2.640194.21.B10\tWater\t384PP_AQ_BP2_HT\tC19\t12.068\t3085.0\tNormalizedDNA\tC19\n1.SKB3.640195.21.C10\tWater\t384PP_AQ_BP2_HT\tE19\t12.068\t3085.0\tNormalizedDNA\tE19\n1.SKB4.640189.21.D10\tWater\t384PP_AQ_BP2_HT\tG19\t12.068\t3085.0\tNormalizedDNA\tG19\n1.SKB5.640181.21.E10\tWater\t384PP_AQ_BP2_HT\tI19\t12.068\t3085.0\tNormalizedDNA\tI19\n1.SKB6.640176.21.F10\tWater\t384PP_AQ_BP2_HT\tK19\t12.068\t3085.0\tNormalizedDNA\tK19\nvibrio.positive.control.21.G10\tWater\t384PP_AQ_BP2_HT\tM19\t6.089\t2680.0\tNormalizedDNA\tM19\nblank.21.H10\tWater\t384PP_AQ_BP2_HT\tO19\t0.342\t0.0\tNormalizedDNA\tO19\n1.SKB1.640202.21.A11\tWater\t384PP_AQ_BP2_HT\tA21\t12.068\t3085.0\tNormalizedDNA\tA21\n1.SKB2.640194.21.B11\tWater\t384PP_AQ_BP2_HT\tC21\t12.068\t3085.0\tNormalizedDNA\tC21\n1.SKB3.640195.21.C11\tWater\t384PP_AQ_BP2_HT\tE21\t12.068\t3085.0\tNormalizedDNA\tE21\n1.SKB4.640189.21.D11\tWater\t384PP_AQ_BP2_HT\tG21\t12.068\t3085.0\tNormalizedDNA\tG21\n1.SKB5.640181.21.E11\tWater\t384PP_AQ_BP2_HT\tI21\t12.068\t3085.0\tNormalizedDNA\tI21\n1.SKB6.640176.21.F11\tWater\t384PP_AQ_BP2_HT\tK21\t12.068\t3085.0\tNormalizedDNA\tK21\nvibrio.positive.control.21.G11\tWater\t384PP_AQ_BP2_HT\tM21\t6.089\t2680.0\tNormalizedDNA\tM21\nblank.21.H11\tWater\t384PP_AQ_BP2_HT\tO21\t0.342\t0.0\tNormalizedDNA\tO21\n1.SKB1.640202.21.A12\tWater\t384PP_AQ_BP2_HT\tA23\t12.068\t3085.0\tNormalizedDNA\tA23\n1.SKB2.640194.21.B12\tWater\t384PP_AQ_BP2_HT\tC23\t12.068\t3085.0\tNormalizedDNA\tC23\n1.SKB3.640195.21.C12\tWater\t384PP_AQ_BP2_HT\tE23\t12.068\t3085.0\tNormalizedDNA\tE23\n1.SKB4.640189.21.D12\tWater\t384PP_AQ_BP2_HT\tG23\t12.068\t3085.0\tNormalizedDNA\tG23\n1.SKB5.640181.21.E12\tWater\t384PP_AQ_BP2_HT\tI23\t12.068\t3085.0\tNormalizedDNA\tI23\n1.SKB6.640176.21.F12\tWater\t384PP_AQ_BP2_HT\tK23\t12.068\t3085.0\tNormalizedDNA\tK23\nvibrio.positive.control.21.G12\tWater\t384PP_AQ_BP2_HT\tM23\t6.089\t2680.0\tNormalizedDNA\tM23\n1.SKB1.640202.27.A1\tWater\t384PP_AQ_BP2_HT\tA2\t12.068\t3085.0\tNormalizedDNA\tA2\n1.SKB2.640194.27.B1\tWater\t384PP_AQ_BP2_HT\tC2\t12.068\t3085.0\tNormalizedDNA\tC2\n1.SKB3.640195.27.C1\tWater\t384PP_AQ_BP2_HT\tE2\t12.068\t3085.0\tNormalizedDNA\tE2\n1.SKB4.640189.27.D1\tWater\t384PP_AQ_BP2_HT\tG2\t12.068\t3085.0\tNormalizedDNA\tG2\n1.SKB5.640181.27.E1\tWater\t384PP_AQ_BP2_HT\tI2\t12.068\t3085.0\tNormalizedDNA\tI2\n1.SKB6.640176.27.F1\tWater\t384PP_AQ_BP2_HT\tK2\t12.068\t3085.0\tNormalizedDNA\tK2\nvibrio.positive.control.27.G1\tWater\t384PP_AQ_BP2_HT\tM2\t6.089\t2680.0\tNormalizedDNA\tM2\nblank.27.H1\tWater\t384PP_AQ_BP2_HT\tO2\t0.342\t0.0\tNormalizedDNA\tO2\n1.SKB1.640202.27.A2\tWater\t384PP_AQ_BP2_HT\tA4\t12.068\t3085.0\tNormalizedDNA\tA4\n1.SKB2.640194.27.B2\tWater\t384PP_AQ_BP2_HT\tC4\t12.068\t3085.0\tNormalizedDNA\tC4\n1.SKB3.640195.27.C2\tWater\t384PP_AQ_BP2_HT\tE4\t12.068\t3085.0\tNormalizedDNA\tE4\n1.SKB4.640189.27.D2\tWater\t384PP_AQ_BP2_HT\tG4\t12.068\t3085.0\tNormalizedDNA\tG4\n1.SKB5.640181.27.E2\tWater\t384PP_AQ_BP2_HT\tI4\t12.068\t3085.0\tNormalizedDNA\tI4\n1.SKB6.640176.27.F2\tWater\t384PP_AQ_BP2_HT\tK4\t12.068\t3085.0\tNormalizedDNA\tK4\nvibrio.positive.control.27.G2\tWater\t384PP_AQ_BP2_HT\tM4\t6.089\t2680.0\tNormalizedDNA\tM4\nblank.27.H2\tWater\t384PP_AQ_BP2_HT\tO4\t0.342\t0.0\tNormalizedDNA\tO4\n1.SKB1.640202.27.A3\tWater\t384PP_AQ_BP2_HT\tA6\t12.068\t3085.0\tNormalizedDNA\tA6\n1.SKB2.640194.27.B3\tWater\t384PP_AQ_BP2_HT\tC6\t12.068\t3085.0\tNormalizedDNA\tC6\n1.SKB3.640195.27.C3\tWater\t384PP_AQ_BP2_HT\tE6\t12.068\t3085.0\tNormalizedDNA\tE6\n1.SKB4.640189.27.D3\tWater\t384PP_AQ_BP2_HT\tG6\t12.068\t3085.0\tNormalizedDNA\tG6\n1.SKB5.640181.27.E3\tWater\t384PP_AQ_BP2_HT\tI6\t12.068\t3085.0\tNormalizedDNA\tI6\n1.SKB6.640176.27.F3\tWater\t384PP_AQ_BP2_HT\tK6\t12.068\t3085.0\tNormalizedDNA\tK6\nvibrio.positive.control.27.G3\tWater\t384PP_AQ_BP2_HT\tM6\t6.089\t2680.0\tNormalizedDNA\tM6\nblank.27.H3\tWater\t384PP_AQ_BP2_HT\tO6\t0.342\t0.0\tNormalizedDNA\tO6\n1.SKB1.640202.27.A4\tWater\t384PP_AQ_BP2_HT\tA8\t12.068\t3085.0\tNormalizedDNA\tA8\n1.SKB2.640194.27.B4\tWater\t384PP_AQ_BP2_HT\tC8\t12.068\t3085.0\tNormalizedDNA\tC8\n1.SKB3.640195.27.C4\tWater\t384PP_AQ_BP2_HT\tE8\t12.068\t3085.0\tNormalizedDNA\tE8\n1.SKB4.640189.27.D4\tWater\t384PP_AQ_BP2_HT\tG8\t12.068\t3085.0\tNormalizedDNA\tG8\n1.SKB5.640181.27.E4\tWater\t384PP_AQ_BP2_HT\tI8\t12.068\t3085.0\tNormalizedDNA\tI8\n1.SKB6.640176.27.F4\tWater\t384PP_AQ_BP2_HT\tK8\t12.068\t3085.0\tNormalizedDNA\tK8\nvibrio.positive.control.27.G4\tWater\t384PP_AQ_BP2_HT\tM8\t6.089\t2680.0\tNormalizedDNA\tM8\nblank.27.H4\tWater\t384PP_AQ_BP2_HT\tO8\t0.342\t0.0\tNormalizedDNA\tO8\n1.SKB1.640202.27.A5\tWater\t384PP_AQ_BP2_HT\tA10\t12.068\t3085.0\tNormalizedDNA\tA10\n1.SKB2.640194.27.B5\tWater\t384PP_AQ_BP2_HT\tC10\t12.068\t3085.0\tNormalizedDNA\tC10\n1.SKB3.640195.27.C5\tWater\t384PP_AQ_BP2_HT\tE10\t12.068\t3085.0\tNormalizedDNA\tE10\n1.SKB4.640189.27.D5\tWater\t384PP_AQ_BP2_HT\tG10\t12.068\t3085.0\tNormalizedDNA\tG10\n1.SKB5.640181.27.E5\tWater\t384PP_AQ_BP2_HT\tI10\t12.068\t3085.0\tNormalizedDNA\tI10\n1.SKB6.640176.27.F5\tWater\t384PP_AQ_BP2_HT\tK10\t12.068\t3085.0\tNormalizedDNA\tK10\nvibrio.positive.control.27.G5\tWater\t384PP_AQ_BP2_HT\tM10\t6.089\t2680.0\tNormalizedDNA\tM10\nblank.27.H5\tWater\t384PP_AQ_BP2_HT\tO10\t0.342\t0.0\tNormalizedDNA\tO10\n1.SKB1.640202.27.A6\tWater\t384PP_AQ_BP2_HT\tA12\t12.068\t3085.0\tNormalizedDNA\tA12\n1.SKB2.640194.27.B6\tWater\t384PP_AQ_BP2_HT\tC12\t12.068\t3085.0\tNormalizedDNA\tC12\n1.SKB3.640195.27.C6\tWater\t384PP_AQ_BP2_HT\tE12\t12.068\t3085.0\tNormalizedDNA\tE12\n1.SKB4.640189.27.D6\tWater\t384PP_AQ_BP2_HT\tG12\t12.068\t3085.0\tNormalizedDNA\tG12\n1.SKB5.640181.27.E6\tWater\t384PP_AQ_BP2_HT\tI12\t12.068\t3085.0\tNormalizedDNA\tI12\n1.SKB6.640176.27.F6\tWater\t384PP_AQ_BP2_HT\tK12\t12.068\t3085.0\tNormalizedDNA\tK12\nvibrio.positive.control.27.G6\tWater\t384PP_AQ_BP2_HT\tM12\t6.089\t2680.0\tNormalizedDNA\tM12\nblank.27.H6\tWater\t384PP_AQ_BP2_HT\tO12\t0.342\t0.0\tNormalizedDNA\tO12\n1.SKB1.640202.27.A7\tWater\t384PP_AQ_BP2_HT\tA14\t12.068\t3085.0\tNormalizedDNA\tA14\n1.SKB2.640194.27.B7\tWater\t384PP_AQ_BP2_HT\tC14\t12.068\t3085.0\tNormalizedDNA\tC14\n1.SKB3.640195.27.C7\tWater\t384PP_AQ_BP2_HT\tE14\t12.068\t3085.0\tNormalizedDNA\tE14\n1.SKB4.640189.27.D7\tWater\t384PP_AQ_BP2_HT\tG14\t12.068\t3085.0\tNormalizedDNA\tG14\n1.SKB5.640181.27.E7\tWater\t384PP_AQ_BP2_HT\tI14\t12.068\t3085.0\tNormalizedDNA\tI14\n1.SKB6.640176.27.F7\tWater\t384PP_AQ_BP2_HT\tK14\t12.068\t3085.0\tNormalizedDNA\tK14\nvibrio.positive.control.27.G7\tWater\t384PP_AQ_BP2_HT\tM14\t6.089\t2680.0\tNormalizedDNA\tM14\nblank.27.H7\tWater\t384PP_AQ_BP2_HT\tO14\t0.342\t0.0\tNormalizedDNA\tO14\n1.SKB1.640202.27.A8\tWater\t384PP_AQ_BP2_HT\tA16\t12.068\t3085.0\tNormalizedDNA\tA16\n1.SKB2.640194.27.B8\tWater\t384PP_AQ_BP2_HT\tC16\t12.068\t3085.0\tNormalizedDNA\tC16\n1.SKB3.640195.27.C8\tWater\t384PP_AQ_BP2_HT\tE16\t12.068\t3085.0\tNormalizedDNA\tE16\n1.SKB4.640189.27.D8\tWater\t384PP_AQ_BP2_HT\tG16\t12.068\t3085.0\tNormalizedDNA\tG16\n1.SKB5.640181.27.E8\tWater\t384PP_AQ_BP2_HT\tI16\t12.068\t3085.0\tNormalizedDNA\tI16\n1.SKB6.640176.27.F8\tWater\t384PP_AQ_BP2_HT\tK16\t12.068\t3085.0\tNormalizedDNA\tK16\nvibrio.positive.control.27.G8\tWater\t384PP_AQ_BP2_HT\tM16\t6.089\t2680.0\tNormalizedDNA\tM16\nblank.27.H8\tWater\t384PP_AQ_BP2_HT\tO16\t0.342\t0.0\tNormalizedDNA\tO16\n1.SKB1.640202.27.A9\tWater\t384PP_AQ_BP2_HT\tA18\t12.068\t3085.0\tNormalizedDNA\tA18\n1.SKB2.640194.27.B9\tWater\t384PP_AQ_BP2_HT\tC18\t12.068\t3085.0\tNormalizedDNA\tC18\n1.SKB3.640195.27.C9\tWater\t384PP_AQ_BP2_HT\tE18\t12.068\t3085.0\tNormalizedDNA\tE18\n1.SKB4.640189.27.D9\tWater\t384PP_AQ_BP2_HT\tG18\t12.068\t3085.0\tNormalizedDNA\tG18\n1.SKB5.640181.27.E9\tWater\t384PP_AQ_BP2_HT\tI18\t12.068\t3085.0\tNormalizedDNA\tI18\n1.SKB6.640176.27.F9\tWater\t384PP_AQ_BP2_HT\tK18\t12.068\t3085.0\tNormalizedDNA\tK18\nvibrio.positive.control.27.G9\tWater\t384PP_AQ_BP2_HT\tM18\t6.089\t2680.0\tNormalizedDNA\tM18\nblank.27.H9\tWater\t384PP_AQ_BP2_HT\tO18\t0.342\t0.0\tNormalizedDNA\tO18\n1.SKB1.640202.27.A10\tWater\t384PP_AQ_BP2_HT\tA20\t12.068\t3085.0\tNormalizedDNA\tA20\n1.SKB2.640194.27.B10\tWater\t384PP_AQ_BP2_HT\tC20\t12.068\t3085.0\tNormalizedDNA\tC20\n1.SKB3.640195.27.C10\tWater\t384PP_AQ_BP2_HT\tE20\t12.068\t3085.0\tNormalizedDNA\tE20\n1.SKB4.640189.27.D10\tWater\t384PP_AQ_BP2_HT\tG20\t12.068\t3085.0\tNormalizedDNA\tG20\n1.SKB5.640181.27.E10\tWater\t384PP_AQ_BP2_HT\tI20\t12.068\t3085.0\tNormalizedDNA\tI20\n1.SKB6.640176.27.F10\tWater\t384PP_AQ_BP2_HT\tK20\t12.068\t3085.0\tNormalizedDNA\tK20\nvibrio.positive.control.27.G10\tWater\t384PP_AQ_BP2_HT\tM20\t6.089\t2680.0\tNormalizedDNA\tM20\nblank.27.H10\tWater\t384PP_AQ_BP2_HT\tO20\t0.342\t0.0\tNormalizedDNA\tO20\n1.SKB1.640202.27.A11\tWater\t384PP_AQ_BP2_HT\tA22\t12.068\t3085.0\tNormalizedDNA\tA22\n1.SKB2.640194.27.B11\tWater\t384PP_AQ_BP2_HT\tC22\t12.068\t3085.0\tNormalizedDNA\tC22\n1.SKB3.640195.27.C11\tWater\t384PP_AQ_BP2_HT\tE22\t12.068\t3085.0\tNormalizedDNA\tE22\n1.SKB4.640189.27.D11\tWater\t384PP_AQ_BP2_HT\tG22\t12.068\t3085.0\tNormalizedDNA\tG22\n1.SKB5.640181.27.E11\tWater\t384PP_AQ_BP2_HT\tI22\t12.068\t3085.0\tNormalizedDNA\tI22\n1.SKB6.640176.27.F11\tWater\t384PP_AQ_BP2_HT\tK22\t12.068\t3085.0\tNormalizedDNA\tK22\nvibrio.positive.control.27.G11\tWater\t384PP_AQ_BP2_HT\tM22\t6.089\t2680.0\tNormalizedDNA\tM22\nblank.27.H11\tWater\t384PP_AQ_BP2_HT\tO22\t0.342\t0.0\tNormalizedDNA\tO22\n1.SKB1.640202.27.A12\tWater\t384PP_AQ_BP2_HT\tA24\t12.068\t3085.0\tNormalizedDNA\tA24\n1.SKB2.640194.27.B12\tWater\t384PP_AQ_BP2_HT\tC24\t12.068\t3085.0\tNormalizedDNA\tC24\n1.SKB3.640195.27.C12\tWater\t384PP_AQ_BP2_HT\tE24\t12.068\t3085.0\tNormalizedDNA\tE24\n1.SKB4.640189.27.D12\tWater\t384PP_AQ_BP2_HT\tG24\t12.068\t3085.0\tNormalizedDNA\tG24\n1.SKB5.640181.27.E12\tWater\t384PP_AQ_BP2_HT\tI24\t12.068\t3085.0\tNormalizedDNA\tI24\n1.SKB6.640176.27.F12\tWater\t384PP_AQ_BP2_HT\tK24\t12.068\t3085.0\tNormalizedDNA\tK24\nvibrio.positive.control.27.G12\tWater\t384PP_AQ_BP2_HT\tM24\t6.089\t2680.0\tNormalizedDNA\tM24\n1.SKB1.640202.30.A1\tWater\t384PP_AQ_BP2_HT\tB1\t12.068\t3085.0\tNormalizedDNA\tB1\n1.SKB2.640194.30.B1\tWater\t384PP_AQ_BP2_HT\tD1\t12.068\t3085.0\tNormalizedDNA\tD1\n1.SKB3.640195.30.C1\tWater\t384PP_AQ_BP2_HT\tF1\t12.068\t3085.0\tNormalizedDNA\tF1\n1.SKB4.640189.30.D1\tWater\t384PP_AQ_BP2_HT\tH1\t12.068\t3085.0\tNormalizedDNA\tH1\n1.SKB5.640181.30.E1\tWater\t384PP_AQ_BP2_HT\tJ1\t12.068\t3085.0\tNormalizedDNA\tJ1\n1.SKB6.640176.30.F1\tWater\t384PP_AQ_BP2_HT\tL1\t12.068\t3085.0\tNormalizedDNA\tL1\nvibrio.positive.control.30.G1\tWater\t384PP_AQ_BP2_HT\tN1\t6.089\t2680.0\tNormalizedDNA\tN1\nblank.30.H1\tWater\t384PP_AQ_BP2_HT\tP1\t0.342\t0.0\tNormalizedDNA\tP1\n1.SKB1.640202.30.A2\tWater\t384PP_AQ_BP2_HT\tB3\t12.068\t3085.0\tNormalizedDNA\tB3\n1.SKB2.640194.30.B2\tWater\t384PP_AQ_BP2_HT\tD3\t12.068\t3085.0\tNormalizedDNA\tD3\n1.SKB3.640195.30.C2\tWater\t384PP_AQ_BP2_HT\tF3\t12.068\t3085.0\tNormalizedDNA\tF3\n1.SKB4.640189.30.D2\tWater\t384PP_AQ_BP2_HT\tH3\t12.068\t3085.0\tNormalizedDNA\tH3\n1.SKB5.640181.30.E2\tWater\t384PP_AQ_BP2_HT\tJ3\t12.068\t3085.0\tNormalizedDNA\tJ3\n1.SKB6.640176.30.F2\tWater\t384PP_AQ_BP2_HT\tL3\t12.068\t3085.0\tNormalizedDNA\tL3\nvibrio.positive.control.30.G2\tWater\t384PP_AQ_BP2_HT\tN3\t6.089\t2680.0\tNormalizedDNA\tN3\nblank.30.H2\tWater\t384PP_AQ_BP2_HT\tP3\t0.342\t0.0\tNormalizedDNA\tP3\n1.SKB1.640202.30.A3\tWater\t384PP_AQ_BP2_HT\tB5\t12.068\t3085.0\tNormalizedDNA\tB5\n1.SKB2.640194.30.B3\tWater\t384PP_AQ_BP2_HT\tD5\t12.068\t3085.0\tNormalizedDNA\tD5\n1.SKB3.640195.30.C3\tWater\t384PP_AQ_BP2_HT\tF5\t12.068\t3085.0\tNormalizedDNA\tF5\n1.SKB4.640189.30.D3\tWater\t384PP_AQ_BP2_HT\tH5\t12.068\t3085.0\tNormalizedDNA\tH5\n1.SKB5.640181.30.E3\tWater\t384PP_AQ_BP2_HT\tJ5\t12.068\t3085.0\tNormalizedDNA\tJ5\n1.SKB6.640176.30.F3\tWater\t384PP_AQ_BP2_HT\tL5\t12.068\t3085.0\tNormalizedDNA\tL5\nvibrio.positive.control.30.G3\tWater\t384PP_AQ_BP2_HT\tN5\t6.089\t2680.0\tNormalizedDNA\tN5\nblank.30.H3\tWater\t384PP_AQ_BP2_HT\tP5\t0.342\t0.0\tNormalizedDNA\tP5\n1.SKB1.640202.30.A4\tWater\t384PP_AQ_BP2_HT\tB7\t12.068\t3085.0\tNormalizedDNA\tB7\n1.SKB2.640194.30.B4\tWater\t384PP_AQ_BP2_HT\tD7\t12.068\t3085.0\tNormalizedDNA\tD7\n1.SKB3.640195.30.C4\tWater\t384PP_AQ_BP2_HT\tF7\t12.068\t3085.0\tNormalizedDNA\tF7\n1.SKB4.640189.30.D4\tWater\t384PP_AQ_BP2_HT\tH7\t12.068\t3085.0\tNormalizedDNA\tH7\n1.SKB5.640181.30.E4\tWater\t384PP_AQ_BP2_HT\tJ7\t12.068\t3085.0\tNormalizedDNA\tJ7\n1.SKB6.640176.30.F4\tWater\t384PP_AQ_BP2_HT\tL7\t12.068\t3085.0\tNormalizedDNA\tL7\nvibrio.positive.control.30.G4\tWater\t384PP_AQ_BP2_HT\tN7\t6.089\t2680.0\tNormalizedDNA\tN7\nblank.30.H4\tWater\t384PP_AQ_BP2_HT\tP7\t0.342\t0.0\tNormalizedDNA\tP7\n1.SKB1.640202.30.A5\tWater\t384PP_AQ_BP2_HT\tB9\t12.068\t3085.0\tNormalizedDNA\tB9\n1.SKB2.640194.30.B5\tWater\t384PP_AQ_BP2_HT\tD9\t12.068\t3085.0\tNormalizedDNA\tD9\n1.SKB3.640195.30.C5\tWater\t384PP_AQ_BP2_HT\tF9\t12.068\t3085.0\tNormalizedDNA\tF9\n1.SKB4.640189.30.D5\tWater\t384PP_AQ_BP2_HT\tH9\t12.068\t3085.0\tNormalizedDNA\tH9\n1.SKB5.640181.30.E5\tWater\t384PP_AQ_BP2_HT\tJ9\t12.068\t3085.0\tNormalizedDNA\tJ9\n1.SKB6.640176.30.F5\tWater\t384PP_AQ_BP2_HT\tL9\t12.068\t3085.0\tNormalizedDNA\tL9\nvibrio.positive.control.30.G5\tWater\t384PP_AQ_BP2_HT\tN9\t6.089\t2680.0\tNormalizedDNA\tN9\nblank.30.H5\tWater\t384PP_AQ_BP2_HT\tP9\t0.342\t0.0\tNormalizedDNA\tP9\n1.SKB1.640202.30.A6\tWater\t384PP_AQ_BP2_HT\tB11\t12.068\t3085.0\tNormalizedDNA\tB11\n1.SKB2.640194.30.B6\tWater\t384PP_AQ_BP2_HT\tD11\t12.068\t3085.0\tNormalizedDNA\tD11\n1.SKB3.640195.30.C6\tWater\t384PP_AQ_BP2_HT\tF11\t12.068\t3085.0\tNormalizedDNA\tF11\n1.SKB4.640189.30.D6\tWater\t384PP_AQ_BP2_HT\tH11\t12.068\t3085.0\tNormalizedDNA\tH11\n1.SKB5.640181.30.E6\tWater\t384PP_AQ_BP2_HT\tJ11\t12.068\t3085.0\tNormalizedDNA\tJ11\n1.SKB6.640176.30.F6\tWater\t384PP_AQ_BP2_HT\tL11\t12.068\t3085.0\tNormalizedDNA\tL11\nvibrio.positive.control.30.G6\tWater\t384PP_AQ_BP2_HT\tN11\t6.089\t2680.0\tNormalizedDNA\tN11\nblank.30.H6\tWater\t384PP_AQ_BP2_HT\tP11\t0.342\t0.0\tNormalizedDNA\tP11\n1.SKB1.640202.30.A7\tWater\t384PP_AQ_BP2_HT\tB13\t12.068\t3085.0\tNormalizedDNA\tB13\n1.SKB2.640194.30.B7\tWater\t384PP_AQ_BP2_HT\tD13\t12.068\t3085.0\tNormalizedDNA\tD13\n1.SKB3.640195.30.C7\tWater\t384PP_AQ_BP2_HT\tF13\t12.068\t3085.0\tNormalizedDNA\tF13\n1.SKB4.640189.30.D7\tWater\t384PP_AQ_BP2_HT\tH13\t12.068\t3085.0\tNormalizedDNA\tH13\n1.SKB5.640181.30.E7\tWater\t384PP_AQ_BP2_HT\tJ13\t12.068\t3085.0\tNormalizedDNA\tJ13\n1.SKB6.640176.30.F7\tWater\t384PP_AQ_BP2_HT\tL13\t12.068\t3085.0\tNormalizedDNA\tL13\nvibrio.positive.control.30.G7\tWater\t384PP_AQ_BP2_HT\tN13\t6.089\t2680.0\tNormalizedDNA\tN13\nblank.30.H7\tWater\t384PP_AQ_BP2_HT\tP13\t0.342\t0.0\tNormalizedDNA\tP13\n1.SKB1.640202.30.A8\tWater\t384PP_AQ_BP2_HT\tB15\t12.068\t3085.0\tNormalizedDNA\tB15\n1.SKB2.640194.30.B8\tWater\t384PP_AQ_BP2_HT\tD15\t12.068\t3085.0\tNormalizedDNA\tD15\n1.SKB3.640195.30.C8\tWater\t384PP_AQ_BP2_HT\tF15\t12.068\t3085.0\tNormalizedDNA\tF15\n1.SKB4.640189.30.D8\tWater\t384PP_AQ_BP2_HT\tH15\t12.068\t3085.0\tNormalizedDNA\tH15\n1.SKB5.640181.30.E8\tWater\t384PP_AQ_BP2_HT\tJ15\t12.068\t3085.0\tNormalizedDNA\tJ15\n1.SKB6.640176.30.F8\tWater\t384PP_AQ_BP2_HT\tL15\t12.068\t3085.0\tNormalizedDNA\tL15\nvibrio.positive.control.30.G8\tWater\t384PP_AQ_BP2_HT\tN15\t6.089\t2680.0\tNormalizedDNA\tN15\nblank.30.H8\tWater\t384PP_AQ_BP2_HT\tP15\t0.342\t0.0\tNormalizedDNA\tP15\n1.SKB1.640202.30.A9\tWater\t384PP_AQ_BP2_HT\tB17\t12.068\t3085.0\tNormalizedDNA\tB17\n1.SKB2.640194.30.B9\tWater\t384PP_AQ_BP2_HT\tD17\t12.068\t3085.0\tNormalizedDNA\tD17\n1.SKB3.640195.30.C9\tWater\t384PP_AQ_BP2_HT\tF17\t12.068\t3085.0\tNormalizedDNA\tF17\n1.SKB4.640189.30.D9\tWater\t384PP_AQ_BP2_HT\tH17\t12.068\t3085.0\tNormalizedDNA\tH17\n1.SKB5.640181.30.E9\tWater\t384PP_AQ_BP2_HT\tJ17\t12.068\t3085.0\tNormalizedDNA\tJ17\n1.SKB6.640176.30.F9\tWater\t384PP_AQ_BP2_HT\tL17\t12.068\t3085.0\tNormalizedDNA\tL17\nvibrio.positive.control.30.G9\tWater\t384PP_AQ_BP2_HT\tN17\t6.089\t2680.0\tNormalizedDNA\tN17\nblank.30.H9\tWater\t384PP_AQ_BP2_HT\tP17\t0.342\t0.0\tNormalizedDNA\tP17\n1.SKB1.640202.30.A10\tWater\t384PP_AQ_BP2_HT\tB19\t12.068\t3085.0\tNormalizedDNA\tB19\n1.SKB2.640194.30.B10\tWater\t384PP_AQ_BP2_HT\tD19\t12.068\t3085.0\tNormalizedDNA\tD19\n1.SKB3.640195.30.C10\tWater\t384PP_AQ_BP2_HT\tF19\t12.068\t3085.0\tNormalizedDNA\tF19\n1.SKB4.640189.30.D10\tWater\t384PP_AQ_BP2_HT\tH19\t12.068\t3085.0\tNormalizedDNA\tH19\n1.SKB5.640181.30.E10\tWater\t384PP_AQ_BP2_HT\tJ19\t12.068\t3085.0\tNormalizedDNA\tJ19\n1.SKB6.640176.30.F10\tWater\t384PP_AQ_BP2_HT\tL19\t12.068\t3085.0\tNormalizedDNA\tL19\nvibrio.positive.control.30.G10\tWater\t384PP_AQ_BP2_HT\tN19\t6.089\t2680.0\tNormalizedDNA\tN19\nblank.30.H10\tWater\t384PP_AQ_BP2_HT\tP19\t0.342\t0.0\tNormalizedDNA\tP19\n1.SKB1.640202.30.A11\tWater\t384PP_AQ_BP2_HT\tB21\t12.068\t3085.0\tNormalizedDNA\tB21\n1.SKB2.640194.30.B11\tWater\t384PP_AQ_BP2_HT\tD21\t12.068\t3085.0\tNormalizedDNA\tD21\n1.SKB3.640195.30.C11\tWater\t384PP_AQ_BP2_HT\tF21\t12.068\t3085.0\tNormalizedDNA\tF21\n1.SKB4.640189.30.D11\tWater\t384PP_AQ_BP2_HT\tH21\t12.068\t3085.0\tNormalizedDNA\tH21\n1.SKB5.640181.30.E11\tWater\t384PP_AQ_BP2_HT\tJ21\t12.068\t3085.0\tNormalizedDNA\tJ21\n1.SKB6.640176.30.F11\tWater\t384PP_AQ_BP2_HT\tL21\t12.068\t3085.0\tNormalizedDNA\tL21\nvibrio.positive.control.30.G11\tWater\t384PP_AQ_BP2_HT\tN21\t6.089\t2680.0\tNormalizedDNA\tN21\nblank.30.H11\tWater\t384PP_AQ_BP2_HT\tP21\t0.342\t0.0\tNormalizedDNA\tP21\n1.SKB1.640202.30.A12\tWater\t384PP_AQ_BP2_HT\tB23\t12.068\t3085.0\tNormalizedDNA\tB23\n1.SKB2.640194.30.B12\tWater\t384PP_AQ_BP2_HT\tD23\t12.068\t3085.0\tNormalizedDNA\tD23\n1.SKB3.640195.30.C12\tWater\t384PP_AQ_BP2_HT\tF23\t12.068\t3085.0\tNormalizedDNA\tF23\n1.SKB4.640189.30.D12\tWater\t384PP_AQ_BP2_HT\tH23\t12.068\t3085.0\tNormalizedDNA\tH23\n1.SKB5.640181.30.E12\tWater\t384PP_AQ_BP2_HT\tJ23\t12.068\t3085.0\tNormalizedDNA\tJ23\n1.SKB6.640176.30.F12\tWater\t384PP_AQ_BP2_HT\tL23\t12.068\t3085.0\tNormalizedDNA\tL23\nvibrio.positive.control.30.G12\tWater\t384PP_AQ_BP2_HT\tN23\t6.089\t2680.0\tNormalizedDNA\tN23\n1.SKB1.640202.33.A1\tWater\t384PP_AQ_BP2_HT\tB2\t12.068\t3085.0\tNormalizedDNA\tB2\n1.SKB2.640194.33.B1\tWater\t384PP_AQ_BP2_HT\tD2\t12.068\t3085.0\tNormalizedDNA\tD2\n1.SKB3.640195.33.C1\tWater\t384PP_AQ_BP2_HT\tF2\t12.068\t3085.0\tNormalizedDNA\tF2\n1.SKB4.640189.33.D1\tWater\t384PP_AQ_BP2_HT\tH2\t12.068\t3085.0\tNormalizedDNA\tH2\n1.SKB5.640181.33.E1\tWater\t384PP_AQ_BP2_HT\tJ2\t12.068\t3085.0\tNormalizedDNA\tJ2\n1.SKB6.640176.33.F1\tWater\t384PP_AQ_BP2_HT\tL2\t12.068\t3085.0\tNormalizedDNA\tL2\nvibrio.positive.control.33.G1\tWater\t384PP_AQ_BP2_HT\tN2\t6.089\t2680.0\tNormalizedDNA\tN2\nblank.33.H1\tWater\t384PP_AQ_BP2_HT\tP2\t0.342\t0.0\tNormalizedDNA\tP2\n1.SKB1.640202.33.A2\tWater\t384PP_AQ_BP2_HT\tB4\t12.068\t3085.0\tNormalizedDNA\tB4\n1.SKB2.640194.33.B2\tWater\t384PP_AQ_BP2_HT\tD4\t12.068\t3085.0\tNormalizedDNA\tD4\n1.SKB3.640195.33.C2\tWater\t384PP_AQ_BP2_HT\tF4\t12.068\t3085.0\tNormalizedDNA\tF4\n1.SKB4.640189.33.D2\tWater\t384PP_AQ_BP2_HT\tH4\t12.068\t3085.0\tNormalizedDNA\tH4\n1.SKB5.640181.33.E2\tWater\t384PP_AQ_BP2_HT\tJ4\t12.068\t3085.0\tNormalizedDNA\tJ4\n1.SKB6.640176.33.F2\tWater\t384PP_AQ_BP2_HT\tL4\t12.068\t3085.0\tNormalizedDNA\tL4\nvibrio.positive.control.33.G2\tWater\t384PP_AQ_BP2_HT\tN4\t6.089\t2680.0\tNormalizedDNA\tN4\nblank.33.H2\tWater\t384PP_AQ_BP2_HT\tP4\t0.342\t0.0\tNormalizedDNA\tP4\n1.SKB1.640202.33.A3\tWater\t384PP_AQ_BP2_HT\tB6\t12.068\t3085.0\tNormalizedDNA\tB6\n1.SKB2.640194.33.B3\tWater\t384PP_AQ_BP2_HT\tD6\t12.068\t3085.0\tNormalizedDNA\tD6\n1.SKB3.640195.33.C3\tWater\t384PP_AQ_BP2_HT\tF6\t12.068\t3085.0\tNormalizedDNA\tF6\n1.SKB4.640189.33.D3\tWater\t384PP_AQ_BP2_HT\tH6\t12.068\t3085.0\tNormalizedDNA\tH6\n1.SKB5.640181.33.E3\tWater\t384PP_AQ_BP2_HT\tJ6\t12.068\t3085.0\tNormalizedDNA\tJ6\n1.SKB6.640176.33.F3\tWater\t384PP_AQ_BP2_HT\tL6\t12.068\t3085.0\tNormalizedDNA\tL6\nvibrio.positive.control.33.G3\tWater\t384PP_AQ_BP2_HT\tN6\t6.089\t2680.0\tNormalizedDNA\tN6\nblank.33.H3\tWater\t384PP_AQ_BP2_HT\tP6\t0.342\t0.0\tNormalizedDNA\tP6\n1.SKB1.640202.33.A4\tWater\t384PP_AQ_BP2_HT\tB8\t12.068\t3085.0\tNormalizedDNA\tB8\n1.SKB2.640194.33.B4\tWater\t384PP_AQ_BP2_HT\tD8\t12.068\t3085.0\tNormalizedDNA\tD8\n1.SKB3.640195.33.C4\tWater\t384PP_AQ_BP2_HT\tF8\t12.068\t3085.0\tNormalizedDNA\tF8\n1.SKB4.640189.33.D4\tWater\t384PP_AQ_BP2_HT\tH8\t12.068\t3085.0\tNormalizedDNA\tH8\n1.SKB5.640181.33.E4\tWater\t384PP_AQ_BP2_HT\tJ8\t12.068\t3085.0\tNormalizedDNA\tJ8\n1.SKB6.640176.33.F4\tWater\t384PP_AQ_BP2_HT\tL8\t12.068\t3085.0\tNormalizedDNA\tL8\nvibrio.positive.control.33.G4\tWater\t384PP_AQ_BP2_HT\tN8\t6.089\t2680.0\tNormalizedDNA\tN8\nblank.33.H4\tWater\t384PP_AQ_BP2_HT\tP8\t0.342\t0.0\tNormalizedDNA\tP8\n1.SKB1.640202.33.A5\tWater\t384PP_AQ_BP2_HT\tB10\t12.068\t3085.0\tNormalizedDNA\tB10\n1.SKB2.640194.33.B5\tWater\t384PP_AQ_BP2_HT\tD10\t12.068\t3085.0\tNormalizedDNA\tD10\n1.SKB3.640195.33.C5\tWater\t384PP_AQ_BP2_HT\tF10\t12.068\t3085.0\tNormalizedDNA\tF10\n1.SKB4.640189.33.D5\tWater\t384PP_AQ_BP2_HT\tH10\t12.068\t3085.0\tNormalizedDNA\tH10\n1.SKB5.640181.33.E5\tWater\t384PP_AQ_BP2_HT\tJ10\t12.068\t3085.0\tNormalizedDNA\tJ10\n1.SKB6.640176.33.F5\tWater\t384PP_AQ_BP2_HT\tL10\t12.068\t3085.0\tNormalizedDNA\tL10\nvibrio.positive.control.33.G5\tWater\t384PP_AQ_BP2_HT\tN10\t6.089\t2680.0\tNormalizedDNA\tN10\nblank.33.H5\tWater\t384PP_AQ_BP2_HT\tP10\t0.342\t0.0\tNormalizedDNA\tP10\n1.SKB1.640202.33.A6\tWater\t384PP_AQ_BP2_HT\tB12\t12.068\t3085.0\tNormalizedDNA\tB12\n1.SKB2.640194.33.B6\tWater\t384PP_AQ_BP2_HT\tD12\t12.068\t3085.0\tNormalizedDNA\tD12\n1.SKB3.640195.33.C6\tWater\t384PP_AQ_BP2_HT\tF12\t12.068\t3085.0\tNormalizedDNA\tF12\n1.SKB4.640189.33.D6\tWater\t384PP_AQ_BP2_HT\tH12\t12.068\t3085.0\tNormalizedDNA\tH12\n1.SKB5.640181.33.E6\tWater\t384PP_AQ_BP2_HT\tJ12\t12.068\t3085.0\tNormalizedDNA\tJ12\n1.SKB6.640176.33.F6\tWater\t384PP_AQ_BP2_HT\tL12\t12.068\t3085.0\tNormalizedDNA\tL12\nvibrio.positive.control.33.G6\tWater\t384PP_AQ_BP2_HT\tN12\t6.089\t2680.0\tNormalizedDNA\tN12\nblank.33.H6\tWater\t384PP_AQ_BP2_HT\tP12\t0.342\t0.0\tNormalizedDNA\tP12\n1.SKB1.640202.33.A7\tWater\t384PP_AQ_BP2_HT\tB14\t12.068\t3085.0\tNormalizedDNA\tB14\n1.SKB2.640194.33.B7\tWater\t384PP_AQ_BP2_HT\tD14\t12.068\t3085.0\tNormalizedDNA\tD14\n1.SKB3.640195.33.C7\tWater\t384PP_AQ_BP2_HT\tF14\t12.068\t3085.0\tNormalizedDNA\tF14\n1.SKB4.640189.33.D7\tWater\t384PP_AQ_BP2_HT\tH14\t12.068\t3085.0\tNormalizedDNA\tH14\n1.SKB5.640181.33.E7\tWater\t384PP_AQ_BP2_HT\tJ14\t12.068\t3085.0\tNormalizedDNA\tJ14\n1.SKB6.640176.33.F7\tWater\t384PP_AQ_BP2_HT\tL14\t12.068\t3085.0\tNormalizedDNA\tL14\nvibrio.positive.control.33.G7\tWater\t384PP_AQ_BP2_HT\tN14\t6.089\t2680.0\tNormalizedDNA\tN14\nblank.33.H7\tWater\t384PP_AQ_BP2_HT\tP14\t0.342\t0.0\tNormalizedDNA\tP14\n1.SKB1.640202.33.A8\tWater\t384PP_AQ_BP2_HT\tB16\t12.068\t3085.0\tNormalizedDNA\tB16\n1.SKB2.640194.33.B8\tWater\t384PP_AQ_BP2_HT\tD16\t12.068\t3085.0\tNormalizedDNA\tD16\n1.SKB3.640195.33.C8\tWater\t384PP_AQ_BP2_HT\tF16\t12.068\t3085.0\tNormalizedDNA\tF16\n1.SKB4.640189.33.D8\tWater\t384PP_AQ_BP2_HT\tH16\t12.068\t3085.0\tNormalizedDNA\tH16\n1.SKB5.640181.33.E8\tWater\t384PP_AQ_BP2_HT\tJ16\t12.068\t3085.0\tNormalizedDNA\tJ16\n1.SKB6.640176.33.F8\tWater\t384PP_AQ_BP2_HT\tL16\t12.068\t3085.0\tNormalizedDNA\tL16\nvibrio.positive.control.33.G8\tWater\t384PP_AQ_BP2_HT\tN16\t6.089\t2680.0\tNormalizedDNA\tN16\nblank.33.H8\tWater\t384PP_AQ_BP2_HT\tP16\t0.342\t0.0\tNormalizedDNA\tP16\n1.SKB1.640202.33.A9\tWater\t384PP_AQ_BP2_HT\tB18\t12.068\t3085.0\tNormalizedDNA\tB18\n1.SKB2.640194.33.B9\tWater\t384PP_AQ_BP2_HT\tD18\t12.068\t3085.0\tNormalizedDNA\tD18\n1.SKB3.640195.33.C9\tWater\t384PP_AQ_BP2_HT\tF18\t12.068\t3085.0\tNormalizedDNA\tF18\n1.SKB4.640189.33.D9\tWater\t384PP_AQ_BP2_HT\tH18\t12.068\t3085.0\tNormalizedDNA\tH18\n1.SKB5.640181.33.E9\tWater\t384PP_AQ_BP2_HT\tJ18\t12.068\t3085.0\tNormalizedDNA\tJ18\n1.SKB6.640176.33.F9\tWater\t384PP_AQ_BP2_HT\tL18\t12.068\t3085.0\tNormalizedDNA\tL18\nvibrio.positive.control.33.G9\tWater\t384PP_AQ_BP2_HT\tN18\t6.089\t2680.0\tNormalizedDNA\tN18\nblank.33.H9\tWater\t384PP_AQ_BP2_HT\tP18\t0.342\t0.0\tNormalizedDNA\tP18\n1.SKB1.640202.33.A10\tWater\t384PP_AQ_BP2_HT\tB20\t12.068\t3085.0\tNormalizedDNA\tB20\n1.SKB2.640194.33.B10\tWater\t384PP_AQ_BP2_HT\tD20\t12.068\t3085.0\tNormalizedDNA\tD20\n1.SKB3.640195.33.C10\tWater\t384PP_AQ_BP2_HT\tF20\t12.068\t3085.0\tNormalizedDNA\tF20\n1.SKB4.640189.33.D10\tWater\t384PP_AQ_BP2_HT\tH20\t12.068\t3085.0\tNormalizedDNA\tH20\n1.SKB5.640181.33.E10\tWater\t384PP_AQ_BP2_HT\tJ20\t12.068\t3085.0\tNormalizedDNA\tJ20\n1.SKB6.640176.33.F10\tWater\t384PP_AQ_BP2_HT\tL20\t12.068\t3085.0\tNormalizedDNA\tL20\nvibrio.positive.control.33.G10\tWater\t384PP_AQ_BP2_HT\tN20\t6.089\t2680.0\tNormalizedDNA\tN20\nblank.33.H10\tWater\t384PP_AQ_BP2_HT\tP20\t0.342\t0.0\tNormalizedDNA\tP20\n1.SKB1.640202.33.A11\tWater\t384PP_AQ_BP2_HT\tB22\t12.068\t3085.0\tNormalizedDNA\tB22\n1.SKB2.640194.33.B11\tWater\t384PP_AQ_BP2_HT\tD22\t12.068\t3085.0\tNormalizedDNA\tD22\n1.SKB3.640195.33.C11\tWater\t384PP_AQ_BP2_HT\tF22\t12.068\t3085.0\tNormalizedDNA\tF22\n1.SKB4.640189.33.D11\tWater\t384PP_AQ_BP2_HT\tH22\t12.068\t3085.0\tNormalizedDNA\tH22\n1.SKB5.640181.33.E11\tWater\t384PP_AQ_BP2_HT\tJ22\t12.068\t3085.0\tNormalizedDNA\tJ22\n1.SKB6.640176.33.F11\tWater\t384PP_AQ_BP2_HT\tL22\t12.068\t3085.0\tNormalizedDNA\tL22\nvibrio.positive.control.33.G11\tWater\t384PP_AQ_BP2_HT\tN22\t6.089\t2680.0\tNormalizedDNA\tN22\nblank.33.H11\tWater\t384PP_AQ_BP2_HT\tP22\t0.342\t0.0\tNormalizedDNA\tP22\n1.SKB1.640202.33.A12\tWater\t384PP_AQ_BP2_HT\tB24\t12.068\t3085.0\tNormalizedDNA\tB24\n1.SKB2.640194.33.B12\tWater\t384PP_AQ_BP2_HT\tD24\t12.068\t3085.0\tNormalizedDNA\tD24\n1.SKB3.640195.33.C12\tWater\t384PP_AQ_BP2_HT\tF24\t12.068\t3085.0\tNormalizedDNA\tF24\n1.SKB4.640189.33.D12\tWater\t384PP_AQ_BP2_HT\tH24\t12.068\t3085.0\tNormalizedDNA\tH24\n1.SKB5.640181.33.E12\tWater\t384PP_AQ_BP2_HT\tJ24\t12.068\t3085.0\tNormalizedDNA\tJ24\n1.SKB6.640176.33.F12\tWater\t384PP_AQ_BP2_HT\tL24\t12.068\t3085.0\tNormalizedDNA\tL24\nvibrio.positive.control.33.G12\tWater\t384PP_AQ_BP2_HT\tN24\t6.089\t2680.0\tNormalizedDNA\tN24\n1.SKB1.640202.21.A1\tSample\t384PP_AQ_BP2_HT\tA1\t12.068\t415.0\tNormalizedDNA\tA1\n1.SKB2.640194.21.B1\tSample\t384PP_AQ_BP2_HT\tC1\t12.068\t415.0\tNormalizedDNA\tC1\n1.SKB3.640195.21.C1\tSample\t384PP_AQ_BP2_HT\tE1\t12.068\t415.0\tNormalizedDNA\tE1\n1.SKB4.640189.21.D1\tSample\t384PP_AQ_BP2_HT\tG1\t12.068\t415.0\tNormalizedDNA\tG1\n1.SKB5.640181.21.E1\tSample\t384PP_AQ_BP2_HT\tI1\t12.068\t415.0\tNormalizedDNA\tI1\n1.SKB6.640176.21.F1\tSample\t384PP_AQ_BP2_HT\tK1\t12.068\t415.0\tNormalizedDNA\tK1\nvibrio.positive.control.21.G1\tSample\t384PP_AQ_BP2_HT\tM1\t6.089\t820.0\tNormalizedDNA\tM1\nblank.21.H1\tSample\t384PP_AQ_BP2_HT\tO1\t0.342\t3500.0\tNormalizedDNA\tO1\n1.SKB1.640202.21.A2\tSample\t384PP_AQ_BP2_HT\tA3\t12.068\t415.0\tNormalizedDNA\tA3\n1.SKB2.640194.21.B2\tSample\t384PP_AQ_BP2_HT\tC3\t12.068\t415.0\tNormalizedDNA\tC3\n1.SKB3.640195.21.C2\tSample\t384PP_AQ_BP2_HT\tE3\t12.068\t415.0\tNormalizedDNA\tE3\n1.SKB4.640189.21.D2\tSample\t384PP_AQ_BP2_HT\tG3\t12.068\t415.0\tNormalizedDNA\tG3\n1.SKB5.640181.21.E2\tSample\t384PP_AQ_BP2_HT\tI3\t12.068\t415.0\tNormalizedDNA\tI3\n1.SKB6.640176.21.F2\tSample\t384PP_AQ_BP2_HT\tK3\t12.068\t415.0\tNormalizedDNA\tK3\nvibrio.positive.control.21.G2\tSample\t384PP_AQ_BP2_HT\tM3\t6.089\t820.0\tNormalizedDNA\tM3\nblank.21.H2\tSample\t384PP_AQ_BP2_HT\tO3\t0.342\t3500.0\tNormalizedDNA\tO3\n1.SKB1.640202.21.A3\tSample\t384PP_AQ_BP2_HT\tA5\t12.068\t415.0\tNormalizedDNA\tA5\n1.SKB2.640194.21.B3\tSample\t384PP_AQ_BP2_HT\tC5\t12.068\t415.0\tNormalizedDNA\tC5\n1.SKB3.640195.21.C3\tSample\t384PP_AQ_BP2_HT\tE5\t12.068\t415.0\tNormalizedDNA\tE5\n1.SKB4.640189.21.D3\tSample\t384PP_AQ_BP2_HT\tG5\t12.068\t415.0\tNormalizedDNA\tG5\n1.SKB5.640181.21.E3\tSample\t384PP_AQ_BP2_HT\tI5\t12.068\t415.0\tNormalizedDNA\tI5\n1.SKB6.640176.21.F3\tSample\t384PP_AQ_BP2_HT\tK5\t12.068\t415.0\tNormalizedDNA\tK5\nvibrio.positive.control.21.G3\tSample\t384PP_AQ_BP2_HT\tM5\t6.089\t820.0\tNormalizedDNA\tM5\nblank.21.H3\tSample\t384PP_AQ_BP2_HT\tO5\t0.342\t3500.0\tNormalizedDNA\tO5\n1.SKB1.640202.21.A4\tSample\t384PP_AQ_BP2_HT\tA7\t12.068\t415.0\tNormalizedDNA\tA7\n1.SKB2.640194.21.B4\tSample\t384PP_AQ_BP2_HT\tC7\t12.068\t415.0\tNormalizedDNA\tC7\n1.SKB3.640195.21.C4\tSample\t384PP_AQ_BP2_HT\tE7\t12.068\t415.0\tNormalizedDNA\tE7\n1.SKB4.640189.21.D4\tSample\t384PP_AQ_BP2_HT\tG7\t12.068\t415.0\tNormalizedDNA\tG7\n1.SKB5.640181.21.E4\tSample\t384PP_AQ_BP2_HT\tI7\t12.068\t415.0\tNormalizedDNA\tI7\n1.SKB6.640176.21.F4\tSample\t384PP_AQ_BP2_HT\tK7\t12.068\t415.0\tNormalizedDNA\tK7\nvibrio.positive.control.21.G4\tSample\t384PP_AQ_BP2_HT\tM7\t6.089\t820.0\tNormalizedDNA\tM7\nblank.21.H4\tSample\t384PP_AQ_BP2_HT\tO7\t0.342\t3500.0\tNormalizedDNA\tO7\n1.SKB1.640202.21.A5\tSample\t384PP_AQ_BP2_HT\tA9\t12.068\t415.0\tNormalizedDNA\tA9\n1.SKB2.640194.21.B5\tSample\t384PP_AQ_BP2_HT\tC9\t12.068\t415.0\tNormalizedDNA\tC9\n1.SKB3.640195.21.C5\tSample\t384PP_AQ_BP2_HT\tE9\t12.068\t415.0\tNormalizedDNA\tE9\n1.SKB4.640189.21.D5\tSample\t384PP_AQ_BP2_HT\tG9\t12.068\t415.0\tNormalizedDNA\tG9\n1.SKB5.640181.21.E5\tSample\t384PP_AQ_BP2_HT\tI9\t12.068\t415.0\tNormalizedDNA\tI9\n1.SKB6.640176.21.F5\tSample\t384PP_AQ_BP2_HT\tK9\t12.068\t415.0\tNormalizedDNA\tK9\nvibrio.positive.control.21.G5\tSample\t384PP_AQ_BP2_HT\tM9\t6.089\t820.0\tNormalizedDNA\tM9\nblank.21.H5\tSample\t384PP_AQ_BP2_HT\tO9\t0.342\t3500.0\tNormalizedDNA\tO9\n1.SKB1.640202.21.A6\tSample\t384PP_AQ_BP2_HT\tA11\t12.068\t415.0\tNormalizedDNA\tA11\n1.SKB2.640194.21.B6\tSample\t384PP_AQ_BP2_HT\tC11\t12.068\t415.0\tNormalizedDNA\tC11\n1.SKB3.640195.21.C6\tSample\t384PP_AQ_BP2_HT\tE11\t12.068\t415.0\tNormalizedDNA\tE11\n1.SKB4.640189.21.D6\tSample\t384PP_AQ_BP2_HT\tG11\t12.068\t415.0\tNormalizedDNA\tG11\n1.SKB5.640181.21.E6\tSample\t384PP_AQ_BP2_HT\tI11\t12.068\t415.0\tNormalizedDNA\tI11\n1.SKB6.640176.21.F6\tSample\t384PP_AQ_BP2_HT\tK11\t12.068\t415.0\tNormalizedDNA\tK11\nvibrio.positive.control.21.G6\tSample\t384PP_AQ_BP2_HT\tM11\t6.089\t820.0\tNormalizedDNA\tM11\nblank.21.H6\tSample\t384PP_AQ_BP2_HT\tO11\t0.342\t3500.0\tNormalizedDNA\tO11\n1.SKB1.640202.21.A7\tSample\t384PP_AQ_BP2_HT\tA13\t12.068\t415.0\tNormalizedDNA\tA13\n1.SKB2.640194.21.B7\tSample\t384PP_AQ_BP2_HT\tC13\t12.068\t415.0\tNormalizedDNA\tC13\n1.SKB3.640195.21.C7\tSample\t384PP_AQ_BP2_HT\tE13\t12.068\t415.0\tNormalizedDNA\tE13\n1.SKB4.640189.21.D7\tSample\t384PP_AQ_BP2_HT\tG13\t12.068\t415.0\tNormalizedDNA\tG13\n1.SKB5.640181.21.E7\tSample\t384PP_AQ_BP2_HT\tI13\t12.068\t415.0\tNormalizedDNA\tI13\n1.SKB6.640176.21.F7\tSample\t384PP_AQ_BP2_HT\tK13\t12.068\t415.0\tNormalizedDNA\tK13\nvibrio.positive.control.21.G7\tSample\t384PP_AQ_BP2_HT\tM13\t6.089\t820.0\tNormalizedDNA\tM13\nblank.21.H7\tSample\t384PP_AQ_BP2_HT\tO13\t0.342\t3500.0\tNormalizedDNA\tO13\n1.SKB1.640202.21.A8\tSample\t384PP_AQ_BP2_HT\tA15\t12.068\t415.0\tNormalizedDNA\tA15\n1.SKB2.640194.21.B8\tSample\t384PP_AQ_BP2_HT\tC15\t12.068\t415.0\tNormalizedDNA\tC15\n1.SKB3.640195.21.C8\tSample\t384PP_AQ_BP2_HT\tE15\t12.068\t415.0\tNormalizedDNA\tE15\n1.SKB4.640189.21.D8\tSample\t384PP_AQ_BP2_HT\tG15\t12.068\t415.0\tNormalizedDNA\tG15\n1.SKB5.640181.21.E8\tSample\t384PP_AQ_BP2_HT\tI15\t12.068\t415.0\tNormalizedDNA\tI15\n1.SKB6.640176.21.F8\tSample\t384PP_AQ_BP2_HT\tK15\t12.068\t415.0\tNormalizedDNA\tK15\nvibrio.positive.control.21.G8\tSample\t384PP_AQ_BP2_HT\tM15\t6.089\t820.0\tNormalizedDNA\tM15\nblank.21.H8\tSample\t384PP_AQ_BP2_HT\tO15\t0.342\t3500.0\tNormalizedDNA\tO15\n1.SKB1.640202.21.A9\tSample\t384PP_AQ_BP2_HT\tA17\t12.068\t415.0\tNormalizedDNA\tA17\n1.SKB2.640194.21.B9\tSample\t384PP_AQ_BP2_HT\tC17\t12.068\t415.0\tNormalizedDNA\tC17\n1.SKB3.640195.21.C9\tSample\t384PP_AQ_BP2_HT\tE17\t12.068\t415.0\tNormalizedDNA\tE17\n1.SKB4.640189.21.D9\tSample\t384PP_AQ_BP2_HT\tG17\t12.068\t415.0\tNormalizedDNA\tG17\n1.SKB5.640181.21.E9\tSample\t384PP_AQ_BP2_HT\tI17\t12.068\t415.0\tNormalizedDNA\tI17\n1.SKB6.640176.21.F9\tSample\t384PP_AQ_BP2_HT\tK17\t12.068\t415.0\tNormalizedDNA\tK17\nvibrio.positive.control.21.G9\tSample\t384PP_AQ_BP2_HT\tM17\t6.089\t820.0\tNormalizedDNA\tM17\nblank.21.H9\tSample\t384PP_AQ_BP2_HT\tO17\t0.342\t3500.0\tNormalizedDNA\tO17\n1.SKB1.640202.21.A10\tSample\t384PP_AQ_BP2_HT\tA19\t12.068\t415.0\tNormalizedDNA\tA19\n1.SKB2.640194.21.B10\tSample\t384PP_AQ_BP2_HT\tC19\t12.068\t415.0\tNormalizedDNA\tC19\n1.SKB3.640195.21.C10\tSample\t384PP_AQ_BP2_HT\tE19\t12.068\t415.0\tNormalizedDNA\tE19\n1.SKB4.640189.21.D10\tSample\t384PP_AQ_BP2_HT\tG19\t12.068\t415.0\tNormalizedDNA\tG19\n1.SKB5.640181.21.E10\tSample\t384PP_AQ_BP2_HT\tI19\t12.068\t415.0\tNormalizedDNA\tI19\n1.SKB6.640176.21.F10\tSample\t384PP_AQ_BP2_HT\tK19\t12.068\t415.0\tNormalizedDNA\tK19\nvibrio.positive.control.21.G10\tSample\t384PP_AQ_BP2_HT\tM19\t6.089\t820.0\tNormalizedDNA\tM19\nblank.21.H10\tSample\t384PP_AQ_BP2_HT\tO19\t0.342\t3500.0\tNormalizedDNA\tO19\n1.SKB1.640202.21.A11\tSample\t384PP_AQ_BP2_HT\tA21\t12.068\t415.0\tNormalizedDNA\tA21\n1.SKB2.640194.21.B11\tSample\t384PP_AQ_BP2_HT\tC21\t12.068\t415.0\tNormalizedDNA\tC21\n1.SKB3.640195.21.C11\tSample\t384PP_AQ_BP2_HT\tE21\t12.068\t415.0\tNormalizedDNA\tE21\n1.SKB4.640189.21.D11\tSample\t384PP_AQ_BP2_HT\tG21\t12.068\t415.0\tNormalizedDNA\tG21\n1.SKB5.640181.21.E11\tSample\t384PP_AQ_BP2_HT\tI21\t12.068\t415.0\tNormalizedDNA\tI21\n1.SKB6.640176.21.F11\tSample\t384PP_AQ_BP2_HT\tK21\t12.068\t415.0\tNormalizedDNA\tK21\nvibrio.positive.control.21.G11\tSample\t384PP_AQ_BP2_HT\tM21\t6.089\t820.0\tNormalizedDNA\tM21\nblank.21.H11\tSample\t384PP_AQ_BP2_HT\tO21\t0.342\t3500.0\tNormalizedDNA\tO21\n1.SKB1.640202.21.A12\tSample\t384PP_AQ_BP2_HT\tA23\t12.068\t415.0\tNormalizedDNA\tA23\n1.SKB2.640194.21.B12\tSample\t384PP_AQ_BP2_HT\tC23\t12.068\t415.0\tNormalizedDNA\tC23\n1.SKB3.640195.21.C12\tSample\t384PP_AQ_BP2_HT\tE23\t12.068\t415.0\tNormalizedDNA\tE23\n1.SKB4.640189.21.D12\tSample\t384PP_AQ_BP2_HT\tG23\t12.068\t415.0\tNormalizedDNA\tG23\n1.SKB5.640181.21.E12\tSample\t384PP_AQ_BP2_HT\tI23\t12.068\t415.0\tNormalizedDNA\tI23\n1.SKB6.640176.21.F12\tSample\t384PP_AQ_BP2_HT\tK23\t12.068\t415.0\tNormalizedDNA\tK23\nvibrio.positive.control.21.G12\tSample\t384PP_AQ_BP2_HT\tM23\t6.089\t820.0\tNormalizedDNA\tM23\n1.SKB1.640202.27.A1\tSample\t384PP_AQ_BP2_HT\tA2\t12.068\t415.0\tNormalizedDNA\tA2\n1.SKB2.640194.27.B1\tSample\t384PP_AQ_BP2_HT\tC2\t12.068\t415.0\tNormalizedDNA\tC2\n1.SKB3.640195.27.C1\tSample\t384PP_AQ_BP2_HT\tE2\t12.068\t415.0\tNormalizedDNA\tE2\n1.SKB4.640189.27.D1\tSample\t384PP_AQ_BP2_HT\tG2\t12.068\t415.0\tNormalizedDNA\tG2\n1.SKB5.640181.27.E1\tSample\t384PP_AQ_BP2_HT\tI2\t12.068\t415.0\tNormalizedDNA\tI2\n1.SKB6.640176.27.F1\tSample\t384PP_AQ_BP2_HT\tK2\t12.068\t415.0\tNormalizedDNA\tK2\nvibrio.positive.control.27.G1\tSample\t384PP_AQ_BP2_HT\tM2\t6.089\t820.0\tNormalizedDNA\tM2\nblank.27.H1\tSample\t384PP_AQ_BP2_HT\tO2\t0.342\t3500.0\tNormalizedDNA\tO2\n1.SKB1.640202.27.A2\tSample\t384PP_AQ_BP2_HT\tA4\t12.068\t415.0\tNormalizedDNA\tA4\n1.SKB2.640194.27.B2\tSample\t384PP_AQ_BP2_HT\tC4\t12.068\t415.0\tNormalizedDNA\tC4\n1.SKB3.640195.27.C2\tSample\t384PP_AQ_BP2_HT\tE4\t12.068\t415.0\tNormalizedDNA\tE4\n1.SKB4.640189.27.D2\tSample\t384PP_AQ_BP2_HT\tG4\t12.068\t415.0\tNormalizedDNA\tG4\n1.SKB5.640181.27.E2\tSample\t384PP_AQ_BP2_HT\tI4\t12.068\t415.0\tNormalizedDNA\tI4\n1.SKB6.640176.27.F2\tSample\t384PP_AQ_BP2_HT\tK4\t12.068\t415.0\tNormalizedDNA\tK4\nvibrio.positive.control.27.G2\tSample\t384PP_AQ_BP2_HT\tM4\t6.089\t820.0\tNormalizedDNA\tM4\nblank.27.H2\tSample\t384PP_AQ_BP2_HT\tO4\t0.342\t3500.0\tNormalizedDNA\tO4\n1.SKB1.640202.27.A3\tSample\t384PP_AQ_BP2_HT\tA6\t12.068\t415.0\tNormalizedDNA\tA6\n1.SKB2.640194.27.B3\tSample\t384PP_AQ_BP2_HT\tC6\t12.068\t415.0\tNormalizedDNA\tC6\n1.SKB3.640195.27.C3\tSample\t384PP_AQ_BP2_HT\tE6\t12.068\t415.0\tNormalizedDNA\tE6\n1.SKB4.640189.27.D3\tSample\t384PP_AQ_BP2_HT\tG6\t12.068\t415.0\tNormalizedDNA\tG6\n1.SKB5.640181.27.E3\tSample\t384PP_AQ_BP2_HT\tI6\t12.068\t415.0\tNormalizedDNA\tI6\n1.SKB6.640176.27.F3\tSample\t384PP_AQ_BP2_HT\tK6\t12.068\t415.0\tNormalizedDNA\tK6\nvibrio.positive.control.27.G3\tSample\t384PP_AQ_BP2_HT\tM6\t6.089\t820.0\tNormalizedDNA\tM6\nblank.27.H3\tSample\t384PP_AQ_BP2_HT\tO6\t0.342\t3500.0\tNormalizedDNA\tO6\n1.SKB1.640202.27.A4\tSample\t384PP_AQ_BP2_HT\tA8\t12.068\t415.0\tNormalizedDNA\tA8\n1.SKB2.640194.27.B4\tSample\t384PP_AQ_BP2_HT\tC8\t12.068\t415.0\tNormalizedDNA\tC8\n1.SKB3.640195.27.C4\tSample\t384PP_AQ_BP2_HT\tE8\t12.068\t415.0\tNormalizedDNA\tE8\n1.SKB4.640189.27.D4\tSample\t384PP_AQ_BP2_HT\tG8\t12.068\t415.0\tNormalizedDNA\tG8\n1.SKB5.640181.27.E4\tSample\t384PP_AQ_BP2_HT\tI8\t12.068\t415.0\tNormalizedDNA\tI8\n1.SKB6.640176.27.F4\tSample\t384PP_AQ_BP2_HT\tK8\t12.068\t415.0\tNormalizedDNA\tK8\nvibrio.positive.control.27.G4\tSample\t384PP_AQ_BP2_HT\tM8\t6.089\t820.0\tNormalizedDNA\tM8\nblank.27.H4\tSample\t384PP_AQ_BP2_HT\tO8\t0.342\t3500.0\tNormalizedDNA\tO8\n1.SKB1.640202.27.A5\tSample\t384PP_AQ_BP2_HT\tA10\t12.068\t415.0\tNormalizedDNA\tA10\n1.SKB2.640194.27.B5\tSample\t384PP_AQ_BP2_HT\tC10\t12.068\t415.0\tNormalizedDNA\tC10\n1.SKB3.640195.27.C5\tSample\t384PP_AQ_BP2_HT\tE10\t12.068\t415.0\tNormalizedDNA\tE10\n1.SKB4.640189.27.D5\tSample\t384PP_AQ_BP2_HT\tG10\t12.068\t415.0\tNormalizedDNA\tG10\n1.SKB5.640181.27.E5\tSample\t384PP_AQ_BP2_HT\tI10\t12.068\t415.0\tNormalizedDNA\tI10\n1.SKB6.640176.27.F5\tSample\t384PP_AQ_BP2_HT\tK10\t12.068\t415.0\tNormalizedDNA\tK10\nvibrio.positive.control.27.G5\tSample\t384PP_AQ_BP2_HT\tM10\t6.089\t820.0\tNormalizedDNA\tM10\nblank.27.H5\tSample\t384PP_AQ_BP2_HT\tO10\t0.342\t3500.0\tNormalizedDNA\tO10\n1.SKB1.640202.27.A6\tSample\t384PP_AQ_BP2_HT\tA12\t12.068\t415.0\tNormalizedDNA\tA12\n1.SKB2.640194.27.B6\tSample\t384PP_AQ_BP2_HT\tC12\t12.068\t415.0\tNormalizedDNA\tC12\n1.SKB3.640195.27.C6\tSample\t384PP_AQ_BP2_HT\tE12\t12.068\t415.0\tNormalizedDNA\tE12\n1.SKB4.640189.27.D6\tSample\t384PP_AQ_BP2_HT\tG12\t12.068\t415.0\tNormalizedDNA\tG12\n1.SKB5.640181.27.E6\tSample\t384PP_AQ_BP2_HT\tI12\t12.068\t415.0\tNormalizedDNA\tI12\n1.SKB6.640176.27.F6\tSample\t384PP_AQ_BP2_HT\tK12\t12.068\t415.0\tNormalizedDNA\tK12\nvibrio.positive.control.27.G6\tSample\t384PP_AQ_BP2_HT\tM12\t6.089\t820.0\tNormalizedDNA\tM12\nblank.27.H6\tSample\t384PP_AQ_BP2_HT\tO12\t0.342\t3500.0\tNormalizedDNA\tO12\n1.SKB1.640202.27.A7\tSample\t384PP_AQ_BP2_HT\tA14\t12.068\t415.0\tNormalizedDNA\tA14\n1.SKB2.640194.27.B7\tSample\t384PP_AQ_BP2_HT\tC14\t12.068\t415.0\tNormalizedDNA\tC14\n1.SKB3.640195.27.C7\tSample\t384PP_AQ_BP2_HT\tE14\t12.068\t415.0\tNormalizedDNA\tE14\n1.SKB4.640189.27.D7\tSample\t384PP_AQ_BP2_HT\tG14\t12.068\t415.0\tNormalizedDNA\tG14\n1.SKB5.640181.27.E7\tSample\t384PP_AQ_BP2_HT\tI14\t12.068\t415.0\tNormalizedDNA\tI14\n1.SKB6.640176.27.F7\tSample\t384PP_AQ_BP2_HT\tK14\t12.068\t415.0\tNormalizedDNA\tK14\nvibrio.positive.control.27.G7\tSample\t384PP_AQ_BP2_HT\tM14\t6.089\t820.0\tNormalizedDNA\tM14\nblank.27.H7\tSample\t384PP_AQ_BP2_HT\tO14\t0.342\t3500.0\tNormalizedDNA\tO14\n1.SKB1.640202.27.A8\tSample\t384PP_AQ_BP2_HT\tA16\t12.068\t415.0\tNormalizedDNA\tA16\n1.SKB2.640194.27.B8\tSample\t384PP_AQ_BP2_HT\tC16\t12.068\t415.0\tNormalizedDNA\tC16\n1.SKB3.640195.27.C8\tSample\t384PP_AQ_BP2_HT\tE16\t12.068\t415.0\tNormalizedDNA\tE16\n1.SKB4.640189.27.D8\tSample\t384PP_AQ_BP2_HT\tG16\t12.068\t415.0\tNormalizedDNA\tG16\n1.SKB5.640181.27.E8\tSample\t384PP_AQ_BP2_HT\tI16\t12.068\t415.0\tNormalizedDNA\tI16\n1.SKB6.640176.27.F8\tSample\t384PP_AQ_BP2_HT\tK16\t12.068\t415.0\tNormalizedDNA\tK16\nvibrio.positive.control.27.G8\tSample\t384PP_AQ_BP2_HT\tM16\t6.089\t820.0\tNormalizedDNA\tM16\nblank.27.H8\tSample\t384PP_AQ_BP2_HT\tO16\t0.342\t3500.0\tNormalizedDNA\tO16\n1.SKB1.640202.27.A9\tSample\t384PP_AQ_BP2_HT\tA18\t12.068\t415.0\tNormalizedDNA\tA18\n1.SKB2.640194.27.B9\tSample\t384PP_AQ_BP2_HT\tC18\t12.068\t415.0\tNormalizedDNA\tC18\n1.SKB3.640195.27.C9\tSample\t384PP_AQ_BP2_HT\tE18\t12.068\t415.0\tNormalizedDNA\tE18\n1.SKB4.640189.27.D9\tSample\t384PP_AQ_BP2_HT\tG18\t12.068\t415.0\tNormalizedDNA\tG18\n1.SKB5.640181.27.E9\tSample\t384PP_AQ_BP2_HT\tI18\t12.068\t415.0\tNormalizedDNA\tI18\n1.SKB6.640176.27.F9\tSample\t384PP_AQ_BP2_HT\tK18\t12.068\t415.0\tNormalizedDNA\tK18\nvibrio.positive.control.27.G9\tSample\t384PP_AQ_BP2_HT\tM18\t6.089\t820.0\tNormalizedDNA\tM18\nblank.27.H9\tSample\t384PP_AQ_BP2_HT\tO18\t0.342\t3500.0\tNormalizedDNA\tO18\n1.SKB1.640202.27.A10\tSample\t384PP_AQ_BP2_HT\tA20\t12.068\t415.0\tNormalizedDNA\tA20\n1.SKB2.640194.27.B10\tSample\t384PP_AQ_BP2_HT\tC20\t12.068\t415.0\tNormalizedDNA\tC20\n1.SKB3.640195.27.C10\tSample\t384PP_AQ_BP2_HT\tE20\t12.068\t415.0\tNormalizedDNA\tE20\n1.SKB4.640189.27.D10\tSample\t384PP_AQ_BP2_HT\tG20\t12.068\t415.0\tNormalizedDNA\tG20\n1.SKB5.640181.27.E10\tSample\t384PP_AQ_BP2_HT\tI20\t12.068\t415.0\tNormalizedDNA\tI20\n1.SKB6.640176.27.F10\tSample\t384PP_AQ_BP2_HT\tK20\t12.068\t415.0\tNormalizedDNA\tK20\nvibrio.positive.control.27.G10\tSample\t384PP_AQ_BP2_HT\tM20\t6.089\t820.0\tNormalizedDNA\tM20\nblank.27.H10\tSample\t384PP_AQ_BP2_HT\tO20\t0.342\t3500.0\tNormalizedDNA\tO20\n1.SKB1.640202.27.A11\tSample\t384PP_AQ_BP2_HT\tA22\t12.068\t415.0\tNormalizedDNA\tA22\n1.SKB2.640194.27.B11\tSample\t384PP_AQ_BP2_HT\tC22\t12.068\t415.0\tNormalizedDNA\tC22\n1.SKB3.640195.27.C11\tSample\t384PP_AQ_BP2_HT\tE22\t12.068\t415.0\tNormalizedDNA\tE22\n1.SKB4.640189.27.D11\tSample\t384PP_AQ_BP2_HT\tG22\t12.068\t415.0\tNormalizedDNA\tG22\n1.SKB5.640181.27.E11\tSample\t384PP_AQ_BP2_HT\tI22\t12.068\t415.0\tNormalizedDNA\tI22\n1.SKB6.640176.27.F11\tSample\t384PP_AQ_BP2_HT\tK22\t12.068\t415.0\tNormalizedDNA\tK22\nvibrio.positive.control.27.G11\tSample\t384PP_AQ_BP2_HT\tM22\t6.089\t820.0\tNormalizedDNA\tM22\nblank.27.H11\tSample\t384PP_AQ_BP2_HT\tO22\t0.342\t3500.0\tNormalizedDNA\tO22\n1.SKB1.640202.27.A12\tSample\t384PP_AQ_BP2_HT\tA24\t12.068\t415.0\tNormalizedDNA\tA24\n1.SKB2.640194.27.B12\tSample\t384PP_AQ_BP2_HT\tC24\t12.068\t415.0\tNormalizedDNA\tC24\n1.SKB3.640195.27.C12\tSample\t384PP_AQ_BP2_HT\tE24\t12.068\t415.0\tNormalizedDNA\tE24\n1.SKB4.640189.27.D12\tSample\t384PP_AQ_BP2_HT\tG24\t12.068\t415.0\tNormalizedDNA\tG24\n1.SKB5.640181.27.E12\tSample\t384PP_AQ_BP2_HT\tI24\t12.068\t415.0\tNormalizedDNA\tI24\n1.SKB6.640176.27.F12\tSample\t384PP_AQ_BP2_HT\tK24\t12.068\t415.0\tNormalizedDNA\tK24\nvibrio.positive.control.27.G12\tSample\t384PP_AQ_BP2_HT\tM24\t6.089\t820.0\tNormalizedDNA\tM24\n1.SKB1.640202.30.A1\tSample\t384PP_AQ_BP2_HT\tB1\t12.068\t415.0\tNormalizedDNA\tB1\n1.SKB2.640194.30.B1\tSample\t384PP_AQ_BP2_HT\tD1\t12.068\t415.0\tNormalizedDNA\tD1\n1.SKB3.640195.30.C1\tSample\t384PP_AQ_BP2_HT\tF1\t12.068\t415.0\tNormalizedDNA\tF1\n1.SKB4.640189.30.D1\tSample\t384PP_AQ_BP2_HT\tH1\t12.068\t415.0\tNormalizedDNA\tH1\n1.SKB5.640181.30.E1\tSample\t384PP_AQ_BP2_HT\tJ1\t12.068\t415.0\tNormalizedDNA\tJ1\n1.SKB6.640176.30.F1\tSample\t384PP_AQ_BP2_HT\tL1\t12.068\t415.0\tNormalizedDNA\tL1\nvibrio.positive.control.30.G1\tSample\t384PP_AQ_BP2_HT\tN1\t6.089\t820.0\tNormalizedDNA\tN1\nblank.30.H1\tSample\t384PP_AQ_BP2_HT\tP1\t0.342\t3500.0\tNormalizedDNA\tP1\n1.SKB1.640202.30.A2\tSample\t384PP_AQ_BP2_HT\tB3\t12.068\t415.0\tNormalizedDNA\tB3\n1.SKB2.640194.30.B2\tSample\t384PP_AQ_BP2_HT\tD3\t12.068\t415.0\tNormalizedDNA\tD3\n1.SKB3.640195.30.C2\tSample\t384PP_AQ_BP2_HT\tF3\t12.068\t415.0\tNormalizedDNA\tF3\n1.SKB4.640189.30.D2\tSample\t384PP_AQ_BP2_HT\tH3\t12.068\t415.0\tNormalizedDNA\tH3\n1.SKB5.640181.30.E2\tSample\t384PP_AQ_BP2_HT\tJ3\t12.068\t415.0\tNormalizedDNA\tJ3\n1.SKB6.640176.30.F2\tSample\t384PP_AQ_BP2_HT\tL3\t12.068\t415.0\tNormalizedDNA\tL3\nvibrio.positive.control.30.G2\tSample\t384PP_AQ_BP2_HT\tN3\t6.089\t820.0\tNormalizedDNA\tN3\nblank.30.H2\tSample\t384PP_AQ_BP2_HT\tP3\t0.342\t3500.0\tNormalizedDNA\tP3\n1.SKB1.640202.30.A3\tSample\t384PP_AQ_BP2_HT\tB5\t12.068\t415.0\tNormalizedDNA\tB5\n1.SKB2.640194.30.B3\tSample\t384PP_AQ_BP2_HT\tD5\t12.068\t415.0\tNormalizedDNA\tD5\n1.SKB3.640195.30.C3\tSample\t384PP_AQ_BP2_HT\tF5\t12.068\t415.0\tNormalizedDNA\tF5\n1.SKB4.640189.30.D3\tSample\t384PP_AQ_BP2_HT\tH5\t12.068\t415.0\tNormalizedDNA\tH5\n1.SKB5.640181.30.E3\tSample\t384PP_AQ_BP2_HT\tJ5\t12.068\t415.0\tNormalizedDNA\tJ5\n1.SKB6.640176.30.F3\tSample\t384PP_AQ_BP2_HT\tL5\t12.068\t415.0\tNormalizedDNA\tL5\nvibrio.positive.control.30.G3\tSample\t384PP_AQ_BP2_HT\tN5\t6.089\t820.0\tNormalizedDNA\tN5\nblank.30.H3\tSample\t384PP_AQ_BP2_HT\tP5\t0.342\t3500.0\tNormalizedDNA\tP5\n1.SKB1.640202.30.A4\tSample\t384PP_AQ_BP2_HT\tB7\t12.068\t415.0\tNormalizedDNA\tB7\n1.SKB2.640194.30.B4\tSample\t384PP_AQ_BP2_HT\tD7\t12.068\t415.0\tNormalizedDNA\tD7\n1.SKB3.640195.30.C4\tSample\t384PP_AQ_BP2_HT\tF7\t12.068\t415.0\tNormalizedDNA\tF7\n1.SKB4.640189.30.D4\tSample\t384PP_AQ_BP2_HT\tH7\t12.068\t415.0\tNormalizedDNA\tH7\n1.SKB5.640181.30.E4\tSample\t384PP_AQ_BP2_HT\tJ7\t12.068\t415.0\tNormalizedDNA\tJ7\n1.SKB6.640176.30.F4\tSample\t384PP_AQ_BP2_HT\tL7\t12.068\t415.0\tNormalizedDNA\tL7\nvibrio.positive.control.30.G4\tSample\t384PP_AQ_BP2_HT\tN7\t6.089\t820.0\tNormalizedDNA\tN7\nblank.30.H4\tSample\t384PP_AQ_BP2_HT\tP7\t0.342\t3500.0\tNormalizedDNA\tP7\n1.SKB1.640202.30.A5\tSample\t384PP_AQ_BP2_HT\tB9\t12.068\t415.0\tNormalizedDNA\tB9\n1.SKB2.640194.30.B5\tSample\t384PP_AQ_BP2_HT\tD9\t12.068\t415.0\tNormalizedDNA\tD9\n1.SKB3.640195.30.C5\tSample\t384PP_AQ_BP2_HT\tF9\t12.068\t415.0\tNormalizedDNA\tF9\n1.SKB4.640189.30.D5\tSample\t384PP_AQ_BP2_HT\tH9\t12.068\t415.0\tNormalizedDNA\tH9\n1.SKB5.640181.30.E5\tSample\t384PP_AQ_BP2_HT\tJ9\t12.068\t415.0\tNormalizedDNA\tJ9\n1.SKB6.640176.30.F5\tSample\t384PP_AQ_BP2_HT\tL9\t12.068\t415.0\tNormalizedDNA\tL9\nvibrio.positive.control.30.G5\tSample\t384PP_AQ_BP2_HT\tN9\t6.089\t820.0\tNormalizedDNA\tN9\nblank.30.H5\tSample\t384PP_AQ_BP2_HT\tP9\t0.342\t3500.0\tNormalizedDNA\tP9\n1.SKB1.640202.30.A6\tSample\t384PP_AQ_BP2_HT\tB11\t12.068\t415.0\tNormalizedDNA\tB11\n1.SKB2.640194.30.B6\tSample\t384PP_AQ_BP2_HT\tD11\t12.068\t415.0\tNormalizedDNA\tD11\n1.SKB3.640195.30.C6\tSample\t384PP_AQ_BP2_HT\tF11\t12.068\t415.0\tNormalizedDNA\tF11\n1.SKB4.640189.30.D6\tSample\t384PP_AQ_BP2_HT\tH11\t12.068\t415.0\tNormalizedDNA\tH11\n1.SKB5.640181.30.E6\tSample\t384PP_AQ_BP2_HT\tJ11\t12.068\t415.0\tNormalizedDNA\tJ11\n1.SKB6.640176.30.F6\tSample\t384PP_AQ_BP2_HT\tL11\t12.068\t415.0\tNormalizedDNA\tL11\nvibrio.positive.control.30.G6\tSample\t384PP_AQ_BP2_HT\tN11\t6.089\t820.0\tNormalizedDNA\tN11\nblank.30.H6\tSample\t384PP_AQ_BP2_HT\tP11\t0.342\t3500.0\tNormalizedDNA\tP11\n1.SKB1.640202.30.A7\tSample\t384PP_AQ_BP2_HT\tB13\t12.068\t415.0\tNormalizedDNA\tB13\n1.SKB2.640194.30.B7\tSample\t384PP_AQ_BP2_HT\tD13\t12.068\t415.0\tNormalizedDNA\tD13\n1.SKB3.640195.30.C7\tSample\t384PP_AQ_BP2_HT\tF13\t12.068\t415.0\tNormalizedDNA\tF13\n1.SKB4.640189.30.D7\tSample\t384PP_AQ_BP2_HT\tH13\t12.068\t415.0\tNormalizedDNA\tH13\n1.SKB5.640181.30.E7\tSample\t384PP_AQ_BP2_HT\tJ13\t12.068\t415.0\tNormalizedDNA\tJ13\n1.SKB6.640176.30.F7\tSample\t384PP_AQ_BP2_HT\tL13\t12.068\t415.0\tNormalizedDNA\tL13\nvibrio.positive.control.30.G7\tSample\t384PP_AQ_BP2_HT\tN13\t6.089\t820.0\tNormalizedDNA\tN13\nblank.30.H7\tSample\t384PP_AQ_BP2_HT\tP13\t0.342\t3500.0\tNormalizedDNA\tP13\n1.SKB1.640202.30.A8\tSample\t384PP_AQ_BP2_HT\tB15\t12.068\t415.0\tNormalizedDNA\tB15\n1.SKB2.640194.30.B8\tSample\t384PP_AQ_BP2_HT\tD15\t12.068\t415.0\tNormalizedDNA\tD15\n1.SKB3.640195.30.C8\tSample\t384PP_AQ_BP2_HT\tF15\t12.068\t415.0\tNormalizedDNA\tF15\n1.SKB4.640189.30.D8\tSample\t384PP_AQ_BP2_HT\tH15\t12.068\t415.0\tNormalizedDNA\tH15\n1.SKB5.640181.30.E8\tSample\t384PP_AQ_BP2_HT\tJ15\t12.068\t415.0\tNormalizedDNA\tJ15\n1.SKB6.640176.30.F8\tSample\t384PP_AQ_BP2_HT\tL15\t12.068\t415.0\tNormalizedDNA\tL15\nvibrio.positive.control.30.G8\tSample\t384PP_AQ_BP2_HT\tN15\t6.089\t820.0\tNormalizedDNA\tN15\nblank.30.H8\tSample\t384PP_AQ_BP2_HT\tP15\t0.342\t3500.0\tNormalizedDNA\tP15\n1.SKB1.640202.30.A9\tSample\t384PP_AQ_BP2_HT\tB17\t12.068\t415.0\tNormalizedDNA\tB17\n1.SKB2.640194.30.B9\tSample\t384PP_AQ_BP2_HT\tD17\t12.068\t415.0\tNormalizedDNA\tD17\n1.SKB3.640195.30.C9\tSample\t384PP_AQ_BP2_HT\tF17\t12.068\t415.0\tNormalizedDNA\tF17\n1.SKB4.640189.30.D9\tSample\t384PP_AQ_BP2_HT\tH17\t12.068\t415.0\tNormalizedDNA\tH17\n1.SKB5.640181.30.E9\tSample\t384PP_AQ_BP2_HT\tJ17\t12.068\t415.0\tNormalizedDNA\tJ17\n1.SKB6.640176.30.F9\tSample\t384PP_AQ_BP2_HT\tL17\t12.068\t415.0\tNormalizedDNA\tL17\nvibrio.positive.control.30.G9\tSample\t384PP_AQ_BP2_HT\tN17\t6.089\t820.0\tNormalizedDNA\tN17\nblank.30.H9\tSample\t384PP_AQ_BP2_HT\tP17\t0.342\t3500.0\tNormalizedDNA\tP17\n1.SKB1.640202.30.A10\tSample\t384PP_AQ_BP2_HT\tB19\t12.068\t415.0\tNormalizedDNA\tB19\n1.SKB2.640194.30.B10\tSample\t384PP_AQ_BP2_HT\tD19\t12.068\t415.0\tNormalizedDNA\tD19\n1.SKB3.640195.30.C10\tSample\t384PP_AQ_BP2_HT\tF19\t12.068\t415.0\tNormalizedDNA\tF19\n1.SKB4.640189.30.D10\tSample\t384PP_AQ_BP2_HT\tH19\t12.068\t415.0\tNormalizedDNA\tH19\n1.SKB5.640181.30.E10\tSample\t384PP_AQ_BP2_HT\tJ19\t12.068\t415.0\tNormalizedDNA\tJ19\n1.SKB6.640176.30.F10\tSample\t384PP_AQ_BP2_HT\tL19\t12.068\t415.0\tNormalizedDNA\tL19\nvibrio.positive.control.30.G10\tSample\t384PP_AQ_BP2_HT\tN19\t6.089\t820.0\tNormalizedDNA\tN19\nblank.30.H10\tSample\t384PP_AQ_BP2_HT\tP19\t0.342\t3500.0\tNormalizedDNA\tP19\n1.SKB1.640202.30.A11\tSample\t384PP_AQ_BP2_HT\tB21\t12.068\t415.0\tNormalizedDNA\tB21\n1.SKB2.640194.30.B11\tSample\t384PP_AQ_BP2_HT\tD21\t12.068\t415.0\tNormalizedDNA\tD21\n1.SKB3.640195.30.C11\tSample\t384PP_AQ_BP2_HT\tF21\t12.068\t415.0\tNormalizedDNA\tF21\n1.SKB4.640189.30.D11\tSample\t384PP_AQ_BP2_HT\tH21\t12.068\t415.0\tNormalizedDNA\tH21\n1.SKB5.640181.30.E11\tSample\t384PP_AQ_BP2_HT\tJ21\t12.068\t415.0\tNormalizedDNA\tJ21\n1.SKB6.640176.30.F11\tSample\t384PP_AQ_BP2_HT\tL21\t12.068\t415.0\tNormalizedDNA\tL21\nvibrio.positive.control.30.G11\tSample\t384PP_AQ_BP2_HT\tN21\t6.089\t820.0\tNormalizedDNA\tN21\nblank.30.H11\tSample\t384PP_AQ_BP2_HT\tP21\t0.342\t3500.0\tNormalizedDNA\tP21\n1.SKB1.640202.30.A12\tSample\t384PP_AQ_BP2_HT\tB23\t12.068\t415.0\tNormalizedDNA\tB23\n1.SKB2.640194.30.B12\tSample\t384PP_AQ_BP2_HT\tD23\t12.068\t415.0\tNormalizedDNA\tD23\n1.SKB3.640195.30.C12\tSample\t384PP_AQ_BP2_HT\tF23\t12.068\t415.0\tNormalizedDNA\tF23\n1.SKB4.640189.30.D12\tSample\t384PP_AQ_BP2_HT\tH23\t12.068\t415.0\tNormalizedDNA\tH23\n1.SKB5.640181.30.E12\tSample\t384PP_AQ_BP2_HT\tJ23\t12.068\t415.0\tNormalizedDNA\tJ23\n1.SKB6.640176.30.F12\tSample\t384PP_AQ_BP2_HT\tL23\t12.068\t415.0\tNormalizedDNA\tL23\nvibrio.positive.control.30.G12\tSample\t384PP_AQ_BP2_HT\tN23\t6.089\t820.0\tNormalizedDNA\tN23\n1.SKB1.640202.33.A1\tSample\t384PP_AQ_BP2_HT\tB2\t12.068\t415.0\tNormalizedDNA\tB2\n1.SKB2.640194.33.B1\tSample\t384PP_AQ_BP2_HT\tD2\t12.068\t415.0\tNormalizedDNA\tD2\n1.SKB3.640195.33.C1\tSample\t384PP_AQ_BP2_HT\tF2\t12.068\t415.0\tNormalizedDNA\tF2\n1.SKB4.640189.33.D1\tSample\t384PP_AQ_BP2_HT\tH2\t12.068\t415.0\tNormalizedDNA\tH2\n1.SKB5.640181.33.E1\tSample\t384PP_AQ_BP2_HT\tJ2\t12.068\t415.0\tNormalizedDNA\tJ2\n1.SKB6.640176.33.F1\tSample\t384PP_AQ_BP2_HT\tL2\t12.068\t415.0\tNormalizedDNA\tL2\nvibrio.positive.control.33.G1\tSample\t384PP_AQ_BP2_HT\tN2\t6.089\t820.0\tNormalizedDNA\tN2\nblank.33.H1\tSample\t384PP_AQ_BP2_HT\tP2\t0.342\t3500.0\tNormalizedDNA\tP2\n1.SKB1.640202.33.A2\tSample\t384PP_AQ_BP2_HT\tB4\t12.068\t415.0\tNormalizedDNA\tB4\n1.SKB2.640194.33.B2\tSample\t384PP_AQ_BP2_HT\tD4\t12.068\t415.0\tNormalizedDNA\tD4\n1.SKB3.640195.33.C2\tSample\t384PP_AQ_BP2_HT\tF4\t12.068\t415.0\tNormalizedDNA\tF4\n1.SKB4.640189.33.D2\tSample\t384PP_AQ_BP2_HT\tH4\t12.068\t415.0\tNormalizedDNA\tH4\n1.SKB5.640181.33.E2\tSample\t384PP_AQ_BP2_HT\tJ4\t12.068\t415.0\tNormalizedDNA\tJ4\n1.SKB6.640176.33.F2\tSample\t384PP_AQ_BP2_HT\tL4\t12.068\t415.0\tNormalizedDNA\tL4\nvibrio.positive.control.33.G2\tSample\t384PP_AQ_BP2_HT\tN4\t6.089\t820.0\tNormalizedDNA\tN4\nblank.33.H2\tSample\t384PP_AQ_BP2_HT\tP4\t0.342\t3500.0\tNormalizedDNA\tP4\n1.SKB1.640202.33.A3\tSample\t384PP_AQ_BP2_HT\tB6\t12.068\t415.0\tNormalizedDNA\tB6\n1.SKB2.640194.33.B3\tSample\t384PP_AQ_BP2_HT\tD6\t12.068\t415.0\tNormalizedDNA\tD6\n1.SKB3.640195.33.C3\tSample\t384PP_AQ_BP2_HT\tF6\t12.068\t415.0\tNormalizedDNA\tF6\n1.SKB4.640189.33.D3\tSample\t384PP_AQ_BP2_HT\tH6\t12.068\t415.0\tNormalizedDNA\tH6\n1.SKB5.640181.33.E3\tSample\t384PP_AQ_BP2_HT\tJ6\t12.068\t415.0\tNormalizedDNA\tJ6\n1.SKB6.640176.33.F3\tSample\t384PP_AQ_BP2_HT\tL6\t12.068\t415.0\tNormalizedDNA\tL6\nvibrio.positive.control.33.G3\tSample\t384PP_AQ_BP2_HT\tN6\t6.089\t820.0\tNormalizedDNA\tN6\nblank.33.H3\tSample\t384PP_AQ_BP2_HT\tP6\t0.342\t3500.0\tNormalizedDNA\tP6\n1.SKB1.640202.33.A4\tSample\t384PP_AQ_BP2_HT\tB8\t12.068\t415.0\tNormalizedDNA\tB8\n1.SKB2.640194.33.B4\tSample\t384PP_AQ_BP2_HT\tD8\t12.068\t415.0\tNormalizedDNA\tD8\n1.SKB3.640195.33.C4\tSample\t384PP_AQ_BP2_HT\tF8\t12.068\t415.0\tNormalizedDNA\tF8\n1.SKB4.640189.33.D4\tSample\t384PP_AQ_BP2_HT\tH8\t12.068\t415.0\tNormalizedDNA\tH8\n1.SKB5.640181.33.E4\tSample\t384PP_AQ_BP2_HT\tJ8\t12.068\t415.0\tNormalizedDNA\tJ8\n1.SKB6.640176.33.F4\tSample\t384PP_AQ_BP2_HT\tL8\t12.068\t415.0\tNormalizedDNA\tL8\nvibrio.positive.control.33.G4\tSample\t384PP_AQ_BP2_HT\tN8\t6.089\t820.0\tNormalizedDNA\tN8\nblank.33.H4\tSample\t384PP_AQ_BP2_HT\tP8\t0.342\t3500.0\tNormalizedDNA\tP8\n1.SKB1.640202.33.A5\tSample\t384PP_AQ_BP2_HT\tB10\t12.068\t415.0\tNormalizedDNA\tB10\n1.SKB2.640194.33.B5\tSample\t384PP_AQ_BP2_HT\tD10\t12.068\t415.0\tNormalizedDNA\tD10\n1.SKB3.640195.33.C5\tSample\t384PP_AQ_BP2_HT\tF10\t12.068\t415.0\tNormalizedDNA\tF10\n1.SKB4.640189.33.D5\tSample\t384PP_AQ_BP2_HT\tH10\t12.068\t415.0\tNormalizedDNA\tH10\n1.SKB5.640181.33.E5\tSample\t384PP_AQ_BP2_HT\tJ10\t12.068\t415.0\tNormalizedDNA\tJ10\n1.SKB6.640176.33.F5\tSample\t384PP_AQ_BP2_HT\tL10\t12.068\t415.0\tNormalizedDNA\tL10\nvibrio.positive.control.33.G5\tSample\t384PP_AQ_BP2_HT\tN10\t6.089\t820.0\tNormalizedDNA\tN10\nblank.33.H5\tSample\t384PP_AQ_BP2_HT\tP10\t0.342\t3500.0\tNormalizedDNA\tP10\n1.SKB1.640202.33.A6\tSample\t384PP_AQ_BP2_HT\tB12\t12.068\t415.0\tNormalizedDNA\tB12\n1.SKB2.640194.33.B6\tSample\t384PP_AQ_BP2_HT\tD12\t12.068\t415.0\tNormalizedDNA\tD12\n1.SKB3.640195.33.C6\tSample\t384PP_AQ_BP2_HT\tF12\t12.068\t415.0\tNormalizedDNA\tF12\n1.SKB4.640189.33.D6\tSample\t384PP_AQ_BP2_HT\tH12\t12.068\t415.0\tNormalizedDNA\tH12\n1.SKB5.640181.33.E6\tSample\t384PP_AQ_BP2_HT\tJ12\t12.068\t415.0\tNormalizedDNA\tJ12\n1.SKB6.640176.33.F6\tSample\t384PP_AQ_BP2_HT\tL12\t12.068\t415.0\tNormalizedDNA\tL12\nvibrio.positive.control.33.G6\tSample\t384PP_AQ_BP2_HT\tN12\t6.089\t820.0\tNormalizedDNA\tN12\nblank.33.H6\tSample\t384PP_AQ_BP2_HT\tP12\t0.342\t3500.0\tNormalizedDNA\tP12\n1.SKB1.640202.33.A7\tSample\t384PP_AQ_BP2_HT\tB14\t12.068\t415.0\tNormalizedDNA\tB14\n1.SKB2.640194.33.B7\tSample\t384PP_AQ_BP2_HT\tD14\t12.068\t415.0\tNormalizedDNA\tD14\n1.SKB3.640195.33.C7\tSample\t384PP_AQ_BP2_HT\tF14\t12.068\t415.0\tNormalizedDNA\tF14\n1.SKB4.640189.33.D7\tSample\t384PP_AQ_BP2_HT\tH14\t12.068\t415.0\tNormalizedDNA\tH14\n1.SKB5.640181.33.E7\tSample\t384PP_AQ_BP2_HT\tJ14\t12.068\t415.0\tNormalizedDNA\tJ14\n1.SKB6.640176.33.F7\tSample\t384PP_AQ_BP2_HT\tL14\t12.068\t415.0\tNormalizedDNA\tL14\nvibrio.positive.control.33.G7\tSample\t384PP_AQ_BP2_HT\tN14\t6.089\t820.0\tNormalizedDNA\tN14\nblank.33.H7\tSample\t384PP_AQ_BP2_HT\tP14\t0.342\t3500.0\tNormalizedDNA\tP14\n1.SKB1.640202.33.A8\tSample\t384PP_AQ_BP2_HT\tB16\t12.068\t415.0\tNormalizedDNA\tB16\n1.SKB2.640194.33.B8\tSample\t384PP_AQ_BP2_HT\tD16\t12.068\t415.0\tNormalizedDNA\tD16\n1.SKB3.640195.33.C8\tSample\t384PP_AQ_BP2_HT\tF16\t12.068\t415.0\tNormalizedDNA\tF16\n1.SKB4.640189.33.D8\tSample\t384PP_AQ_BP2_HT\tH16\t12.068\t415.0\tNormalizedDNA\tH16\n1.SKB5.640181.33.E8\tSample\t384PP_AQ_BP2_HT\tJ16\t12.068\t415.0\tNormalizedDNA\tJ16\n1.SKB6.640176.33.F8\tSample\t384PP_AQ_BP2_HT\tL16\t12.068\t415.0\tNormalizedDNA\tL16\nvibrio.positive.control.33.G8\tSample\t384PP_AQ_BP2_HT\tN16\t6.089\t820.0\tNormalizedDNA\tN16\nblank.33.H8\tSample\t384PP_AQ_BP2_HT\tP16\t0.342\t3500.0\tNormalizedDNA\tP16\n1.SKB1.640202.33.A9\tSample\t384PP_AQ_BP2_HT\tB18\t12.068\t415.0\tNormalizedDNA\tB18\n1.SKB2.640194.33.B9\tSample\t384PP_AQ_BP2_HT\tD18\t12.068\t415.0\tNormalizedDNA\tD18\n1.SKB3.640195.33.C9\tSample\t384PP_AQ_BP2_HT\tF18\t12.068\t415.0\tNormalizedDNA\tF18\n1.SKB4.640189.33.D9\tSample\t384PP_AQ_BP2_HT\tH18\t12.068\t415.0\tNormalizedDNA\tH18\n1.SKB5.640181.33.E9\tSample\t384PP_AQ_BP2_HT\tJ18\t12.068\t415.0\tNormalizedDNA\tJ18\n1.SKB6.640176.33.F9\tSample\t384PP_AQ_BP2_HT\tL18\t12.068\t415.0\tNormalizedDNA\tL18\nvibrio.positive.control.33.G9\tSample\t384PP_AQ_BP2_HT\tN18\t6.089\t820.0\tNormalizedDNA\tN18\nblank.33.H9\tSample\t384PP_AQ_BP2_HT\tP18\t0.342\t3500.0\tNormalizedDNA\tP18\n1.SKB1.640202.33.A10\tSample\t384PP_AQ_BP2_HT\tB20\t12.068\t415.0\tNormalizedDNA\tB20\n1.SKB2.640194.33.B10\tSample\t384PP_AQ_BP2_HT\tD20\t12.068\t415.0\tNormalizedDNA\tD20\n1.SKB3.640195.33.C10\tSample\t384PP_AQ_BP2_HT\tF20\t12.068\t415.0\tNormalizedDNA\tF20\n1.SKB4.640189.33.D10\tSample\t384PP_AQ_BP2_HT\tH20\t12.068\t415.0\tNormalizedDNA\tH20\n1.SKB5.640181.33.E10\tSample\t384PP_AQ_BP2_HT\tJ20\t12.068\t415.0\tNormalizedDNA\tJ20\n1.SKB6.640176.33.F10\tSample\t384PP_AQ_BP2_HT\tL20\t12.068\t415.0\tNormalizedDNA\tL20\nvibrio.positive.control.33.G10\tSample\t384PP_AQ_BP2_HT\tN20\t6.089\t820.0\tNormalizedDNA\tN20\nblank.33.H10\tSample\t384PP_AQ_BP2_HT\tP20\t0.342\t3500.0\tNormalizedDNA\tP20\n1.SKB1.640202.33.A11\tSample\t384PP_AQ_BP2_HT\tB22\t12.068\t415.0\tNormalizedDNA\tB22\n1.SKB2.640194.33.B11\tSample\t384PP_AQ_BP2_HT\tD22\t12.068\t415.0\tNormalizedDNA\tD22\n1.SKB3.640195.33.C11\tSample\t384PP_AQ_BP2_HT\tF22\t12.068\t415.0\tNormalizedDNA\tF22\n1.SKB4.640189.33.D11\tSample\t384PP_AQ_BP2_HT\tH22\t12.068\t415.0\tNormalizedDNA\tH22\n1.SKB5.640181.33.E11\tSample\t384PP_AQ_BP2_HT\tJ22\t12.068\t415.0\tNormalizedDNA\tJ22\n1.SKB6.640176.33.F11\tSample\t384PP_AQ_BP2_HT\tL22\t12.068\t415.0\tNormalizedDNA\tL22\nvibrio.positive.control.33.G11\tSample\t384PP_AQ_BP2_HT\tN22\t6.089\t820.0\tNormalizedDNA\tN22\nblank.33.H11\tSample\t384PP_AQ_BP2_HT\tP22\t0.342\t3500.0\tNormalizedDNA\tP22\n1.SKB1.640202.33.A12\tSample\t384PP_AQ_BP2_HT\tB24\t12.068\t415.0\tNormalizedDNA\tB24\n1.SKB2.640194.33.B12\tSample\t384PP_AQ_BP2_HT\tD24\t12.068\t415.0\tNormalizedDNA\tD24\n1.SKB3.640195.33.C12\tSample\t384PP_AQ_BP2_HT\tF24\t12.068\t415.0\tNormalizedDNA\tF24\n1.SKB4.640189.33.D12\tSample\t384PP_AQ_BP2_HT\tH24\t12.068\t415.0\tNormalizedDNA\tH24\n1.SKB5.640181.33.E12\tSample\t384PP_AQ_BP2_HT\tJ24\t12.068\t415.0\tNormalizedDNA\tJ24\n1.SKB6.640176.33.F12\tSample\t384PP_AQ_BP2_HT\tL24\t12.068\t415.0\tNormalizedDNA\tL24\nvibrio.positive.control.33.G12\tSample\t384PP_AQ_BP2_HT\tN24\t6.089\t820.0\tNormalizedDNA\tN24'

TARGET_EXAMPLE = 'sample_name\tcenter_project_name\tepmotion_robot\tepmotion_tm300_8_tool\tepmotion_tm50_8_tool\tepmotion_tool\texperiment\textraction_kit\tfwd_cycles\tgdata_robot\tkingfisher_robot\tmaster_mix\tplate\tplatform\tprimer_composition\tprimer_set_composition\tprincipal_investigator\trev_cycles\trun_name\trun_prefix\tsequencer_description\twater_lot\twell\n1.SKB1.640202.21.A1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTCCCTTGTCTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA1\n1.SKB1.640202.21.A10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTACAGCGCATAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA10\n1.SKB1.640202.21.A11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACCGGTATGTAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA11\n1.SKB1.640202.21.A12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAATTGTGTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA12\n1.SKB1.640202.21.A2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACGAGACTGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA2\n1.SKB1.640202.21.A3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGCTGTACGGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA3\n1.SKB1.640202.21.A4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATCACCAGGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA4\n1.SKB1.640202.21.A5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGGTCAACGATA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA5\n1.SKB1.640202.21.A6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATCGCACAGTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA6\n1.SKB1.640202.21.A7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGTGTAGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA7\n1.SKB1.640202.21.A8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGCGGAGGTTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA8\n1.SKB1.640202.21.A9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATCCTTTGGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA9\n1.SKB1.640202.27.A1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTCCCTTGTCTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA1\n1.SKB1.640202.27.A10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTACAGCGCATAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA10\n1.SKB1.640202.27.A11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACCGGTATGTAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA11\n1.SKB1.640202.27.A12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAATTGTGTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA12\n1.SKB1.640202.27.A2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACGAGACTGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA2\n1.SKB1.640202.27.A3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGCTGTACGGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA3\n1.SKB1.640202.27.A4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATCACCAGGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA4\n1.SKB1.640202.27.A5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGGTCAACGATA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA5\n1.SKB1.640202.27.A6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATCGCACAGTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA6\n1.SKB1.640202.27.A7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGTGTAGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA7\n1.SKB1.640202.27.A8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGCGGAGGTTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA8\n1.SKB1.640202.27.A9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATCCTTTGGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA9\n1.SKB1.640202.30.A1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTCCCTTGTCTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA1\n1.SKB1.640202.30.A10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTACAGCGCATAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA10\n1.SKB1.640202.30.A11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACCGGTATGTAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA11\n1.SKB1.640202.30.A12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAATTGTGTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA12\n1.SKB1.640202.30.A2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACGAGACTGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA2\n1.SKB1.640202.30.A3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGCTGTACGGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA3\n1.SKB1.640202.30.A4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATCACCAGGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA4\n1.SKB1.640202.30.A5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGGTCAACGATA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA5\n1.SKB1.640202.30.A6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATCGCACAGTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA6\n1.SKB1.640202.30.A7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGTGTAGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA7\n1.SKB1.640202.30.A8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGCGGAGGTTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA8\n1.SKB1.640202.30.A9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATCCTTTGGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA9\n1.SKB1.640202.33.A1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTCCCTTGTCTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA1\n1.SKB1.640202.33.A10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTACAGCGCATAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA10\n1.SKB1.640202.33.A11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACCGGTATGTAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA11\n1.SKB1.640202.33.A12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAATTGTGTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA12\n1.SKB1.640202.33.A2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACGAGACTGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA2\n1.SKB1.640202.33.A3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGCTGTACGGATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA3\n1.SKB1.640202.33.A4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATCACCAGGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA4\n1.SKB1.640202.33.A5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGGTCAACGATA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA5\n1.SKB1.640202.33.A6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATCGCACAGTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA6\n1.SKB1.640202.33.A7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGTGTAGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA7\n1.SKB1.640202.33.A8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGCGGAGGTTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA8\n1.SKB1.640202.33.A9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATCCTTTGGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tA9\n1.SKB2.640194.21.B1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGCATACACTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB1\n1.SKB2.640194.21.B10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCAGCTCATCAGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB10\n1.SKB2.640194.21.B11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCAAACAACAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB11\n1.SKB2.640194.21.B12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGCAACACCATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB12\n1.SKB2.640194.21.B2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGAACGAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB2\n1.SKB2.640194.21.B3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACCAGTGACTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB3\n1.SKB2.640194.21.B4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGAATACCAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB4\n1.SKB2.640194.21.B5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTAGATCGTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB5\n1.SKB2.640194.21.B6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTAACGTGTGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB6\n1.SKB2.640194.21.B7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCATTATGGCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB7\n1.SKB2.640194.21.B8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCCAATACGCCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB8\n1.SKB2.640194.21.B9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGATCTGCGATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB9\n1.SKB2.640194.27.B1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGCATACACTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB1\n1.SKB2.640194.27.B10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCAGCTCATCAGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB10\n1.SKB2.640194.27.B11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCAAACAACAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB11\n1.SKB2.640194.27.B12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGCAACACCATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB12\n1.SKB2.640194.27.B2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGAACGAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB2\n1.SKB2.640194.27.B3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACCAGTGACTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB3\n1.SKB2.640194.27.B4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGAATACCAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB4\n1.SKB2.640194.27.B5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTAGATCGTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB5\n1.SKB2.640194.27.B6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTAACGTGTGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB6\n1.SKB2.640194.27.B7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCATTATGGCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB7\n1.SKB2.640194.27.B8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCCAATACGCCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB8\n1.SKB2.640194.27.B9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGATCTGCGATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB9\n1.SKB2.640194.30.B1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGCATACACTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB1\n1.SKB2.640194.30.B10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCAGCTCATCAGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB10\n1.SKB2.640194.30.B11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCAAACAACAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB11\n1.SKB2.640194.30.B12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGCAACACCATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB12\n1.SKB2.640194.30.B2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGAACGAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB2\n1.SKB2.640194.30.B3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACCAGTGACTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB3\n1.SKB2.640194.30.B4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGAATACCAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB4\n1.SKB2.640194.30.B5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTAGATCGTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB5\n1.SKB2.640194.30.B6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTAACGTGTGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB6\n1.SKB2.640194.30.B7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCATTATGGCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB7\n1.SKB2.640194.30.B8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCCAATACGCCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB8\n1.SKB2.640194.30.B9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGATCTGCGATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB9\n1.SKB2.640194.33.B1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGCATACACTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB1\n1.SKB2.640194.33.B10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCAGCTCATCAGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB10\n1.SKB2.640194.33.B11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCAAACAACAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB11\n1.SKB2.640194.33.B12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGCAACACCATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB12\n1.SKB2.640194.33.B2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGAACGAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB2\n1.SKB2.640194.33.B3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACCAGTGACTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB3\n1.SKB2.640194.33.B4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGAATACCAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB4\n1.SKB2.640194.33.B5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTAGATCGTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB5\n1.SKB2.640194.33.B6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTAACGTGTGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB6\n1.SKB2.640194.33.B7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCATTATGGCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB7\n1.SKB2.640194.33.B8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCCAATACGCCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB8\n1.SKB2.640194.33.B9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGATCTGCGATCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tB9\n1.SKB3.640195.21.C1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGCGATATATCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC1\n1.SKB3.640195.21.C10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCAACTCCCGTGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC10\n1.SKB3.640195.21.C11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTTGCGTTAGCAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC11\n1.SKB3.640195.21.C12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTACGAGCCCTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC12\n1.SKB3.640195.21.C2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGCAATCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC2\n1.SKB3.640195.21.C3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGTGCACAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC3\n1.SKB3.640195.21.C4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTATCTGCGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC4\n1.SKB3.640195.21.C5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGGGAAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC5\n1.SKB3.640195.21.C6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCAAATTCGGGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC6\n1.SKB3.640195.21.C7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGATTGACCAAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC7\n1.SKB3.640195.21.C8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTACGAGCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC8\n1.SKB3.640195.21.C9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGCATATGCACTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC9\n1.SKB3.640195.27.C1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGCGATATATCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC1\n1.SKB3.640195.27.C10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCAACTCCCGTGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC10\n1.SKB3.640195.27.C11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTTGCGTTAGCAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC11\n1.SKB3.640195.27.C12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTACGAGCCCTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC12\n1.SKB3.640195.27.C2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGCAATCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC2\n1.SKB3.640195.27.C3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGTGCACAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC3\n1.SKB3.640195.27.C4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTATCTGCGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC4\n1.SKB3.640195.27.C5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGGGAAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC5\n1.SKB3.640195.27.C6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCAAATTCGGGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC6\n1.SKB3.640195.27.C7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGATTGACCAAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC7\n1.SKB3.640195.27.C8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTACGAGCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC8\n1.SKB3.640195.27.C9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGCATATGCACTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC9\n1.SKB3.640195.30.C1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGCGATATATCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC1\n1.SKB3.640195.30.C10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCAACTCCCGTGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC10\n1.SKB3.640195.30.C11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTTGCGTTAGCAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC11\n1.SKB3.640195.30.C12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTACGAGCCCTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC12\n1.SKB3.640195.30.C2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGCAATCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC2\n1.SKB3.640195.30.C3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGTGCACAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC3\n1.SKB3.640195.30.C4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTATCTGCGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC4\n1.SKB3.640195.30.C5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGGGAAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC5\n1.SKB3.640195.30.C6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCAAATTCGGGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC6\n1.SKB3.640195.30.C7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGATTGACCAAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC7\n1.SKB3.640195.30.C8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTACGAGCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC8\n1.SKB3.640195.30.C9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGCATATGCACTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC9\n1.SKB3.640195.33.C1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGCGATATATCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC1\n1.SKB3.640195.33.C10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCAACTCCCGTGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC10\n1.SKB3.640195.33.C11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTTGCGTTAGCAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC11\n1.SKB3.640195.33.C12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTACGAGCCCTAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC12\n1.SKB3.640195.33.C2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGCAATCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC2\n1.SKB3.640195.33.C3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGTCGTGCACAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC3\n1.SKB3.640195.33.C4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTATCTGCGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC4\n1.SKB3.640195.33.C5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCGAGGGAAAGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC5\n1.SKB3.640195.33.C6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCAAATTCGGGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC6\n1.SKB3.640195.33.C7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGATTGACCAAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC7\n1.SKB3.640195.33.C8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTACGAGCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC8\n1.SKB3.640195.33.C9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGCATATGCACTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tC9\n1.SKB4.640189.21.D1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCACTACGCTAGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD1\n1.SKB4.640189.21.D10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTCGGAATTAGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD10\n1.SKB4.640189.21.D11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGTGAATTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD11\n1.SKB4.640189.21.D12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCATTCGTGGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD12\n1.SKB4.640189.21.D2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGCAGTCCTCGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD2\n1.SKB4.640189.21.D3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACCATAGCTCCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD3\n1.SKB4.640189.21.D4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTCGACATCTCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD4\n1.SKB4.640189.21.D5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGAACACTTTGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD5\n1.SKB4.640189.21.D6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGAGCCATCTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD6\n1.SKB4.640189.21.D7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGGTACACGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD7\n1.SKB4.640189.21.D8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAAGGCGCTCCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD8\n1.SKB4.640189.21.D9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTAATACGGATCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD9\n1.SKB4.640189.27.D1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCACTACGCTAGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD1\n1.SKB4.640189.27.D10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTCGGAATTAGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD10\n1.SKB4.640189.27.D11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGTGAATTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD11\n1.SKB4.640189.27.D12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCATTCGTGGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD12\n1.SKB4.640189.27.D2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGCAGTCCTCGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD2\n1.SKB4.640189.27.D3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACCATAGCTCCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD3\n1.SKB4.640189.27.D4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTCGACATCTCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD4\n1.SKB4.640189.27.D5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGAACACTTTGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD5\n1.SKB4.640189.27.D6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGAGCCATCTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD6\n1.SKB4.640189.27.D7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGGTACACGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD7\n1.SKB4.640189.27.D8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAAGGCGCTCCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD8\n1.SKB4.640189.27.D9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTAATACGGATCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD9\n1.SKB4.640189.30.D1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCACTACGCTAGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD1\n1.SKB4.640189.30.D10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTCGGAATTAGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD10\n1.SKB4.640189.30.D11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGTGAATTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD11\n1.SKB4.640189.30.D12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCATTCGTGGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD12\n1.SKB4.640189.30.D2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGCAGTCCTCGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD2\n1.SKB4.640189.30.D3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACCATAGCTCCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD3\n1.SKB4.640189.30.D4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTCGACATCTCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD4\n1.SKB4.640189.30.D5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGAACACTTTGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD5\n1.SKB4.640189.30.D6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGAGCCATCTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD6\n1.SKB4.640189.30.D7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGGTACACGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD7\n1.SKB4.640189.30.D8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAAGGCGCTCCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD8\n1.SKB4.640189.30.D9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTAATACGGATCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD9\n1.SKB4.640189.33.D1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCACTACGCTAGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD1\n1.SKB4.640189.33.D10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTCGGAATTAGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD10\n1.SKB4.640189.33.D11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGTGAATTCGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD11\n1.SKB4.640189.33.D12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCATTCGTGGCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD12\n1.SKB4.640189.33.D2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGCAGTCCTCGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD2\n1.SKB4.640189.33.D3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACCATAGCTCCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD3\n1.SKB4.640189.33.D4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTCGACATCTCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD4\n1.SKB4.640189.33.D5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGAACACTTTGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD5\n1.SKB4.640189.33.D6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGAGCCATCTGTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD6\n1.SKB4.640189.33.D7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGGTACACGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD7\n1.SKB4.640189.33.D8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAAGGCGCTCCTT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD8\n1.SKB4.640189.33.D9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTAATACGGATCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tD9\n1.SKB5.640181.21.E1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTACTACGTGGCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE1\n1.SKB5.640181.21.E10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTATACCGCTGCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE10\n1.SKB5.640181.21.E11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTGAGGCATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE11\n1.SKB5.640181.21.E12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACAATAGACACC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE12\n1.SKB5.640181.21.E2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGGCCAGTTCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE2\n1.SKB5.640181.21.E3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGATGTTCGCTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE3\n1.SKB5.640181.21.E4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCTATCTCCTGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE4\n1.SKB5.640181.21.E5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACTCACAGGAAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE5\n1.SKB5.640181.21.E6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATGATGAGCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE6\n1.SKB5.640181.21.E7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGACAGAGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE7\n1.SKB5.640181.21.E8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGTCGCAAATAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE8\n1.SKB5.640181.21.E9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCATCCCTCTACT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE9\n1.SKB5.640181.27.E1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTACTACGTGGCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE1\n1.SKB5.640181.27.E10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTATACCGCTGCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE10\n1.SKB5.640181.27.E11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTGAGGCATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE11\n1.SKB5.640181.27.E12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACAATAGACACC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE12\n1.SKB5.640181.27.E2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGGCCAGTTCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE2\n1.SKB5.640181.27.E3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGATGTTCGCTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE3\n1.SKB5.640181.27.E4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCTATCTCCTGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE4\n1.SKB5.640181.27.E5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACTCACAGGAAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE5\n1.SKB5.640181.27.E6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATGATGAGCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE6\n1.SKB5.640181.27.E7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGACAGAGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE7\n1.SKB5.640181.27.E8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGTCGCAAATAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE8\n1.SKB5.640181.27.E9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCATCCCTCTACT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE9\n1.SKB5.640181.30.E1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTACTACGTGGCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE1\n1.SKB5.640181.30.E10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTATACCGCTGCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE10\n1.SKB5.640181.30.E11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTGAGGCATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE11\n1.SKB5.640181.30.E12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACAATAGACACC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE12\n1.SKB5.640181.30.E2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGGCCAGTTCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE2\n1.SKB5.640181.30.E3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGATGTTCGCTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE3\n1.SKB5.640181.30.E4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCTATCTCCTGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE4\n1.SKB5.640181.30.E5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACTCACAGGAAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE5\n1.SKB5.640181.30.E6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATGATGAGCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE6\n1.SKB5.640181.30.E7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGACAGAGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE7\n1.SKB5.640181.30.E8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGTCGCAAATAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE8\n1.SKB5.640181.30.E9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCATCCCTCTACT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE9\n1.SKB5.640181.33.E1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTACTACGTGGCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE1\n1.SKB5.640181.33.E10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTATACCGCTGCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE10\n1.SKB5.640181.33.E11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGTTGAGGCATT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE11\n1.SKB5.640181.33.E12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACAATAGACACC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE12\n1.SKB5.640181.33.E2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGGCCAGTTCCTA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE2\n1.SKB5.640181.33.E3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGATGTTCGCTAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE3\n1.SKB5.640181.33.E4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCTATCTCCTGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE4\n1.SKB5.640181.33.E5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACTCACAGGAAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE5\n1.SKB5.640181.33.E6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATGATGAGCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE6\n1.SKB5.640181.33.E7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTCGACAGAGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE7\n1.SKB5.640181.33.E8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGTCGCAAATAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE8\n1.SKB5.640181.33.E9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCATCCCTCTACT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tE9\n1.SKB6.640176.21.F1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCGGTCAATTGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF1\n1.SKB6.640176.21.F10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTATCGACACAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF10\n1.SKB6.640176.21.F11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGATTCCGGCTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF11\n1.SKB6.640176.21.F12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAATTGCCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF12\n1.SKB6.640176.21.F2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGAGTCTCAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF2\n1.SKB6.640176.21.F3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGCTCGAAGATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF3\n1.SKB6.640176.21.F4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGGCTTACGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF4\n1.SKB6.640176.21.F5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTCTCTACCACTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF5\n1.SKB6.640176.21.F6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tACTTCCAACTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF6\n1.SKB6.640176.21.F7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACCTAGGAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF7\n1.SKB6.640176.21.F8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTGTTGTCGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF8\n1.SKB6.640176.21.F9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCCACAGATCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF9\n1.SKB6.640176.27.F1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCGGTCAATTGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF1\n1.SKB6.640176.27.F10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTATCGACACAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF10\n1.SKB6.640176.27.F11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGATTCCGGCTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF11\n1.SKB6.640176.27.F12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAATTGCCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF12\n1.SKB6.640176.27.F2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGAGTCTCAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF2\n1.SKB6.640176.27.F3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGCTCGAAGATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF3\n1.SKB6.640176.27.F4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGGCTTACGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF4\n1.SKB6.640176.27.F5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTCTCTACCACTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF5\n1.SKB6.640176.27.F6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tACTTCCAACTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF6\n1.SKB6.640176.27.F7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACCTAGGAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF7\n1.SKB6.640176.27.F8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTGTTGTCGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF8\n1.SKB6.640176.27.F9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCCACAGATCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF9\n1.SKB6.640176.30.F1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCGGTCAATTGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF1\n1.SKB6.640176.30.F10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTATCGACACAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF10\n1.SKB6.640176.30.F11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGATTCCGGCTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF11\n1.SKB6.640176.30.F12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAATTGCCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF12\n1.SKB6.640176.30.F2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGAGTCTCAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF2\n1.SKB6.640176.30.F3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGCTCGAAGATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF3\n1.SKB6.640176.30.F4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGGCTTACGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF4\n1.SKB6.640176.30.F5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTCTCTACCACTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF5\n1.SKB6.640176.30.F6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tACTTCCAACTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF6\n1.SKB6.640176.30.F7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACCTAGGAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF7\n1.SKB6.640176.30.F8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTGTTGTCGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF8\n1.SKB6.640176.30.F9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCCACAGATCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF9\n1.SKB6.640176.33.F1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCGGTCAATTGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF1\n1.SKB6.640176.33.F10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTATCGACACAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF10\n1.SKB6.640176.33.F11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGATTCCGGCTCA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF11\n1.SKB6.640176.33.F12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAATTGCCGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF12\n1.SKB6.640176.33.F2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGAGTCTCAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF2\n1.SKB6.640176.33.F3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGCTCGAAGATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF3\n1.SKB6.640176.33.F4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGGCTTACGTGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF4\n1.SKB6.640176.33.F5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTCTCTACCACTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF5\n1.SKB6.640176.33.F6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tACTTCCAACTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF6\n1.SKB6.640176.33.F7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACCTAGGAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF7\n1.SKB6.640176.33.F8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTGTTGTCGTGC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF8\n1.SKB6.640176.33.F9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCCACAGATCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tF9\nblank.21.H1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAAGATGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH1\nblank.21.H10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGGAGTAGGTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH10\nblank.21.H11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGCTCTATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH11\nblank.21.H2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGCGTTCTAGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH2\nblank.21.H3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTTGTTCTGGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH3\nblank.21.H4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGGACTTCCAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH4\nblank.21.H5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACAACCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH5\nblank.21.H6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tCTGCTATTCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH6\nblank.21.H7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATGTCACCGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH7\nblank.21.H8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGTAACGCCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH8\nblank.21.H9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGCAGAACATCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH9\nblank.27.H1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAAGATGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH1\nblank.27.H10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGGAGTAGGTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH10\nblank.27.H11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGCTCTATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH11\nblank.27.H2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGCGTTCTAGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH2\nblank.27.H3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTTGTTCTGGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH3\nblank.27.H4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGGACTTCCAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH4\nblank.27.H5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACAACCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH5\nblank.27.H6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tCTGCTATTCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH6\nblank.27.H7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATGTCACCGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH7\nblank.27.H8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGTAACGCCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH8\nblank.27.H9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGCAGAACATCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH9\nblank.30.H1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAAGATGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH1\nblank.30.H10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGGAGTAGGTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH10\nblank.30.H11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGCTCTATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH11\nblank.30.H2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGCGTTCTAGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH2\nblank.30.H3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTTGTTCTGGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH3\nblank.30.H4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGGACTTCCAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH4\nblank.30.H5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACAACCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH5\nblank.30.H6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tCTGCTATTCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH6\nblank.30.H7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATGTCACCGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH7\nblank.30.H8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGTAACGCCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH8\nblank.30.H9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGCAGAACATCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH9\nblank.33.H1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCGTAAGATGCCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH1\nblank.33.H10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGGAGTAGGTGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH10\nblank.33.H11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTTGGCTCTATTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH11\nblank.33.H2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGCGTTCTAGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH2\nblank.33.H3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTTGTTCTGGGA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH3\nblank.33.H4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGGACTTCCAGCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH4\nblank.33.H5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCTCACAACCGTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH5\nblank.33.H6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tCTGCTATTCCTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH6\nblank.33.H7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATGTCACCGCTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH7\nblank.33.H8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGTAACGCCGAT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH8\nblank.33.H9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGCAGAACATCT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tH9\nvibrio.positive.control.21.G1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGGTGACTAGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG1\nvibrio.positive.control.21.G10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTGCGCTGAATGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG10\nvibrio.positive.control.21.G11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATGGCTGTCAGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG11\nvibrio.positive.control.21.G12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTTCTCTTCTCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG12\nvibrio.positive.control.21.G2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATGGGTTCCGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG2\nvibrio.positive.control.21.G3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTAGGCATGCTTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG3\nvibrio.positive.control.21.G4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAACTAGTTCAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG4\nvibrio.positive.control.21.G5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tATTCTGCCGAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG5\nvibrio.positive.control.21.G6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tAGCATGTCCCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG6\nvibrio.positive.control.21.G7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTACGATATGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG7\nvibrio.positive.control.21.G8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGTGGTTTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG8\nvibrio.positive.control.21.G9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 1\tMiSeq\tEMP 16S V4 primer plate 1\tTAGTATGCGCAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG9\nvibrio.positive.control.27.G1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGGTGACTAGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG1\nvibrio.positive.control.27.G10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTGCGCTGAATGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG10\nvibrio.positive.control.27.G11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATGGCTGTCAGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG11\nvibrio.positive.control.27.G12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTTCTCTTCTCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG12\nvibrio.positive.control.27.G2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATGGGTTCCGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG2\nvibrio.positive.control.27.G3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTAGGCATGCTTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG3\nvibrio.positive.control.27.G4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAACTAGTTCAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG4\nvibrio.positive.control.27.G5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tATTCTGCCGAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG5\nvibrio.positive.control.27.G6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tAGCATGTCCCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG6\nvibrio.positive.control.27.G7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTACGATATGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG7\nvibrio.positive.control.27.G8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGTGGTTTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG8\nvibrio.positive.control.27.G9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 2\tMiSeq\tEMP 16S V4 primer plate 1\tTAGTATGCGCAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG9\nvibrio.positive.control.30.G1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGGTGACTAGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG1\nvibrio.positive.control.30.G10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTGCGCTGAATGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG10\nvibrio.positive.control.30.G11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATGGCTGTCAGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG11\nvibrio.positive.control.30.G12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTTCTCTTCTCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG12\nvibrio.positive.control.30.G2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATGGGTTCCGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG2\nvibrio.positive.control.30.G3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTAGGCATGCTTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG3\nvibrio.positive.control.30.G4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAACTAGTTCAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG4\nvibrio.positive.control.30.G5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tATTCTGCCGAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG5\nvibrio.positive.control.30.G6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tAGCATGTCCCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG6\nvibrio.positive.control.30.G7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTACGATATGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG7\nvibrio.positive.control.30.G8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGTGGTTTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG8\nvibrio.positive.control.30.G9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 3\tMiSeq\tEMP 16S V4 primer plate 1\tTAGTATGCGCAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG9\nvibrio.positive.control.33.G1\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGGTGACTAGTTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG1\nvibrio.positive.control.33.G10\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTGCGCTGAATGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG10\nvibrio.positive.control.33.G11\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATGGCTGTCAGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG11\nvibrio.positive.control.33.G12\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTTCTCTTCTCG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG12\nvibrio.positive.control.33.G2\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATGGGTTCCGTC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG2\nvibrio.positive.control.33.G3\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTAGGCATGCTTG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG3\nvibrio.positive.control.33.G4\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAACTAGTTCAGG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG4\nvibrio.positive.control.33.G5\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tATTCTGCCGAAG\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG5\nvibrio.positive.control.33.G6\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tAGCATGTCCCGT\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG6\nvibrio.positive.control.33.G7\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTACGATATGAC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG7\nvibrio.positive.control.33.G8\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tGTGGTGGTTTCC\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG8\nvibrio.positive.control.33.G9\tTestExperiment1\tJER-E\t109375A\t311411B\t108379Z\tTestExperiment1\t157022406\t151\tLUCY\tKF1\t443912\tTest plate 4\tMiSeq\tEMP 16S V4 primer plate 1\tTAGTATGCGCAA\ttest@foo.bar\t151\tTest Run.1\tTest Run.1\tMiSeq\tRNBF7110\tG9\n'

SHOTGUN_EXAMPLE = 'sample_name\tcenter_project_name\tepmotion_tool\texperiment\textraction_kit\tfwd_cycles\tgdata_robot\ti5_sequence\tkappa_hyper_plus_kit\tkingfisher_robot\tnormalization_water_lot\tplate\tplatform\tprincipal_investigator\trev_cycles\trun_name\trun_prefix\tsequencer_description\tstub_lot\twell\n1.SKB1.640202.21.A1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACGTTACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A1\tHiSeq4000\t\tA1\n1.SKB1.640202.21.A10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCTGGTT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A10\tHiSeq4000\t\tA10\n1.SKB1.640202.21.A11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCCTTGTT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A11\tHiSeq4000\t\tA11\n1.SKB1.640202.21.A12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTGAGAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A12\tHiSeq4000\t\tA12\n1.SKB1.640202.21.A2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTACACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A2\tHiSeq4000\t\tA2\n1.SKB1.640202.21.A3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCACGTTC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A3\tHiSeq4000\t\tA3\n1.SKB1.640202.21.A4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGCGATT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A4\tHiSeq4000\t\tA4\n1.SKB1.640202.21.A5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTGTCTT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A5\tHiSeq4000\t\tA5\n1.SKB1.640202.21.A6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGGTTGC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A6\tHiSeq4000\t\tA6\n1.SKB1.640202.21.A7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCACAACT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A7\tHiSeq4000\t\tA7\n1.SKB1.640202.21.A8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCGGAAT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A8\tHiSeq4000\t\tA8\n1.SKB1.640202.21.A9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACAAGTC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_A9\tHiSeq4000\t\tA9\n1.SKB1.640202.27.A1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTTCGAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A1\tHiSeq4000\t\tA1\n1.SKB1.640202.27.A10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCAGAGT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A10\tHiSeq4000\t\tA10\n1.SKB1.640202.27.A11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTACACGCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A11\tHiSeq4000\t\tA11\n1.SKB1.640202.27.A12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCCATTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A12\tHiSeq4000\t\tA12\n1.SKB1.640202.27.A2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTATTGGC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A2\tHiSeq4000\t\tA2\n1.SKB1.640202.27.A3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGCACTT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A3\tHiSeq4000\t\tA3\n1.SKB1.640202.27.A4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGACTTCG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A4\tHiSeq4000\t\tA4\n1.SKB1.640202.27.A5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCCGTATG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A5\tHiSeq4000\t\tA5\n1.SKB1.640202.27.A6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTCTCAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A6\tHiSeq4000\t\tA6\n1.SKB1.640202.27.A7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACGATGAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A7\tHiSeq4000\t\tA7\n1.SKB1.640202.27.A8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAACGCTT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A8\tHiSeq4000\t\tA8\n1.SKB1.640202.27.A9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCTGGAA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_27_A9\tHiSeq4000\t\tA9\n1.SKB1.640202.30.A1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTAGTGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A1\tHiSeq4000\t\tA1\n1.SKB1.640202.30.A10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAGCCGAA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A10\tHiSeq4000\t\tA10\n1.SKB1.640202.30.A11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCACGTAA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A11\tHiSeq4000\t\tA11\n1.SKB1.640202.30.A12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGAGTGA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A12\tHiSeq4000\t\tA12\n1.SKB1.640202.30.A2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGAGTGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A2\tHiSeq4000\t\tA2\n1.SKB1.640202.30.A3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGTTCGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A3\tHiSeq4000\t\tA3\n1.SKB1.640202.30.A4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCGTAAGA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A4\tHiSeq4000\t\tA4\n1.SKB1.640202.30.A5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAAGTTGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A5\tHiSeq4000\t\tA5\n1.SKB1.640202.30.A6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTAGTGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A6\tHiSeq4000\t\tA6\n1.SKB1.640202.30.A7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCACTGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A7\tHiSeq4000\t\tA7\n1.SKB1.640202.30.A8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTAAGCGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A8\tHiSeq4000\t\tA8\n1.SKB1.640202.30.A9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCTTGCA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_30_A9\tHiSeq4000\t\tA9\n1.SKB1.640202.33.A1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATTCTGGC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A1\tHiSeq4000\t\tA1\n1.SKB1.640202.33.A10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGATGTAG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A10\tHiSeq4000\t\tA10\n1.SKB1.640202.33.A11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAATCCGA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A11\tHiSeq4000\t\tA11\n1.SKB1.640202.33.A12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAGACGTG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A12\tHiSeq4000\t\tA12\n1.SKB1.640202.33.A2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTTCGTC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A2\tHiSeq4000\t\tA2\n1.SKB1.640202.33.A3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAGCGTCT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A3\tHiSeq4000\t\tA3\n1.SKB1.640202.33.A4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGGTCATA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A4\tHiSeq4000\t\tA4\n1.SKB1.640202.33.A5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGTGGTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A5\tHiSeq4000\t\tA5\n1.SKB1.640202.33.A6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTCTCGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A6\tHiSeq4000\t\tA6\n1.SKB1.640202.33.A7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTGTGTA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A7\tHiSeq4000\t\tA7\n1.SKB1.640202.33.A8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATTACCG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A8\tHiSeq4000\t\tA8\n1.SKB1.640202.33.A9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCGCCAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_33_A9\tHiSeq4000\t\tA9\n1.SKB2.640194.21.B1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGTGTTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B1\tHiSeq4000\t\tB1\n1.SKB2.640194.21.B10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTCATGG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B10\tHiSeq4000\t\tB10\n1.SKB2.640194.21.B11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACTTGCC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B11\tHiSeq4000\t\tB11\n1.SKB2.640194.21.B12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCGCATA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B12\tHiSeq4000\t\tB12\n1.SKB2.640194.21.B2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTATGCTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B2\tHiSeq4000\t\tB2\n1.SKB2.640194.21.B3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTGCGTT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B3\tHiSeq4000\t\tB3\n1.SKB2.640194.21.B4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAGTGACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B4\tHiSeq4000\t\tB4\n1.SKB2.640194.21.B5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGAAGGC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B5\tHiSeq4000\t\tB5\n1.SKB2.640194.21.B6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTATACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B6\tHiSeq4000\t\tB6\n1.SKB2.640194.21.B7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTCTCTCG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B7\tHiSeq4000\t\tB7\n1.SKB2.640194.21.B8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAACCGGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B8\tHiSeq4000\t\tB8\n1.SKB2.640194.21.B9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTTGACG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_B9\tHiSeq4000\t\tB9\n1.SKB2.640194.27.B1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCGTCTT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B1\tHiSeq4000\t\tB1\n1.SKB2.640194.27.B10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTGGATG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B10\tHiSeq4000\t\tB10\n1.SKB2.640194.27.B11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTACGGTTG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B11\tHiSeq4000\t\tB11\n1.SKB2.640194.27.B12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATGTGTG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B12\tHiSeq4000\t\tB12\n1.SKB2.640194.27.B2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTCGCTT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B2\tHiSeq4000\t\tB2\n1.SKB2.640194.27.B3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGCTTAAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B3\tHiSeq4000\t\tB3\n1.SKB2.640194.27.B4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGATAGAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B4\tHiSeq4000\t\tB4\n1.SKB2.640194.27.B5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTGGTAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B5\tHiSeq4000\t\tB5\n1.SKB2.640194.27.B6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTTGGCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B6\tHiSeq4000\t\tB6\n1.SKB2.640194.27.B7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTTATGC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B7\tHiSeq4000\t\tB7\n1.SKB2.640194.27.B8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCAAGGAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B8\tHiSeq4000\t\tB8\n1.SKB2.640194.27.B9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCATCTACG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_27_B9\tHiSeq4000\t\tB9\n1.SKB2.640194.30.B1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATTGCGTG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B1\tHiSeq4000\t\tB1\n1.SKB2.640194.30.B10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCGAACT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B10\tHiSeq4000\t\tB10\n1.SKB2.640194.30.B11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGTGACA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B11\tHiSeq4000\t\tB11\n1.SKB2.640194.30.B12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTAGCCA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B12\tHiSeq4000\t\tB12\n1.SKB2.640194.30.B2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGACAAGAG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B2\tHiSeq4000\t\tB2\n1.SKB2.640194.30.B3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGCAAGTT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B3\tHiSeq4000\t\tB3\n1.SKB2.640194.30.B4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCGGTGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B4\tHiSeq4000\t\tB4\n1.SKB2.640194.30.B5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCCAAGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B5\tHiSeq4000\t\tB5\n1.SKB2.640194.30.B6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGCTGTT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B6\tHiSeq4000\t\tB6\n1.SKB2.640194.30.B7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGCCAAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B7\tHiSeq4000\t\tB7\n1.SKB2.640194.30.B8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCTTGGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B8\tHiSeq4000\t\tB8\n1.SKB2.640194.30.B9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAAGTGCA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_30_B9\tHiSeq4000\t\tB9\n1.SKB2.640194.33.B1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTACCAGGA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B1\tHiSeq4000\t\tB1\n1.SKB2.640194.33.B10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTGTCAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B10\tHiSeq4000\t\tB10\n1.SKB2.640194.33.B11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGACGAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B11\tHiSeq4000\t\tB11\n1.SKB2.640194.33.B12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGAGCTAG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B12\tHiSeq4000\t\tB12\n1.SKB2.640194.33.B2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAATGCCG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B2\tHiSeq4000\t\tB2\n1.SKB2.640194.33.B3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGACGCAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B3\tHiSeq4000\t\tB3\n1.SKB2.640194.33.B4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTAGACG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B4\tHiSeq4000\t\tB4\n1.SKB2.640194.33.B5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGATACGC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B5\tHiSeq4000\t\tB5\n1.SKB2.640194.33.B6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCGATCG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B6\tHiSeq4000\t\tB6\n1.SKB2.640194.33.B7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGTCTGA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B7\tHiSeq4000\t\tB7\n1.SKB2.640194.33.B8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGATACG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B8\tHiSeq4000\t\tB8\n1.SKB2.640194.33.B9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTCGCAA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_33_B9\tHiSeq4000\t\tB9\n1.SKB3.640195.21.C1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGAGGTGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C1\tHiSeq4000\t\tC1\n1.SKB3.640195.21.C10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCTGTAAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C10\tHiSeq4000\t\tC10\n1.SKB3.640195.21.C11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAATGTGG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C11\tHiSeq4000\t\tC11\n1.SKB3.640195.21.C12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAAGTACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C12\tHiSeq4000\t\tC12\n1.SKB3.640195.21.C2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGATGTCC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C2\tHiSeq4000\t\tC2\n1.SKB3.640195.21.C3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAGTTGCG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C3\tHiSeq4000\t\tC3\n1.SKB3.640195.21.C4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGAGACTA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C4\tHiSeq4000\t\tC4\n1.SKB3.640195.21.C5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGGTTCGA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C5\tHiSeq4000\t\tC5\n1.SKB3.640195.21.C6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTAGGTCG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C6\tHiSeq4000\t\tC6\n1.SKB3.640195.21.C7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACGGTCA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C7\tHiSeq4000\t\tC7\n1.SKB3.640195.21.C8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCATGGAAC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C8\tHiSeq4000\t\tC8\n1.SKB3.640195.21.C9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTCTTGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_C9\tHiSeq4000\t\tC9\n1.SKB3.640195.27.C1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGAACTGT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C1\tHiSeq4000\t\tC1\n1.SKB3.640195.27.C10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGTTGGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C10\tHiSeq4000\t\tC10\n1.SKB3.640195.27.C11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGATACCA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C11\tHiSeq4000\t\tC11\n1.SKB3.640195.27.C12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTCTCGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C12\tHiSeq4000\t\tC12\n1.SKB3.640195.27.C2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGGCACTA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C2\tHiSeq4000\t\tC2\n1.SKB3.640195.27.C3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACCACTA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C3\tHiSeq4000\t\tC3\n1.SKB3.640195.27.C4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTCGTTGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C4\tHiSeq4000\t\tC4\n1.SKB3.640195.27.C5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGAACGAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C5\tHiSeq4000\t\tC5\n1.SKB3.640195.27.C6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCGGAATT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C6\tHiSeq4000\t\tC6\n1.SKB3.640195.27.C7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATACTGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C7\tHiSeq4000\t\tC7\n1.SKB3.640195.27.C8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCAACTGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C8\tHiSeq4000\t\tC8\n1.SKB3.640195.27.C9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCGTATCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_27_C9\tHiSeq4000\t\tC9\n1.SKB3.640195.30.C1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTAACGAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C1\tHiSeq4000\t\tC1\n1.SKB3.640195.30.C10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGACTTAGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C10\tHiSeq4000\t\tC10\n1.SKB3.640195.30.C11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGGTTCT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C11\tHiSeq4000\t\tC11\n1.SKB3.640195.30.C12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCAGGTA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C12\tHiSeq4000\t\tC12\n1.SKB3.640195.30.C2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAACACAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C2\tHiSeq4000\t\tC2\n1.SKB3.640195.30.C3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCATGTG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C3\tHiSeq4000\t\tC3\n1.SKB3.640195.30.C4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCTCCTA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C4\tHiSeq4000\t\tC4\n1.SKB3.640195.30.C5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGACTGAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C5\tHiSeq4000\t\tC5\n1.SKB3.640195.30.C6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACGTGGA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C6\tHiSeq4000\t\tC6\n1.SKB3.640195.30.C7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACGTTGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C7\tHiSeq4000\t\tC7\n1.SKB3.640195.30.C8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACACACTC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C8\tHiSeq4000\t\tC8\n1.SKB3.640195.30.C9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCCGAGTT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_30_C9\tHiSeq4000\t\tC9\n1.SKB3.640195.33.C1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTACATCGG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C1\tHiSeq4000\t\tC1\n1.SKB3.640195.33.C10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCTCATG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C10\tHiSeq4000\t\tC10\n1.SKB3.640195.33.C11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAAGTGGC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C11\tHiSeq4000\t\tC11\n1.SKB3.640195.33.C12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGACACA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C12\tHiSeq4000\t\tC12\n1.SKB3.640195.33.C2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGACCATT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C2\tHiSeq4000\t\tC2\n1.SKB3.640195.33.C3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCGTGTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C3\tHiSeq4000\t\tC3\n1.SKB3.640195.33.C4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTAACGC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C4\tHiSeq4000\t\tC4\n1.SKB3.640195.33.C5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCAGATG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C5\tHiSeq4000\t\tC5\n1.SKB3.640195.33.C6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTCAGTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C6\tHiSeq4000\t\tC6\n1.SKB3.640195.33.C7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAATCGTG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C7\tHiSeq4000\t\tC7\n1.SKB3.640195.33.C8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGACGTTA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C8\tHiSeq4000\t\tC8\n1.SKB3.640195.33.C9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACGACAGA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_33_C9\tHiSeq4000\t\tC9\n1.SKB4.640189.21.D1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATCCATG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D1\tHiSeq4000\t\tD1\n1.SKB4.640189.21.D10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCGAAGA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D10\tHiSeq4000\t\tD10\n1.SKB4.640189.21.D11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGGCTGA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D11\tHiSeq4000\t\tD11\n1.SKB4.640189.21.D12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGGTATC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D12\tHiSeq4000\t\tD12\n1.SKB4.640189.21.D2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCCTTCT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D2\tHiSeq4000\t\tD2\n1.SKB4.640189.21.D3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGAGCCA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D3\tHiSeq4000\t\tD3\n1.SKB4.640189.21.D4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGACATGGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D4\tHiSeq4000\t\tD4\n1.SKB4.640189.21.D5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCATGTTCC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D5\tHiSeq4000\t\tD5\n1.SKB4.640189.21.D6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCAAGATC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D6\tHiSeq4000\t\tD6\n1.SKB4.640189.21.D7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACAGACCT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D7\tHiSeq4000\t\tD7\n1.SKB4.640189.21.D8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGGTCCA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D8\tHiSeq4000\t\tD8\n1.SKB4.640189.21.D9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTGATCA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_D9\tHiSeq4000\t\tD9\n1.SKB4.640189.27.D1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCATTCGGT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D1\tHiSeq4000\t\tD1\n1.SKB4.640189.27.D10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATAGGCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D10\tHiSeq4000\t\tD10\n1.SKB4.640189.27.D11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGACATC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D11\tHiSeq4000\t\tD11\n1.SKB4.640189.27.D12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGTCTCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D12\tHiSeq4000\t\tD12\n1.SKB4.640189.27.D2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTTGTCA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D2\tHiSeq4000\t\tD2\n1.SKB4.640189.27.D3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACAGCAAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D3\tHiSeq4000\t\tD3\n1.SKB4.640189.27.D4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGGAGAGT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D4\tHiSeq4000\t\tD4\n1.SKB4.640189.27.D5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTCGTTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D5\tHiSeq4000\t\tD5\n1.SKB4.640189.27.D6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGTGAAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D6\tHiSeq4000\t\tD6\n1.SKB4.640189.27.D7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTACTTGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D7\tHiSeq4000\t\tD7\n1.SKB4.640189.27.D8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTTGATG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D8\tHiSeq4000\t\tD8\n1.SKB4.640189.27.D9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGGAATAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_27_D9\tHiSeq4000\t\tD9\n1.SKB4.640189.30.D1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTGCTGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D1\tHiSeq4000\t\tD1\n1.SKB4.640189.30.D10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACACCAGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D10\tHiSeq4000\t\tD10\n1.SKB4.640189.30.D11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTGTGTC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D11\tHiSeq4000\t\tD11\n1.SKB4.640189.30.D12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTAGGTGA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D12\tHiSeq4000\t\tD12\n1.SKB4.640189.30.D2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCTTAGCT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D2\tHiSeq4000\t\tD2\n1.SKB4.640189.30.D3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAACGGAT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D3\tHiSeq4000\t\tD3\n1.SKB4.640189.30.D4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTTGATC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D4\tHiSeq4000\t\tD4\n1.SKB4.640189.30.D5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACCTGTT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D5\tHiSeq4000\t\tD5\n1.SKB4.640189.30.D6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACGACGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D6\tHiSeq4000\t\tD6\n1.SKB4.640189.30.D7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTATTCCGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D7\tHiSeq4000\t\tD7\n1.SKB4.640189.30.D8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCACTTCT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D8\tHiSeq4000\t\tD8\n1.SKB4.640189.30.D9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCTAAGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_30_D9\tHiSeq4000\t\tD9\n1.SKB4.640189.33.D1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGGTGTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D1\tHiSeq4000\t\tD1\n1.SKB4.640189.33.D10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGAAGACG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D10\tHiSeq4000\t\tD10\n1.SKB4.640189.33.D11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTGAGGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D11\tHiSeq4000\t\tD11\n1.SKB4.640189.33.D12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACGGTCTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D12\tHiSeq4000\t\tD12\n1.SKB4.640189.33.D2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGAAGCT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D2\tHiSeq4000\t\tD2\n1.SKB4.640189.33.D3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCACCAA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D3\tHiSeq4000\t\tD3\n1.SKB4.640189.33.D4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATAGCGGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D4\tHiSeq4000\t\tD4\n1.SKB4.640189.33.D5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCAGTGTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D5\tHiSeq4000\t\tD5\n1.SKB4.640189.33.D6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTGCTAG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D6\tHiSeq4000\t\tD6\n1.SKB4.640189.33.D7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCGATAGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D7\tHiSeq4000\t\tD7\n1.SKB4.640189.33.D8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGATGTC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D8\tHiSeq4000\t\tD8\n1.SKB4.640189.33.D9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTACGGCT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_33_D9\tHiSeq4000\t\tD9\n1.SKB5.640181.21.E1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCCTATCA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E1\tHiSeq4000\t\tE1\n1.SKB5.640181.21.E10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGCTCAA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E10\tHiSeq4000\t\tE10\n1.SKB5.640181.21.E11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTACCGAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E11\tHiSeq4000\t\tE11\n1.SKB5.640181.21.E12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTCTAGG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E12\tHiSeq4000\t\tE12\n1.SKB5.640181.21.E2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATAAGGCG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E2\tHiSeq4000\t\tE2\n1.SKB5.640181.21.E3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACAGCTCA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E3\tHiSeq4000\t\tE3\n1.SKB5.640181.21.E4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCATGTCT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E4\tHiSeq4000\t\tE4\n1.SKB5.640181.21.E5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGCCATA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E5\tHiSeq4000\t\tE5\n1.SKB5.640181.21.E6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGAGCCTT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E6\tHiSeq4000\t\tE6\n1.SKB5.640181.21.E7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTCTTCC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E7\tHiSeq4000\t\tE7\n1.SKB5.640181.21.E8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTCTGAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E8\tHiSeq4000\t\tE8\n1.SKB5.640181.21.E9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCAAGTTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_E9\tHiSeq4000\t\tE9\n1.SKB5.640181.27.E1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGGTTAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E1\tHiSeq4000\t\tE1\n1.SKB5.640181.27.E10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGACAGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E10\tHiSeq4000\t\tE10\n1.SKB5.640181.27.E11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTGTAGC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E11\tHiSeq4000\t\tE11\n1.SKB5.640181.27.E12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAACACCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E12\tHiSeq4000\t\tE12\n1.SKB5.640181.27.E2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACCTCCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E2\tHiSeq4000\t\tE2\n1.SKB5.640181.27.E3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGAAGGAT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E3\tHiSeq4000\t\tE3\n1.SKB5.640181.27.E4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCAGACGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E4\tHiSeq4000\t\tE4\n1.SKB5.640181.27.E5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCAATAGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E5\tHiSeq4000\t\tE5\n1.SKB5.640181.27.E6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTACTGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E6\tHiSeq4000\t\tE6\n1.SKB5.640181.27.E7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCATACCAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E7\tHiSeq4000\t\tE7\n1.SKB5.640181.27.E8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGGACAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E8\tHiSeq4000\t\tE8\n1.SKB5.640181.27.E9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCCTAGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_27_E9\tHiSeq4000\t\tE9\n1.SKB5.640181.30.E1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTGTTCG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E1\tHiSeq4000\t\tE1\n1.SKB5.640181.30.E10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTGATTG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E10\tHiSeq4000\t\tE10\n1.SKB5.640181.30.E11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCATACGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E11\tHiSeq4000\t\tE11\n1.SKB5.640181.30.E12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCCATGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E12\tHiSeq4000\t\tE12\n1.SKB5.640181.30.E2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAAGGAAG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E2\tHiSeq4000\t\tE2\n1.SKB5.640181.30.E3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAATCGAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E3\tHiSeq4000\t\tE3\n1.SKB5.640181.30.E4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCATTCAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E4\tHiSeq4000\t\tE4\n1.SKB5.640181.30.E5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCCGGTA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E5\tHiSeq4000\t\tE5\n1.SKB5.640181.30.E6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACAGGAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E6\tHiSeq4000\t\tE6\n1.SKB5.640181.30.E7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCTTCCA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E7\tHiSeq4000\t\tE7\n1.SKB5.640181.30.E8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGGTCTC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E8\tHiSeq4000\t\tE8\n1.SKB5.640181.30.E9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGGACGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_30_E9\tHiSeq4000\t\tE9\n1.SKB5.640181.33.E1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGCATGAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E1\tHiSeq4000\t\tE1\n1.SKB5.640181.33.E10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTACGCA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E10\tHiSeq4000\t\tE10\n1.SKB5.640181.33.E11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTACCGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E11\tHiSeq4000\t\tE11\n1.SKB5.640181.33.E12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCTGTTGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E12\tHiSeq4000\t\tE12\n1.SKB5.640181.33.E2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGAGGCA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E2\tHiSeq4000\t\tE2\n1.SKB5.640181.33.E3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCACACG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E3\tHiSeq4000\t\tE3\n1.SKB5.640181.33.E4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGACCTAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E4\tHiSeq4000\t\tE4\n1.SKB5.640181.33.E5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATTCCTCC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E5\tHiSeq4000\t\tE5\n1.SKB5.640181.33.E6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCCGTGAA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E6\tHiSeq4000\t\tE6\n1.SKB5.640181.33.E7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGCTATTG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E7\tHiSeq4000\t\tE7\n1.SKB5.640181.33.E8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATTGGAG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E8\tHiSeq4000\t\tE8\n1.SKB5.640181.33.E9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGGACTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_33_E9\tHiSeq4000\t\tE9\n1.SKB6.640176.21.F1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACAACCG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F1\tHiSeq4000\t\tF1\n1.SKB6.640176.21.F10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGAACCTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F10\tHiSeq4000\t\tF10\n1.SKB6.640176.21.F11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCCTAAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F11\tHiSeq4000\t\tF11\n1.SKB6.640176.21.F12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGCACTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F12\tHiSeq4000\t\tF12\n1.SKB6.640176.21.F2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTACCTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F2\tHiSeq4000\t\tF2\n1.SKB6.640176.21.F3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTAAGGC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F3\tHiSeq4000\t\tF3\n1.SKB6.640176.21.F4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTCCATC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F4\tHiSeq4000\t\tF4\n1.SKB6.640176.21.F5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTTGTAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F5\tHiSeq4000\t\tF5\n1.SKB6.640176.21.F6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCAATGGA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F6\tHiSeq4000\t\tF6\n1.SKB6.640176.21.F7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTGTTGG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F7\tHiSeq4000\t\tF7\n1.SKB6.640176.21.F8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACCGAAG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F8\tHiSeq4000\t\tF8\n1.SKB6.640176.21.F9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTACCTTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F9\tHiSeq4000\t\tF9\n1.SKB6.640176.27.F1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGTCGAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F1\tHiSeq4000\t\tF1\n1.SKB6.640176.27.F10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGAATGCC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F10\tHiSeq4000\t\tF10\n1.SKB6.640176.27.F11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATACGACC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F11\tHiSeq4000\t\tF11\n1.SKB6.640176.27.F12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGTCTTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F12\tHiSeq4000\t\tF12\n1.SKB6.640176.27.F2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGACCAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F2\tHiSeq4000\t\tF2\n1.SKB6.640176.27.F3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGCGTTAT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F3\tHiSeq4000\t\tF3\n1.SKB6.640176.27.F4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGACGAATG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F4\tHiSeq4000\t\tF4\n1.SKB6.640176.27.F5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCATCCA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F5\tHiSeq4000\t\tF5\n1.SKB6.640176.27.F6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTGAAGC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F6\tHiSeq4000\t\tF6\n1.SKB6.640176.27.F7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACATTGCG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F7\tHiSeq4000\t\tF7\n1.SKB6.640176.27.F8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGATCCG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F8\tHiSeq4000\t\tF8\n1.SKB6.640176.27.F9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGGTAGCT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_27_F9\tHiSeq4000\t\tF9\n1.SKB6.640176.30.F1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTTGAGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F1\tHiSeq4000\t\tF1\n1.SKB6.640176.30.F10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGTGTGC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F10\tHiSeq4000\t\tF10\n1.SKB6.640176.30.F11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTACTAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F11\tHiSeq4000\t\tF11\n1.SKB6.640176.30.F12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTACAGC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F12\tHiSeq4000\t\tF12\n1.SKB6.640176.30.F2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGTTCTG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F2\tHiSeq4000\t\tF2\n1.SKB6.640176.30.F3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGTTCCT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F3\tHiSeq4000\t\tF3\n1.SKB6.640176.30.F4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGACAATC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F4\tHiSeq4000\t\tF4\n1.SKB6.640176.30.F5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCTGTCC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F5\tHiSeq4000\t\tF5\n1.SKB6.640176.30.F6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGCGCAT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F6\tHiSeq4000\t\tF6\n1.SKB6.640176.30.F7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCTAGGT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F7\tHiSeq4000\t\tF7\n1.SKB6.640176.30.F8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCATCAG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F8\tHiSeq4000\t\tF8\n1.SKB6.640176.30.F9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATAGCGA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_30_F9\tHiSeq4000\t\tF9\n1.SKB6.640176.33.F1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTCGACA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F1\tHiSeq4000\t\tF1\n1.SKB6.640176.33.F10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTCAGAC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F10\tHiSeq4000\t\tF10\n1.SKB6.640176.33.F11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCAAGCA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F11\tHiSeq4000\t\tF11\n1.SKB6.640176.33.F12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACTAGCT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F12\tHiSeq4000\t\tF12\n1.SKB6.640176.33.F2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATCGAGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F2\tHiSeq4000\t\tF2\n1.SKB6.640176.33.F3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGCCTGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F3\tHiSeq4000\t\tF3\n1.SKB6.640176.33.F4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGATGCTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F4\tHiSeq4000\t\tF4\n1.SKB6.640176.33.F5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTAACTCG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F5\tHiSeq4000\t\tF5\n1.SKB6.640176.33.F6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGATTCGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F6\tHiSeq4000\t\tF6\n1.SKB6.640176.33.F7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGTTACGG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F7\tHiSeq4000\t\tF7\n1.SKB6.640176.33.F8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCAATTCG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F8\tHiSeq4000\t\tF8\n1.SKB6.640176.33.F9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGCATACT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_33_F9\tHiSeq4000\t\tF9\nblank.21.H1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTATGGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H1\tHiSeq4000\t\tH1\nblank.21.H10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCTAACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H10\tHiSeq4000\t\tH10\nblank.21.H11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAAGAGGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H11\tHiSeq4000\t\tH11\nblank.21.H2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATTCAGC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H2\tHiSeq4000\t\tH2\nblank.21.H3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACACGGTT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H3\tHiSeq4000\t\tH3\nblank.21.H4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGAAGAAC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H4\tHiSeq4000\t\tH4\nblank.21.H5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAACGAGG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H5\tHiSeq4000\t\tH5\nblank.21.H6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAACATCG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H6\tHiSeq4000\t\tH6\nblank.21.H7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGAAGCGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H7\tHiSeq4000\t\tH7\nblank.21.H8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGTTAGG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H8\tHiSeq4000\t\tH8\nblank.21.H9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGGATCAC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H9\tHiSeq4000\t\tH9\nblank.27.H1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTATTCGCC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H1\tHiSeq4000\t\tH1\nblank.27.H10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCATGGTG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H10\tHiSeq4000\t\tH10\nblank.27.H11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGCAGAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H11\tHiSeq4000\t\tH11\nblank.27.H2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCCAATCG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H2\tHiSeq4000\t\tH2\nblank.27.H3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCATCGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H3\tHiSeq4000\t\tH3\nblank.27.H4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGGTTGTT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H4\tHiSeq4000\t\tH4\nblank.27.H5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTTGTCGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H5\tHiSeq4000\t\tH5\nblank.27.H6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTCAGGAG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H6\tHiSeq4000\t\tH6\nblank.27.H7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGTGTCG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H7\tHiSeq4000\t\tH7\nblank.27.H8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATTGCTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H8\tHiSeq4000\t\tH8\nblank.27.H9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACATAGGC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_27_H9\tHiSeq4000\t\tH9\nblank.30.H1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGACCGTA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H1\tHiSeq4000\t\tH1\nblank.30.H10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATTCGAGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H10\tHiSeq4000\t\tH10\nblank.30.H11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGTAGTC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H11\tHiSeq4000\t\tH11\nblank.30.H2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTAGCATC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H2\tHiSeq4000\t\tH2\nblank.30.H3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCTTCTC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H3\tHiSeq4000\t\tH3\nblank.30.H4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCCATAAC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H4\tHiSeq4000\t\tH4\nblank.30.H5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGGCGAA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H5\tHiSeq4000\t\tH5\nblank.30.H6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGGTCACT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H6\tHiSeq4000\t\tH6\nblank.30.H7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGCAATCT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H7\tHiSeq4000\t\tH7\nblank.30.H8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACCTTGG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H8\tHiSeq4000\t\tH8\nblank.30.H9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACTGGTG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_30_H9\tHiSeq4000\t\tH9\nblank.33.H1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGACATTCC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H1\tHiSeq4000\t\tH1\nblank.33.H10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGCTAGTA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H10\tHiSeq4000\t\tH10\nblank.33.H11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAAGGTCT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H11\tHiSeq4000\t\tH11\nblank.33.H2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGTCCGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H2\tHiSeq4000\t\tH2\nblank.33.H3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCTTCGAA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H3\tHiSeq4000\t\tH3\nblank.33.H4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGAAGTG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H4\tHiSeq4000\t\tH4\nblank.33.H5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCAGGCTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H5\tHiSeq4000\t\tH5\nblank.33.H6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGTGGAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H6\tHiSeq4000\t\tH6\nblank.33.H7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCACGAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H7\tHiSeq4000\t\tH7\nblank.33.H8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGCACGA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H8\tHiSeq4000\t\tH8\nblank.33.H9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATATGCGC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tblank_33_H9\tHiSeq4000\t\tH9\nvibrio.positive.control.21.G1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACTCGTTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G1\tHiSeq4000\t\tG1\nvibrio.positive.control.21.G10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCGACTAT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G10\tHiSeq4000\t\tG10\nvibrio.positive.control.21.G11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAAGGTTC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G11\tHiSeq4000\t\tG11\nvibrio.positive.control.21.G12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCAAGCAA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G12\tHiSeq4000\t\tG12\nvibrio.positive.control.21.G2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTTGCAA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G2\tHiSeq4000\t\tG2\nvibrio.positive.control.21.G3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGCCACA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G3\tHiSeq4000\t\tG3\nvibrio.positive.control.21.G4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGTGACTG\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G4\tHiSeq4000\t\tG4\nvibrio.positive.control.21.G5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGCTGGATT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G5\tHiSeq4000\t\tG5\nvibrio.positive.control.21.G6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGGAGTA\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G6\tHiSeq4000\t\tG6\nvibrio.positive.control.21.G7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGGCATGT\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G7\tHiSeq4000\t\tG7\nvibrio.positive.control.21.G8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTCGTACC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G8\tHiSeq4000\t\tG8\nvibrio.positive.control.21.G9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGACTATGC\t\tKF1\t\tTest plate 1\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G9\tHiSeq4000\t\tG9\nvibrio.positive.control.27.G1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTATCGGTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G1\tHiSeq4000\t\tG1\nvibrio.positive.control.27.G10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTACATCC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G10\tHiSeq4000\t\tG10\nvibrio.positive.control.27.G11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTCCAAGG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G11\tHiSeq4000\t\tG11\nvibrio.positive.control.27.G12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGACTGTT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G12\tHiSeq4000\t\tG12\nvibrio.positive.control.27.G2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAACCGTTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G2\tHiSeq4000\t\tG2\nvibrio.positive.control.27.G3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTGTTGAC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G3\tHiSeq4000\t\tG3\nvibrio.positive.control.27.G4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCATGAGGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G4\tHiSeq4000\t\tG4\nvibrio.positive.control.27.G5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACACATG\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G5\tHiSeq4000\t\tG5\nvibrio.positive.control.27.G6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCTGATC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G6\tHiSeq4000\t\tG6\nvibrio.positive.control.27.G7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGATCGGA\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G7\tHiSeq4000\t\tG7\nvibrio.positive.control.27.G8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTGATTC\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G8\tHiSeq4000\t\tG8\nvibrio.positive.control.27.G9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGAAGGT\t\tKF1\t\tTest plate 2\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_27_G9\tHiSeq4000\t\tG9\nvibrio.positive.control.30.G1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGAACCA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G1\tHiSeq4000\t\tG1\nvibrio.positive.control.30.G10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTACCACAG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G10\tHiSeq4000\t\tG10\nvibrio.positive.control.30.G11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGTCCAA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G11\tHiSeq4000\t\tG11\nvibrio.positive.control.30.G12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTATTCG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G12\tHiSeq4000\t\tG12\nvibrio.positive.control.30.G2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGGAGAT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G2\tHiSeq4000\t\tG2\nvibrio.positive.control.30.G3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGGAACCT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G3\tHiSeq4000\t\tG3\nvibrio.positive.control.30.G4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGGCGTT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G4\tHiSeq4000\t\tG4\nvibrio.positive.control.30.G5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCAAGACT\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G5\tHiSeq4000\t\tG5\nvibrio.positive.control.30.G6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCACTGACA\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G6\tHiSeq4000\t\tG6\nvibrio.positive.control.30.G7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTCAACC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G7\tHiSeq4000\t\tG7\nvibrio.positive.control.30.G8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGACGTC\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G8\tHiSeq4000\t\tG8\nvibrio.positive.control.30.G9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGGTGAG\t\tKF1\t\tTest plate 3\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_30_G9\tHiSeq4000\t\tG9\nvibrio.positive.control.33.G1\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGAGCTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G1\tHiSeq4000\t\tG1\nvibrio.positive.control.33.G10\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCCACAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G10\tHiSeq4000\t\tG10\nvibrio.positive.control.33.G11\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTCGTGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G11\tHiSeq4000\t\tG11\nvibrio.positive.control.33.G12\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGGTACAG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G12\tHiSeq4000\t\tG12\nvibrio.positive.control.33.G2\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATACTCCG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G2\tHiSeq4000\t\tG2\nvibrio.positive.control.33.G3\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACCTGACT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G3\tHiSeq4000\t\tG3\nvibrio.positive.control.33.G4\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGCTTGT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G4\tHiSeq4000\t\tG4\nvibrio.positive.control.33.G5\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATGAGAC\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G5\tHiSeq4000\t\tG5\nvibrio.positive.control.33.G6\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTCAGAT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G6\tHiSeq4000\t\tG6\nvibrio.positive.control.33.G7\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTACGAA\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G7\tHiSeq4000\t\tG7\nvibrio.positive.control.33.G8\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTCAATG\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G8\tHiSeq4000\t\tG8\nvibrio.positive.control.33.G9\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTAGGTT\t\tKF1\t\tTest plate 4\tHiSeq4000\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_33_G9\tHiSeq4000\t\tG9\n'

if __name__ == '__main__':
    main()
