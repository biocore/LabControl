# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from types import GeneratorType

from labman.db.testing import LabmanTestCase
from labman.db.plate import PlateConfiguration, Plate
from labman.db.container import Well
from labman.db.exceptions import LabmanError


class TestPlateConfiguration(LabmanTestCase):
    def test_iter(self):
        obs = PlateConfiguration.iter()
        self.assertIsInstance(obs, GeneratorType)
        obs = list(obs)
        # Since we can't ensure the test order between this test and
        # test_create, we check both lengths, but we only check the content
        # of the first 4 elements
        self.assertIn(len(obs), [4, 5])
        exp = [PlateConfiguration(1), PlateConfiguration(2),
               PlateConfiguration(3), PlateConfiguration(4)]
        self.assertEqual(obs[:4], exp)

    def test_create(self):
        obs = PlateConfiguration.create('96-well Test description', 8, 12)
        self.assertEqual(obs.description, '96-well Test description')
        self.assertEqual(obs.num_rows, 8)
        self.assertEqual(obs.num_columns, 12)


class TestPlate(LabmanTestCase):
    def test_create(self):
        plate_conf = PlateConfiguration.create('96-well Test desc', 8, 12)
        obs = Plate.create('New plate', plate_conf)
        self.assertEqual(obs.external_id, 'New plate')
        self.assertEqual(obs.plate_configuration, plate_conf)
        self.assertFalse(obs.discarded)
        self.assertIsNone(obs.notes)
        # This is a weird case and it should never happen in normal execution
        # of the code: the plate has been created without any well, hence all
        # the None values. In reality, all the plate creation is handled
        # by one of the Process classes, which ensures the creation of all
        # the wells.
        self.assertEqual(obs.layout, [[None] * 12] * 8)

    def test_properties(self):
        # Plate 17 - Defined in the test DB
        tester = Plate(17)
        self.assertEqual(tester.external_id, 'Test plate 1')
        self.assertEqual(tester.plate_configuration, PlateConfiguration(1))
        self.assertFalse(tester.discarded)
        self.assertIsNone(tester.notes)
        obs_layout = tester.layout
        self.assertEqual(len(obs_layout), 8)
        for row in obs_layout:
            self.assertEqual(len(row), 12)

        # Test changing the name of the plate
        tester.external_id = 'Some new name'
        self.assertEqual(tester.external_id, 'Some new name')
        tester.external_id = 'Test plate 1'
        self.assertEqual(tester.external_id, 'Test plate 1')

    def test_get_well(self):
        # Plate 17 - Defined in the test DB
        tester = Plate(17)
        self.assertEqual(tester.get_well(1, 1), Well(1537))
        self.assertEqual(tester.get_well(1, 2), Well(1540))
        self.assertEqual(tester.get_well(7, 2), Well(1756))
        self.assertEqual(tester.get_well(8, 12), Well(1822))
        with self.assertRaises(LabmanError):
            tester.get_well(8, 13)
        with self.assertRaises(LabmanError):
            tester.get_well(9, 12)


if __name__ == '__main__':
    main()
