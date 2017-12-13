# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from datetime import date

from labman.db.testing import LabmanTestCase
from labman.db.user import User
from labman.db.plate import Plate, PlateConfiguration
from labman.db.process import (
    Process, SamplePlatingProcess,
    PrimerWorkingPlateCreationProcess, GDNAExtractionProcess,
    LibraryPrep16SProcess, QuantificationProcess, PoolingProcess)
# NormalizationProcess, LibraryPrepShotgunProcess


class TestProcess(LabmanTestCase):
    def test_factory(self):
        self.assertEqual(Process.factory(4),
                         SamplePlatingProcess(4))
        self.assertEqual(Process.factory(2),
                         PrimerWorkingPlateCreationProcess(1))
        self.assertEqual(Process.factory(5),
                         GDNAExtractionProcess(1))
        self.assertEqual(Process.factory(6),
                         LibraryPrep16SProcess(1))
        self.assertEqual(Process.factory(7),
                         QuantificationProcess(1))
        self.assertEqual(Process.factory(8), PoolingProcess(1))
        # self.assertEqual(Process.factory(),
        #                  NormalizationProcess())
        # self.assertEqual(Process.factory(),
        #                  LibraryPrepShotgunProcess())


class TestSamplePlatingProcess(LabmanTestCase):
    def test_create(self):
        user = User('test@foo.bar')
        # 1 -> 96-well deep-well plate
        plate_config = PlateConfiguration(1)
        obs = SamplePlatingProcess.create(
            user, plate_config, 'Test Plate 1', 10)

        self.assertEqual(obs.date, date.today())
        self.assertEqual(obs.personnel, User('test@foo.bar'))

        # Check that the plate has been created with the correct values
        obs_plate = obs.plate
        self.assertIsInstance(obs_plate, Plate)
        self.assertEqual(obs_plate.external_id, 'Test Plate 1')
        self.assertEqual(obs_plate.plate_configuration, plate_config)
        self.assertFalse(obs_plate.discarded)
        self.assertIsNone(obs_plate.notes)

        # Check that all the wells in the plate contain blanks


if __name__ == '__main__':
    main()
