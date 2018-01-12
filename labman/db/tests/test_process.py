# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from datetime import date
from io import StringIO

import numpy as np
import numpy.testing as npt
import pandas as pd

from labman.db.testing import LabmanTestCase
from labman.db.container import Tube, Well
from labman.db.composition import (
    ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition, Composition, PoolComposition)
from labman.db.user import User
from labman.db.plate import Plate, PlateConfiguration
from labman.db.equipment import Equipment
from labman.db.process import (
    Process, SamplePlatingProcess, ReagentCreationProcess,
    PrimerWorkingPlateCreationProcess, GDNAExtractionProcess,
    LibraryPrep16SProcess, QuantificationProcess, PoolingProcess,
    SequencingProcess, GDNAPlateCompressionProcess)
# NormalizationProcess, LibraryPrepShotgunProcess


class TestProcess(LabmanTestCase):
    def test_factory(self):
        self.assertEqual(Process.factory(6),
                         SamplePlatingProcess(6))
        self.assertEqual(Process.factory(2),
                         PrimerWorkingPlateCreationProcess(1))
        self.assertEqual(Process.factory(7),
                         GDNAExtractionProcess(1))
        self.assertEqual(Process.factory(8),
                         LibraryPrep16SProcess(1))
        self.assertEqual(Process.factory(9),
                         QuantificationProcess(1))
        self.assertEqual(Process.factory(10), PoolingProcess(1))
        # self.assertEqual(Process.factory(),
        #                  NormalizationProcess())
        # self.assertEqual(Process.factory(),
        #                  LibraryPrepShotgunProcess())


class TestSamplePlatingProcess(LabmanTestCase):
    def test_attributes(self):
        tester = SamplePlatingProcess(6)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 6)
        self.assertEqual(tester.plate, Plate(17))

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
                self.assertEqual(obs_composition.upstream_process, obs)
                self.assertEqual(obs_composition.container, well)
                self.assertEqual(obs_composition.total_volume, 10)

    def test_update_well(self):
        tester = SamplePlatingProcess(6)
        obs = SampleComposition(85)

        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)

        # Update a well from CONTROL -> EXPERIMENTAL SAMPLE
        tester.update_well(8, 1, '1.SKM8.640201')
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKM8.640201')

        # Update a well from EXPERIMENTAL SAMPLE -> EXPERIMENTAL SAMPLE
        tester.update_well(8, 1, '1.SKB6.640176')
        self.assertEqual(obs.sample_composition_type, 'experimental sample')
        self.assertEqual(obs.sample_id, '1.SKB6.640176')

        # Update a well from EXPERIMENTAL SAMPLE -> CONTROL
        tester.update_well(8, 1, 'vibrio positive control')
        self.assertEqual(obs.sample_composition_type,
                         'vibrio positive control')
        self.assertIsNone(obs.sample_id)

        # Update a well from CONROL -> CONTROL
        tester.update_well(8, 1, 'blank')
        self.assertEqual(obs.sample_composition_type, 'blank')
        self.assertIsNone(obs.sample_id)


class TestReagentCreationProcess(LabmanTestCase):
    def test_attributes(self):
        tester = ReagentCreationProcess(3)
        self.assertEqual(tester.date, date(2017, 10, 23))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 3)
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


class TestGDNAExtractionProcess(LabmanTestCase):
    def test_attributes(self):
        tester = GDNAExtractionProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 7)
        self.assertEqual(tester.robot, Equipment(5))
        self.assertEqual(tester.kit, ReagentComposition(1))
        self.assertEqual(tester.tool, Equipment(15))

    def test_create(self):
        user = User('test@foo.bar')
        robot = Equipment(6)
        tool = Equipment(15)
        kit = ReagentComposition(1)
        plate = Plate(17)
        obs = GDNAExtractionProcess.create(user, robot, tool, kit, [plate], 10)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.robot, robot)
        self.assertEqual(obs.kit, kit)
        self.assertEqual(obs.tool, tool)

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
            'vibrio positive control')
        self.assertIsNone(
            plate_layout[7][0].composition.sample_composition.sample_id)
        self.assertEqual(
            plate_layout[
                7][0].composition.sample_composition.sample_composition_type,
            'blank')


class TestGDNAPlateCompressionProcess(LabmanTestCase):
    def test_attributes(self):
        tester = GDNAPlateCompressionProcess(13)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 13)
        self.assertEqual(tester.plates, [Plate(20)])

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
        ep = GDNAExtractionProcess.create(
            user, Equipment(6), Equipment(15), ReagentComposition(1),
            [plateA, plateB], 1)

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
        self.assertEqual(tester.process_id, 8)
        self.assertEqual(tester.master_mix, ReagentComposition(2))
        self.assertEqual(tester.tm300_8_tool, Equipment(16))
        self.assertEqual(tester.tm50_8_tool, Equipment(17))
        self.assertEqual(tester.water_lot, ReagentComposition(3))
        self.assertEqual(tester.processing_robot, Equipment(8))

    def test_create(self):
        user = User('test@foo.bar')
        master_mix = ReagentComposition(2)
        water = ReagentComposition(3)
        robot = Equipment(8)
        tm300_8_tool = Equipment(16)
        tm50_8_tool = Equipment(17)
        volume = 10
        plates = [(Plate(18), Plate(9))]
        obs = LibraryPrep16SProcess.create(
            user, master_mix, water, robot, tm300_8_tool, tm50_8_tool,
            volume, plates)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.master_mix, master_mix)
        self.assertEqual(obs.tm300_8_tool, tm300_8_tool)
        self.assertEqual(obs.tm50_8_tool, tm50_8_tool)
        self.assertEqual(obs.water_lot, water)
        self.assertEqual(obs.processing_robot, robot)

        # Check the generated plates
        obs_plates = obs.plates
        self.assertEqual(len(obs_plates), 1)
        obs_plate = obs_plates[0]
        self.assertIsInstance(obs_plate, Plate)
        self.assertEqual(obs_plate.external_id,
                         '16S library - Test gDNA plate 1')
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
                self.assertEqual(obs_composition.total_volume, 10)

        # spot check a couple of elements
        sample_id = plate_layout[0][
            0].composition.gdna_composition.sample_composition.sample_id
        self.assertEqual(sample_id, '1.SKB1.640202')
        barcode = plate_layout[0][
            0].composition.primer_composition.primer_set_composition.barcode
        self.assertEqual(barcode, 'TCCCTTGTCTCC')


class TestQuantificationProcess(LabmanTestCase):
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
        self.assertEqual(tester.process_id, 9)
        obs = tester.concentrations
        self.assertEqual(len(obs), 96)
        self.assertEqual(obs[0], (LibraryPrep16SComposition(1), 1.5))
        self.assertEqual(obs[36], (LibraryPrep16SComposition(37), 1.5))
        self.assertEqual(obs[95], (LibraryPrep16SComposition(96), 1.5))

    def test_create(self):
        user = User('test@foo.bar')
        plate = Plate(18)
        concentrations = np.random.rand(8, 12)
        obs = QuantificationProcess.create(user, plate, concentrations)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        obs_c = obs.concentrations
        self.assertEqual(len(obs_c), 96)
        self.assertEqual(obs_c[0][0], GDNAComposition(1))
        npt.assert_almost_equal(obs_c[0][1], concentrations[0][0])
        self.assertEqual(obs_c[12][0], GDNAComposition(61))
        npt.assert_almost_equal(obs_c[12][1], concentrations[1][0])


class TestPoolingProcess(LabmanTestCase):
    def test_attributes(self):
        tester = PoolingProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 10)
        self.assertEqual(tester.quantification_process,
                         QuantificationProcess(1))
        self.assertEqual(tester.robot, Equipment(8))

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
                                    input_compositions, robot)
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.quantification_process, quant_proc)
        self.assertEqual(obs.robot, robot)


class TestSequencingProcess(LabmanTestCase):
    def test_attributes(self):
        tester = SequencingProcess(1)
        self.assertEqual(tester.date, date(2017, 10, 25))
        self.assertEqual(tester.personnel, User('test@foo.bar'))
        self.assertEqual(tester.process_id, 12)
        self.assertEqual(tester.pool, PoolComposition(2))
        self.assertEqual(tester.run_name, 'TestRun1')
        self.assertEqual(tester.sequencer, Equipment(18))
        self.assertEqual(tester.fwd_cycles, 151)
        self.assertEqual(tester.rev_cycles, 151)
        self.assertEqual(tester.assay, 'test assay')
        self.assertEqual(tester.principal_investigator, User('test@foo.bar'))
        self.assertEqual(tester.contact_0, User('shared@foo.bar'))
        self.assertEqual(tester.contact_1, User('admin@foo.bar'))
        self.assertEqual(tester.contact_2, User('demo@microbio.me'))

    def test_create(self):
        user = User('test@foo.bar')
        pool = PoolComposition(2)
        sequencer = Equipment(18)
        obs = SequencingProcess.create(
            user, pool, 'TestRun', sequencer, 151, 151, 'test assay', user,
            User('shared@foo.bar'), User('admin@foo.bar'),
            User('demo@microbio.me'))
        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, user)
        self.assertEqual(obs.pool, PoolComposition(2))
        self.assertEqual(obs.run_name, 'TestRun')
        self.assertEqual(obs.sequencer, Equipment(18))
        self.assertEqual(obs.fwd_cycles, 151)
        self.assertEqual(obs.rev_cycles, 151)
        self.assertEqual(obs.assay, 'test assay')
        self.assertEqual(obs.principal_investigator, User('test@foo.bar'))
        self.assertEqual(obs.contact_0, User('shared@foo.bar'))
        self.assertEqual(obs.contact_1, User('admin@foo.bar'))
        self.assertEqual(obs.contact_2, User('demo@microbio.me'))

    def test_format_sample_sheet(self):
        tester = SequencingProcess(1)
        self.assertEqual(tester.format_sample_sheet(), EXP_SAMPLE_SHEET)


PLATE_READER_EXAMPLE = """Curve0.5\tY=A*X+B\t1.15E+003\t99.8\t0.773\t?????\n
0.154\t0.680\t0.440\t0.789\t0.778\t3.246\t1.729\t0.436\t0.152\t2.971\t3.280\t\
0.062\t5.396\t0.068\t0.632\t2.467\t1.718\t0.285\t1.950\t2.507\t1.386\t2.492\t\
7.016\t0.083\n
0.064\t15.243\t0.156\t2.325\t13.411\t0.480\t15.444\t3.464\t15.465\t1.597\t\
1.569\t1.810\t3.870\t1.156\t5.219\t0.038\t0.987\t7.321\t0.061\t2.347\t3.436\t\
2.494\t0.991\t1.560\n
0.070\t0.335\t1.160\t0.052\t0.511\t0.087\t0.746\t0.035\t0.070\t0.395\t2.708\t\
0.035\t1.060\t0.041\t1.061\t0.836\t0.876\t1.456\t0.876\t2.330\t1.773\t0.433\t\
2.047\t0.071\n
0.058\t3.684\t0.426\t0.957\t1.564\t1.935\t2.930\t1.175\t45.111\t5.490\t4.659\t\
16.602\t2.911\t4.096\t2.892\t0.084\t2.534\t1.820\t1.132\t0.500\t2.071\t0.761\t\
0.824\t1.364\n
0.045\t0.231\t0.246\t2.600\t0.658\t5.007\t1.093\t1.410\t0.089\t1.810\t0.251\t\
0.034\t2.126\t0.065\t0.893\t2.682\t1.226\t0.980\t4.734\t2.122\t1.469\t1.213\t\
0.057\t0.052\n
0.051\t1.091\t0.117\t0.454\t4.189\t2.823\t1.128\t0.219\t9.575\t1.829\t3.506\t\
7.271\t7.841\t0.504\t1.467\t0.130\t27.226\t3.093\t2.747\t1.087\t4.533\t\
16.917\t1.588\t6.551\n
0.037\t0.067\t0.770\t0.490\t0.711\t0.565\t0.922\t0.063\t0.841\t0.115\t0.046\t\
0.044\t6.361\t0.051\t0.330\t1.742\t0.105\t0.756\t0.320\t3.696\t5.029\t5.671\t\
0.056\t0.060\n
0.050\t0.234\t3.427\t14.636\t1.814\t5.541\t3.395\t6.570\t3.094\t5.384\t2.031\t\
5.400\t16.724\t0.207\t1.038\t0.072\t0.964\t4.050\t4.767\t7.891\t0.340\t1.730\t\
12.827\t1.946\n
0.064\t0.137\t0.843\t0.633\t0.119\t2.592\t5.804\t0.999\t0.511\t0.304\t0.353\t\
0.053\t2.645\t0.070\t0.071\t0.991\t0.286\t3.576\t1.993\t6.539\t8.736\t6.910\t\
0.070\t0.064\n
0.079\t1.160\t1.053\t3.178\t7.796\t2.323\t0.992\t0.760\t2.181\t2.739\t3.232\t\
1.166\t3.257\t0.680\t1.955\t0.088\t0.586\t7.026\t0.306\t8.078\t2.375\t10.286\t\
8.571\t0.528\n
0.081\t1.718\t2.069\t0.863\t0.197\t3.352\t0.132\t0.124\t0.145\t0.628\t0.060\t\
0.060\t2.612\t0.072\t0.177\t0.170\t1.261\t0.464\t4.059\t2.724\t3.449\t0.252\t\
0.073\t0.073\n
0.080\t1.128\t3.536\t38.352\t1.361\t1.293\t0.803\t0.456\t9.873\t6.525\t\
24.843\t1.052\t0.084\t1.034\t1.392\t0.066\t0.598\t3.002\t1.785\t8.376\t\
0.882\t0.272\t4.079\t11.586\n
0.086\t0.548\t0.625\t0.557\t0.601\t0.481\t0.449\t0.643\t52.291\t1.978\t\
0.068\t0.209\t11.138\t0.070\t0.324\t0.492\t5.913\t0.963\t0.843\t8.087\t\
0.647\t0.664\t0.080\t0.090\n
0.099\t8.458\t3.391\t17.942\t7.709\t3.955\t2.891\t7.681\t0.262\t3.994\t\
1.309\t6.377\t1.272\t0.638\t5.323\t5.794\t0.868\t1.021\t1.523\t0.662\t\
3.279\t1.980\t4.208\t1.794\n
0.763\t0.615\t0.352\t0.745\t1.383\t0.546\t0.247\t0.504\t5.138\t0.116\t\
0.167\t0.062\t0.573\t0.096\t0.227\t3.399\t7.361\t2.376\t3.790\t3.389\t\
0.906\t6.238\t0.112\t0.098\n
0.105\t0.505\t4.985\t0.450\t5.264\t15.071\t6.145\t10.357\t1.128\t4.151\t\
9.280\t8.581\t1.343\t2.416\t0.671\t9.347\t0.836\t5.312\t0.719\t0.622\t\
4.342\t4.166\t0.633\t11.101\n
"""

EXP_SAMPLE_SHEET = """[Header],,,,,,,,,,
IEMFileVersion,4,,,,,,,,,
Investigator Name,Dude,,,,PI,Dude,test@foo.bar,,,
Experiment Name,TestRun1,,,,Contact,Shared,Admin,Demo,,
Date,01/09/2018,,,,,shared@foo.bar,admin@foo.bar,demo@microbio.me,,
Workflow,GenerateFASTQ,,,,,,,,,
Application,FASTQ Only,,,,,,,,,
Assay,test assay,,,,,,,,,
Description,labman ID,1,,,,,,,,
Chemistry,Default,,,,,,,,,
,,,,,,,,,,
[Reads],,,,,,,,,,
151,,,,,,,,,,
151,,,,,,,,,,
,,,,,,,,,,
[Settings],,,,,,,,,,
ReverseComplement,0,,,,,,,,,
,,,,,,,,,,
[Data],,,,,,,,,,
Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description,,,
TestRun1,,,,,NNNNNNNNNNNN,,,,,,
"""  # noqa


if __name__ == '__main__':
    main()
