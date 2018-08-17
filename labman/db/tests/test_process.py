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
        obs = SampleComposition(85)

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
        obs = SampleComposition(85)

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
        self.assertEqual(tester.sample_plate, Plate(21))
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
        self.assertEqual(tester.gdna_plates, [Plate(22), Plate(22), Plate(22),
                                              Plate(22)])

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
        self.assertEqual(tester.gdna_plate, Plate(22))
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
        obs = NormalizationProcess(1).generate_echo_picklist()
        obs_lines = obs.splitlines()
        self.assertEqual(
            obs_lines[0],
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Concentration\tTransfer Volume\tDestination Plate Name'
            '\tDestination Well')
        self.assertEqual(
            obs_lines[1],
            '1.SKB1.640202.21.A1\tWater\t384PP_AQ_BP2_HT\tA1\t12.068\t3085.0'
            '\tNormalizedDNA\tA1')
        self.assertEqual(
            obs_lines[380],
            'blank.21.H11\tWater\t384PP_AQ_BP2_HT\tP22\t0.342\t0.0\t'
            'NormalizedDNA\tP22')
        self.assertEqual(
            obs_lines[381],
            '1.SKB1.640202.21.A1\tSample\t384PP_AQ_BP2_HT\tA1\t12.068\t415.0'
            '\tNormalizedDNA\tA1')
        self.assertEqual(
            obs_lines[-1],
            'blank.21.H11\tSample\t384PP_AQ_BP2_HT\tP22\t0.342\t3500.0\t'
            'NormalizedDNA\tP22')


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
        self.assertEqual(len(obs), 95)
        self.assertEqual(obs[0],
                         (LibraryPrep16SComposition(1), 20.0, 60.606))
        self.assertEqual(obs[36],
                         (LibraryPrep16SComposition(37), 20.0, 60.606))
        self.assertEqual(obs[94],
                         (LibraryPrep16SComposition(95), 1.0, 3.0303))

        tester = QuantificationProcess(4)
        self.assertEqual(tester.date,
                         _help_make_datetime('2017-10-25 19:10:25-0700'))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 22)
        self.assertEqual(tester.notes,None)
        obs = tester.concentrations
        self.assertEqual(len(obs), 380)
        self.assertEqual(
            obs[0], (LibraryPrepShotgunComposition(1), 12.068, 36.569))
        self.assertEqual(
            obs[296], (LibraryPrepShotgunComposition(297), 8.904, 26.981))
        self.assertEqual(
            obs[379], (LibraryPrepShotgunComposition(380), 0.342, 1.036))

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
            obs[296], (LibraryPrepShotgunComposition(297), 9.904, 28.981))
        self.assertEqual(
            obs[379], (LibraryPrepShotgunComposition(380), 1.342, 3.036))

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
        self.assertEqual(obs_c[12][0], LibraryPrep16SComposition(13))
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
            'blank.21.H11\tiTru 7 primer\t384LDV_AQ_B2_HT\tP16\t250\t'
            'iTru7_115_08\tTGGTACAG\tIndexPCRPlate\tP22')


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
        self.assertEqual(obs_lines[-1], '1,H11,1,1,1.000,1')

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
            'Test shotgun library plate 1,A1,iTru7_101_01,ACGTTACC,iTru5_01_A,'
            'TTGTCGGT,LabDude_PIDude_1,1.SKB1.640202.21.A1']
        self.assertEqual(obs[:len(exp)], exp)
        exp = ('1,vibrio_positive_control_21_G9,vibrio_positive_control_21_G9,'
               'Test shotgun library plate 1,N18,iTru7_303_12,GATGAGAC,'
               'iTru5_124_C,GATGAGAC,Controls,'
               'vibrio.positive.control.21.G9')
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
TARGET_EXAMPLE = 'sample_name\tBARCODE\tPRIMER\tPrimer_Plate\tWell_ID\tPlating\tExtractionKit_lot\tExtraction_robot\tTM1000_8_tool\tPrimer_date\tMasterMix_lot\tWater_Lot\tProcessing_robot\tTM300_8_tool\tTM50_8_tool\tSample_Plate\tProject_name\tOrig_name\tWell_description\tEXPERIMENT_DESIGN_DESCRIPTION\tLIBRARY_CONSTRUCTION_PROTOCOL\tLINKER\tPLATFORM\tRUN_CENTER\tRUN_DATE\tRUN_PREFIX\tpcr_primers\tsequencing_meth\ttarget_gene\ttarget_subfragment\tcenter_name\tcenter_project_name\tINSTRUMENT_MODEL\tRUNID\n1.SKB1.640202\tCGGTCAATTGAC\tGTGTGYCAGCMGCCGCGGTAA\t1\tF1\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB1.640202\tTest plate 1_1.SKB1.640202_F1\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB2.640194\tGTGGAGTCTCAT\tGTGTGYCAGCMGCCGCGGTAA\t1\tF2\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB2.640194\tTest plate 1_1.SKB2.640194_F2\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB3.640195\tGCTCGAAGATTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tF3\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB3.640195\tTest plate 1_1.SKB3.640195_F3\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB4.640189\tAGGCTTACGTGT\tGTGTGYCAGCMGCCGCGGTAA\t1\tF4\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB4.640189\tTest plate 1_1.SKB4.640189_F4\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB5.640181\tTCTCTACCACTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tF5\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB5.640181\tTest plate 1_1.SKB5.640181_F5\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB6.640176\tACTTCCAACTTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tF6\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB6.640176\tTest plate 1_1.SKB6.640176_F6\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB7.640196\tCTCACCTAGGAA\tGTGTGYCAGCMGCCGCGGTAA\t1\tF7\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB7.640196\tTest plate 1_1.SKB7.640196_F7\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB8.640193\tGTGTTGTCGTGC\tGTGTGYCAGCMGCCGCGGTAA\t1\tF8\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB8.640193\tTest plate 1_1.SKB8.640193_F8\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKB9.640200\tCCACAGATCGAT\tGTGTGYCAGCMGCCGCGGTAA\t1\tF9\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKB9.640200\tTest plate 1_1.SKB9.640200_F9\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKD1.640179\tTATCGACACAAG\tGTGTGYCAGCMGCCGCGGTAA\t1\tF10\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKD1.640179\tTest plate 1_1.SKD1.640179_F10\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKD2.640178\tGATTCCGGCTCA\tGTGTGYCAGCMGCCGCGGTAA\t1\tF11\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKD2.640178\tTest plate 1_1.SKD2.640178_F11\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n1.SKD3.640198\tCGTAATTGCCGC\tGTGTGYCAGCMGCCGCGGTAA\t1\tF12\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t1.SKD3.640198\tTest plate 1_1.SKD3.640198_F12\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H1\tCGTAAGATGCCT\tGTGTGYCAGCMGCCGCGGTAA\t1\tH1\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H1\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H10\tTGGAGTAGGTGG\tGTGTGYCAGCMGCCGCGGTAA\t1\tH10\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H10\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H11\tTTGGCTCTATTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tH11\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H11\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H2\tGCGTTCTAGCTG\tGTGTGYCAGCMGCCGCGGTAA\t1\tH2\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H2\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H3\tGTTGTTCTGGGA\tGTGTGYCAGCMGCCGCGGTAA\t1\tH3\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H3\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H4\tGGACTTCCAGCT\tGTGTGYCAGCMGCCGCGGTAA\t1\tH4\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H4\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H5\tCTCACAACCGTG\tGTGTGYCAGCMGCCGCGGTAA\t1\tH5\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H5\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H6\tCTGCTATTCCTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tH6\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H6\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H7\tATGTCACCGCTG\tGTGTGYCAGCMGCCGCGGTAA\t1\tH7\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H7\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H8\tTGTAACGCCGAT\tGTGTGYCAGCMGCCGCGGTAA\t1\tH8\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H8\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nblank.21.H9\tAGCAGAACATCT\tGTGTGYCAGCMGCCGCGGTAA\t1\tH9\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_H9\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G1\tGGTGACTAGTTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tG1\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G1\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G10\tTGCGCTGAATGT\tGTGTGYCAGCMGCCGCGGTAA\t1\tG10\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G10\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G11\tATGGCTGTCAGT\tGTGTGYCAGCMGCCGCGGTAA\t1\tG11\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G11\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G12\tGTTCTCTTCTCG\tGTGTGYCAGCMGCCGCGGTAA\t1\tG12\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G12\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G2\tATGGGTTCCGTC\tGTGTGYCAGCMGCCGCGGTAA\t1\tG2\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G2\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G3\tTAGGCATGCTTG\tGTGTGYCAGCMGCCGCGGTAA\t1\tG3\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G3\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G4\tAACTAGTTCAGG\tGTGTGYCAGCMGCCGCGGTAA\t1\tG4\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G4\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G5\tATTCTGCCGAAG\tGTGTGYCAGCMGCCGCGGTAA\t1\tG5\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G5\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G6\tAGCATGTCCCGT\tGTGTGYCAGCMGCCGCGGTAA\t1\tG6\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G6\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G7\tGTACGATATGAC\tGTGTGYCAGCMGCCGCGGTAA\t1\tG7\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G7\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G8\tGTGGTGGTTTCC\tGTGTGYCAGCMGCCGCGGTAA\t1\tG8\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G8\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\nvibrio.positive.control.21.G9\tTAGTATGCGCAA\tGTGTGYCAGCMGCCGCGGTAA\t1\tG9\ttest@foo.bar\t157022406\tJER-E_KF1\t108379Z\t2017-10-25 20:10:25-06:00\t443912\tRNBF7110\tLUCY\t109375A\t311411B\tTest plate 1\tTestExperiment1\t\tTest plate 1_None_G9\t\tIllumina EMP protocol 515fbc, 806r amplification of 16S rRNA V4\tGT\tIllumina\tUCSDMI\t\t\tFWD:GTGYCAGCMGCCGCGGTAA; REV:GGACTACNVGGGTWTCTAAT\tSequencing by synthesis\t16S rRNA\tV4\tUCSDMI\t\t\t\n'

SHOTGUN_EXAMPLE = 'sample_name\tPrimer_date\tcenter_project_name\tepmotion_tool\texperiment\textraction_kit\tfwd_cycles\tgdata_robot\ti5_sequence\tinstrument_model\tkappa_hyper_plus_kit\tkingfisher_robot\tnormalization_water_lot\tplate\tplatform\tplatform_id\tprincipal_investigator\trev_cycles\trun_name\trun_prefix\tsequencer_description\tstub_lot\twell_id\n1.SKB1.640202\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCTAGGT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB1_640202_21_F1\tHiSeq4000\t\tF1\n1.SKB2.640194\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCTTGGT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB2_640194_21_F2\tHiSeq4000\t\tF2\n1.SKB3.640195\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCTCATCAG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB3_640195_21_F3\tHiSeq4000\t\tF3\n1.SKB4.640189\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATGACGTC\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB4_640189_21_F4\tHiSeq4000\t\tF4\n1.SKB5.640181\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGGACGT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB5_640181_21_F5\tHiSeq4000\t\tF5\n1.SKB6.640176\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAGCCGAA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB6_640176_21_F6\tHiSeq4000\t\tF6\n1.SKB7.640196\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTGTGTGC\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB7_640196_21_F7\tHiSeq4000\t\tF7\n1.SKB8.640193\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGTGACA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB8_640193_21_F8\tHiSeq4000\t\tF8\n1.SKB9.640200\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGGTACTAC\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKB9_640200_21_F9\tHiSeq4000\t\tF9\n1.SKD1.640179\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCAGTCCAA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKD1_640179_21_F10\tHiSeq4000\t\tF10\n1.SKD2.640178\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGCAGGTA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKD2_640178_21_F11\tHiSeq4000\t\tF11\n1.SKD3.640198\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATTCTGGC\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\t1_SKD3_640198_21_F12\tHiSeq4000\t\tF12\nblank.21.H1\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTACGAA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H1\tHiSeq4000\t\tH1\nblank.21.H10\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTGAGCTAG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H10\tHiSeq4000\t\tH10\nblank.21.H11\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tACGGTCTT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H11\tHiSeq4000\t\tH11\nblank.21.H2\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGACGTTA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H2\tHiSeq4000\t\tH2\nblank.21.H3\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGTCAATG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H3\tHiSeq4000\t\tH3\nblank.21.H4\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCGCCAT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H4\tHiSeq4000\t\tH4\nblank.21.H5\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTTACGGCT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H5\tHiSeq4000\t\tH5\nblank.21.H6\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCCTGTCAT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H6\tHiSeq4000\t\tH6\nblank.21.H7\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTCCACAT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H7\tHiSeq4000\t\tH7\nblank.21.H8\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTAAGTGGC\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H8\tHiSeq4000\t\tH8\nblank.21.H9\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCTCGTGT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tblank_21_H9\tHiSeq4000\t\tH9\nvibrio.positive.control.21.G1\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTGAGCTT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G1\tHiSeq4000\t\tG1\nvibrio.positive.control.21.G10\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCGATCG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G10\tHiSeq4000\t\tG10\nvibrio.positive.control.21.G11\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCCGTGAA\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G11\tHiSeq4000\t\tG11\nvibrio.positive.control.21.G12\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tTCGTGGAT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G12\tHiSeq4000\t\tG12\nvibrio.positive.control.21.G2\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tCGACCATT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G2\tHiSeq4000\t\tG2\nvibrio.positive.control.21.G3\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATACTCCG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G3\tHiSeq4000\t\tG3\nvibrio.positive.control.21.G4\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAAGTCCGT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G4\tHiSeq4000\t\tG4\nvibrio.positive.control.21.G5\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tATCACACG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G5\tHiSeq4000\t\tG5\nvibrio.positive.control.21.G6\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGTTAGACG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G6\tHiSeq4000\t\tG6\nvibrio.positive.control.21.G7\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGAGCTTGT\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G7\tHiSeq4000\t\tG7\nvibrio.positive.control.21.G8\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tAGCAGATG\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G8\tHiSeq4000\t\tG8\nvibrio.positive.control.21.G9\t2017-10-25 20:10:25-06:00\tTestExperimentShotgun1\t108379Z\tTestExperimentShotgun1\t157022406\t151\tLUCY\tGATGAGAC\t\t\tKF1\t\tTest plate 1\tIllumina\t19\ttest@foo.bar\t151\tTestShotgunRun1\tvibrio_positive_control_21_G9\tHiSeq4000\t\tG9\n'

if __name__ == '__main__':
    main()
