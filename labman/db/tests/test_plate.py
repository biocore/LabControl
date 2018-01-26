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
from labman.db.user import User
from labman.db.process import (QuantificationProcess, SamplePlatingProcess,
                               GDNAExtractionProcess)


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
    def test_search(self):
        with self.assertRaises(ValueError):
            Plate.search()

        with self.assertRaises(ValueError):
            Plate.search(samples=['1.SKB1.640202'], query_type='WRONG')

        plate21 = Plate(21)
        plate22 = Plate(22)
        plate23 = Plate(23)

        self.assertEqual(
            Plate.search(samples=['1.SKB1.640202', '1.SKB2.640194']),
            [plate21])
        self.assertEqual(Plate.search(samples=['1.SKB1.640202']), [plate21])

        self.assertEqual(Plate.search(plate_notes='interesting'), [])
        # Add comments to a plate so we can actually test the
        # search functionality
        plate22.notes = 'Some interesting notes'
        plate23.notes = 'More boring notes'

        self.assertEqual(Plate.search(plate_notes='interesting'), [plate22])
        self.assertCountEqual(Plate.search(plate_notes='interesting boring'),
                              [])
        self.assertEqual(
            Plate.search(samples=['1.SKB1.640202'], plate_notes='interesting'),
            [])
        self.assertCountEqual(
            Plate.search(samples=['1.SKB1.640202'], plate_notes='interesting',
                         query_type='UNION'),
            [plate21, plate22])

        # The search engine ignores common english words
        self.assertEqual(Plate.search(plate_notes='more'), [])

        # Add comments to some wells
        plate23.get_well(1, 1).composition.notes = 'What else should I write?'
        self.assertEqual(Plate.search(well_notes='write'), [plate23])
        self.assertEqual(
            Plate.search(plate_notes='interesting', well_notes='write'), [])
        self.assertCountEqual(
            Plate.search(plate_notes='interesting', well_notes='write',
                         query_type='UNION'), [plate22, plate23])

    def test_list_plates(self):
        # Test returning all plates
        obs = Plate.list_plates()
        # We are creating plates below, but at least we know there are 26
        # plates in the test database
        self.assertGreaterEqual(len(obs), 26)
        self.assertEqual(obs[0], {'plate_id': 1,
                                  'external_id': 'EMP 16S V4 primer plate 1'})
        self.assertEqual(
            obs[16], {'plate_id': 17,
                      'external_id': 'EMP 16S V4 primer plate 7 10/23/2017'})
        self.assertEqual(obs[20], {'plate_id': 21,
                                   'external_id': 'Test plate 1'})

        # Test returning sample plates
        obs = Plate.list_plates(['sample'])
        self.assertGreaterEqual(len(obs), 1)
        self.assertEqual(obs[0], {'plate_id': 21,
                                  'external_id': 'Test plate 1'})

        # Test returning gDNA plates
        obs = Plate.list_plates(['gDNA'])
        self.assertEqual(
            obs, [{'plate_id': 22,
                   'external_id': 'Test gDNA plate 1'}])

        obs = Plate.list_plates(['compressed gDNA'])
        self.assertEqual(
            obs, [{'plate_id': 24,
                   'external_id': 'Test compressed gDNA plate 1'}])

        # Test returning primer plates
        obs = Plate.list_plates(['primer'])
        exp = [
            {'plate_id': 11,
             'external_id': 'EMP 16S V4 primer plate 1 10/23/2017'},
            {'plate_id': 12,
             'external_id': 'EMP 16S V4 primer plate 2 10/23/2017'},
            {'plate_id': 13,
             'external_id': 'EMP 16S V4 primer plate 3 10/23/2017'},
            {'plate_id': 14,
             'external_id': 'EMP 16S V4 primer plate 4 10/23/2017'},
            {'plate_id': 15,
             'external_id': 'EMP 16S V4 primer plate 5 10/23/2017'},
            {'plate_id': 16,
             'external_id': 'EMP 16S V4 primer plate 6 10/23/2017'},
            {'plate_id': 17,
             'external_id': 'EMP 16S V4 primer plate 7 10/23/2017'},
            {'plate_id': 18,
             'external_id': 'EMP 16S V4 primer plate 8 10/23/2017'},
            {'plate_id': 19, 'external_id': 'iTru 5 Primer Plate 10/23/2017'},
            {'plate_id': 20, 'external_id': 'iTru 7 Primer Plate 10/23/2017'}]
        self.assertEqual(obs, exp)

        # Test returning gDNA and compressed gDNA plates
        obs = Plate.list_plates(['gDNA', 'compressed gDNA'])
        self.assertEqual(
            obs, [{'plate_id': 22,
                   'external_id': 'Test gDNA plate 1'},
                  {'plate_id': 24,
                   'external_id': 'Test compressed gDNA plate 1'}])

        obs = Plate.list_plates(['compressed gDNA', 'normalized gDNA'])
        self.assertEqual(
            obs, [{'plate_id': 24,
                   'external_id': 'Test compressed gDNA plate 1'},
                  {'plate_id': 25,
                   'external_id': 'Test normalized gDNA plate 1'}])

        obs = Plate.list_plates(['compressed gDNA', 'normalized gDNA'],
                                only_quantified=True)

        self.assertEqual(
            obs, [{'plate_id': 24,
                   'external_id': 'Test compressed gDNA plate 1'}])

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
        self.assertEqual(tester.process, SamplePlatingProcess(10))

        # Test changing the name of the plate
        tester.external_id = 'Some new name'
        self.assertEqual(tester.external_id, 'Some new name')
        tester.external_id = 'Test plate 1'
        self.assertEqual(tester.external_id, 'Test plate 1')

        self.assertEqual(Plate(23).quantification_process,
                         QuantificationProcess(1))
        self.assertEqual(Plate(22).process, GDNAExtractionProcess(1))

        exp = {'1.SKB1.640202': [Well(3073), Well(3253), Well(3433),
                                 Well(3613), Well(3793), Well(3973)],
               '1.SKB2.640194': [Well(3088), Well(3268), Well(3448),
                                 Well(3628), Well(3808), Well(3988)],
               '1.SKB3.640195': [Well(3103), Well(3283), Well(3463),
                                 Well(3643), Well(3823), Well(4003)],
               '1.SKB4.640189': [Well(3118), Well(3298), Well(3478),
                                 Well(3658), Well(3838), Well(4018)],
               '1.SKB5.640181': [Well(3133), Well(3313), Well(3493),
                                 Well(3673), Well(3853), Well(4033)],
               '1.SKB6.640176': [Well(3148), Well(3328), Well(3508),
                                 Well(3688), Well(3868), Well(4048)],
               '1.SKB7.640196': [Well(3163), Well(3343), Well(3523),
                                 Well(3703), Well(3883), Well(4063)],
               '1.SKB8.640193': [Well(3178), Well(3358), Well(3538),
                                 Well(3718), Well(3898), Well(4078)],
               '1.SKB9.640200': [Well(3193), Well(3373), Well(3553),
                                 Well(3733), Well(3913), Well(4093)],
               '1.SKD1.640179': [Well(3208), Well(3388), Well(3568),
                                 Well(3748), Well(3928), Well(4108)],
               '1.SKD2.640178': [Well(3223), Well(3403), Well(3583),
                                 Well(3763), Well(3943), Well(4123)],
               '1.SKD3.640198': [Well(3238), Well(3418), Well(3598),
                                 Well(3778), Well(3958), Well(4138)]}
        self.assertEqual(tester.duplicates, exp)

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

    def test_get_wells_by_sample(self):
        tester = Plate(21)
        exp = [Well(3073), Well(3253), Well(3433), Well(3613), Well(3793),
               Well(3973)]
        self.assertEqual(tester.get_wells_by_sample('1.SKB1.640202'), exp)
        self.assertEqual(tester.get_wells_by_sample('1.SKM1.640183'), [])

    def test_get_previously_plated_wells(self):
        tester = Plate(21)
        self.assertEqual(tester.get_previously_plated_wells(), {})

        # Create another plate and plate some samples in it
        spp = SamplePlatingProcess.create(
            User('test@foo.bar'), PlateConfiguration(1), 'New Plate For Prev')
        spp.update_well(1, 1, '1.SKD1.640179')
        exp = {}
        plate = spp.plate
        exp[Well(3208)] = [plate]
        exp[Well(3388)] = [plate]
        exp[Well(3568)] = [plate]
        exp[Well(3748)] = [plate]
        exp[Well(3928)] = [plate]
        exp[Well(4108)] = [plate]
        obs = tester.get_previously_plated_wells()
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
