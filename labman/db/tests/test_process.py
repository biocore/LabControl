# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from datetime import date

import numpy as np
import numpy.testing as npt

from labman.db.testing import LabmanTestCase
from labman.db.container import Tube, Well
from labman.db.composition import (
    ReagentComposition, SampleComposition, GDNAComposition,
    LibraryPrep16SComposition)
from labman.db.user import User
from labman.db.plate import Plate, PlateConfiguration
from labman.db.equipment import Equipment
from labman.db.process import (
    Process, SamplePlatingProcess, ReagentCreationProcess,
    PrimerWorkingPlateCreationProcess, GDNAExtractionProcess,
    LibraryPrep16SProcess, QuantificationProcess, PoolingProcess)
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
        self.assertEqual(obs_c[12][0], GDNAComposition(13))
        npt.assert_almost_equal(obs_c[12][1], concentrations[1][0])


if __name__ == '__main__':
    main()
