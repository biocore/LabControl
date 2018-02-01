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

    def test_plate_list_discarded_functionality(self):
        # test case based on the test_list_plates
        obs = Plate.list_plates()
        Plate(21).discard = True
        self.assertGreaterEqual(len(obs), 25)
        self.assertEqual(obs[0], {'plate_id': 1,
                                  'external_id': 'EMP 16S V4 primer plate 1'})
        self.assertEqual(
            obs[16], {'plate_id': 17,
                      'external_id': 'EMP 16S V4 primer plate 7 10/23/2017'})
        self.assertEqual(obs[20], {'plate_id': 21,
                                   'external_id': 'Test plate 1'})
        Plate(21).discard = False

        # Test without returning discarded primer plates
        Plate(11).discarded = True
        Plate(12).discarded = True
        Plate(13).discarded = True
        obs = Plate.list_plates(['primer'], include_discarded=False)

        exp = [
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

        # Test returning discarded primer plates
        obs = Plate.list_plates(['primer'], include_discarded=True)
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

        # undo the discarding
        Plate(11).discarded = False
        Plate(12).discarded = False
        Plate(13).discarded = False

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
        tester.discarded = True
        self.assertTrue(tester.discarded)
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

        exp = {'1.SKB1.640202': [[Well(3073), '1.SKB1.640202.21.A1'],
                                 [Well(3253), '1.SKB1.640202.21.B1'],
                                 [Well(3433), '1.SKB1.640202.21.C1'],
                                 [Well(3613), '1.SKB1.640202.21.D1'],
                                 [Well(3793), '1.SKB1.640202.21.E1'],
                                 [Well(3973), '1.SKB1.640202.21.F1']],
               '1.SKB2.640194': [[Well(3088), '1.SKB2.640194.21.A2'],
                                 [Well(3268), '1.SKB2.640194.21.B2'],
                                 [Well(3448), '1.SKB2.640194.21.C2'],
                                 [Well(3628), '1.SKB2.640194.21.D2'],
                                 [Well(3808), '1.SKB2.640194.21.E2'],
                                 [Well(3988), '1.SKB2.640194.21.F2']],
               '1.SKB3.640195': [[Well(3103), '1.SKB3.640195.21.A3'],
                                 [Well(3283), '1.SKB3.640195.21.B3'],
                                 [Well(3463), '1.SKB3.640195.21.C3'],
                                 [Well(3643), '1.SKB3.640195.21.D3'],
                                 [Well(3823), '1.SKB3.640195.21.E3'],
                                 [Well(4003), '1.SKB3.640195.21.F3']],
               '1.SKB4.640189': [[Well(3118), '1.SKB4.640189.21.A4'],
                                 [Well(3298), '1.SKB4.640189.21.B4'],
                                 [Well(3478), '1.SKB4.640189.21.C4'],
                                 [Well(3658), '1.SKB4.640189.21.D4'],
                                 [Well(3838), '1.SKB4.640189.21.E4'],
                                 [Well(4018), '1.SKB4.640189.21.F4']],
               '1.SKB5.640181': [[Well(3133), '1.SKB5.640181.21.A5'],
                                 [Well(3313), '1.SKB5.640181.21.B5'],
                                 [Well(3493), '1.SKB5.640181.21.C5'],
                                 [Well(3673), '1.SKB5.640181.21.D5'],
                                 [Well(3853), '1.SKB5.640181.21.E5'],
                                 [Well(4033), '1.SKB5.640181.21.F5']],
               '1.SKB6.640176': [[Well(3148), '1.SKB6.640176.21.A6'],
                                 [Well(3328), '1.SKB6.640176.21.B6'],
                                 [Well(3508), '1.SKB6.640176.21.C6'],
                                 [Well(3688), '1.SKB6.640176.21.D6'],
                                 [Well(3868), '1.SKB6.640176.21.E6'],
                                 [Well(4048), '1.SKB6.640176.21.F6']],
               '1.SKB7.640196': [[Well(3163), '1.SKB7.640196.21.A7'],
                                 [Well(3343), '1.SKB7.640196.21.B7'],
                                 [Well(3523), '1.SKB7.640196.21.C7'],
                                 [Well(3703), '1.SKB7.640196.21.D7'],
                                 [Well(3883), '1.SKB7.640196.21.E7'],
                                 [Well(4063), '1.SKB7.640196.21.F7']],
               '1.SKB8.640193': [[Well(3178), '1.SKB8.640193.21.A8'],
                                 [Well(3358), '1.SKB8.640193.21.B8'],
                                 [Well(3538), '1.SKB8.640193.21.C8'],
                                 [Well(3718), '1.SKB8.640193.21.D8'],
                                 [Well(3898), '1.SKB8.640193.21.E8'],
                                 [Well(4078), '1.SKB8.640193.21.F8']],
               '1.SKB9.640200': [[Well(3193), '1.SKB9.640200.21.A9'],
                                 [Well(3373), '1.SKB9.640200.21.B9'],
                                 [Well(3553), '1.SKB9.640200.21.C9'],
                                 [Well(3733), '1.SKB9.640200.21.D9'],
                                 [Well(3913), '1.SKB9.640200.21.E9'],
                                 [Well(4093), '1.SKB9.640200.21.F9']],
               '1.SKD1.640179': [[Well(3208), '1.SKD1.640179.21.A10'],
                                 [Well(3388), '1.SKD1.640179.21.B10'],
                                 [Well(3568), '1.SKD1.640179.21.C10'],
                                 [Well(3748), '1.SKD1.640179.21.D10'],
                                 [Well(3928), '1.SKD1.640179.21.E10'],
                                 [Well(4108), '1.SKD1.640179.21.F10']],
               '1.SKD2.640178': [[Well(3223), '1.SKD2.640178.21.A11'],
                                 [Well(3403), '1.SKD2.640178.21.B11'],
                                 [Well(3583), '1.SKD2.640178.21.C11'],
                                 [Well(3763), '1.SKD2.640178.21.D11'],
                                 [Well(3943), '1.SKD2.640178.21.E11'],
                                 [Well(4123), '1.SKD2.640178.21.F11']],
               '1.SKD3.640198': [[Well(3238), '1.SKD3.640198.21.A12'],
                                 [Well(3418), '1.SKD3.640198.21.B12'],
                                 [Well(3598), '1.SKD3.640198.21.C12'],
                                 [Well(3778), '1.SKD3.640198.21.D12'],
                                 [Well(3958), '1.SKD3.640198.21.E12'],
                                 [Well(4138), '1.SKD3.640198.21.F12']]}
        self.assertEqual(tester.duplicates, exp)
        self.assertEqual(tester.unknown_samples, [])
        exp = tester.get_well(1, 1)
        exp.composition.update('Unknown')
        self.assertEqual(tester.unknown_samples, [exp])
        exp.composition.update('1.SKB1.640202')

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
