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
from labman.db.study import Study
from labman.db.process import QuantificationProcess


class TestPlateConfiguration(LabmanTestCase):
    def test_iter(self):
        obs = PlateConfiguration.iter()
        self.assertIsInstance(obs, GeneratorType)
        obs = list(obs)
        # Since we can't ensure the test order between this test and
        # test_create, we check both lengths, but we only check the content
        # of the first 5 elements
        self.assertIn(len(obs), [5, 6])
        exp = [PlateConfiguration(1), PlateConfiguration(2),
               PlateConfiguration(3), PlateConfiguration(4),
               PlateConfiguration(5)]
        self.assertEqual(obs[:5], exp)

    def test_create(self):
        obs = PlateConfiguration.create('96-well Test description', 8, 12)
        self.assertEqual(obs.description, '96-well Test description')
        self.assertEqual(obs.num_rows, 8)
        self.assertEqual(obs.num_columns, 12)


class TestPlate(LabmanTestCase):
    def test_list_plates(self):
        # Test returning all plates
        obs = Plate.list_plates()
        # We are creating plates below, but at least we know there are 19
        # plates in the test database
        self.assertGreaterEqual(len(obs), 26)
        self.assertEqual(obs[0], {'plate_id': 1,
                                  'external_id': 'EMP primer plate 1'})
        self.assertEqual(
            obs[16], {'plate_id': 17,
                      'external_id': 'EMP Primer plate 7 10/23/2017'})
        self.assertEqual(obs[20], {'plate_id': 21,
                                   'external_id': 'Test plate 1'})

        # Test returning sample plates
        obs = Plate.list_plates('sample')
        self.assertEqual(obs, [{'plate_id': 21,
                                'external_id': 'Test plate 1'}])

        # Test returning gDNA plates
        obs = Plate.list_plates('gDNA')
        self.assertEqual(
            obs, [{'plate_id': 22,
                   'external_id': 'Test gDNA plate 1'},
                  {'plate_id': 24,
                   'external_id': 'Test compressed gDNA plate 1'}])

        # Test returning primer plates
        obs = Plate.list_plates('primer')
        exp = [
            {'plate_id': 11, 'external_id': 'EMP Primer plate 1 10/23/2017'},
            {'plate_id': 12, 'external_id': 'EMP Primer plate 2 10/23/2017'},
            {'plate_id': 13, 'external_id': 'EMP Primer plate 3 10/23/2017'},
            {'plate_id': 14, 'external_id': 'EMP Primer plate 4 10/23/2017'},
            {'plate_id': 15, 'external_id': 'EMP Primer plate 5 10/23/2017'},
            {'plate_id': 16, 'external_id': 'EMP Primer plate 6 10/23/2017'},
            {'plate_id': 17, 'external_id': 'EMP Primer plate 7 10/23/2017'},
            {'plate_id': 18, 'external_id': 'EMP Primer plate 8 10/23/2017'},
            {'plate_id': 19, 'external_id': 'iTru 5 Primer Plate 10/23/2017'},
            {'plate_id': 20, 'external_id': 'iTru 7 Primer Plate 10/23/2017'}]
        self.assertEqual(obs, exp)

    def test_external_id_exists(self):
        self.assertTrue(Plate.external_id_exists('Test plate 1'))
        self.assertFalse(Plate.external_id_exists('This is a new name'))

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
        # Plate 21 - Defined in the test DB
        tester = Plate(21)
        self.assertEqual(tester.external_id, 'Test plate 1')
        self.assertEqual(tester.plate_configuration, PlateConfiguration(1))
        self.assertFalse(tester.discarded)
        self.assertIsNone(tester.notes)
        obs_layout = tester.layout
        self.assertEqual(len(obs_layout), 8)
        for row in obs_layout:
            self.assertEqual(len(row), 12)
        self.assertEqual(tester.studies, {Study(1)})
        self.assertIsNone(tester.quantification_process)

        # Test changing the name of the plate
        tester.external_id = 'Some new name'
        self.assertEqual(tester.external_id, 'Some new name')
        tester.external_id = 'Test plate 1'
        self.assertEqual(tester.external_id, 'Test plate 1')

        self.assertEqual(Plate(23).quantification_process,
                         QuantificationProcess(1))

    def test_get_well(self):
        # Plate 21 - Defined in the test DB
        tester = Plate(21)
        self.assertEqual(tester.get_well(1, 1), Well(3073))
        self.assertEqual(tester.get_well(1, 2), Well(3088))
        self.assertEqual(tester.get_well(7, 2), Well(4168))
        self.assertEqual(tester.get_well(8, 12), Well(4498))
        with self.assertRaises(LabmanError):
            tester.get_well(8, 13)
        with self.assertRaises(LabmanError):
            tester.get_well(9, 12)


if __name__ == '__main__':
    main()
