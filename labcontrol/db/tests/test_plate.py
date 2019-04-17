# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labcontrol development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main
from types import GeneratorType
import datetime

from labcontrol.db.testing import LabcontrolTestCase
from labcontrol.db.plate import PlateConfiguration, Plate
from labcontrol.db.container import Well
from labcontrol.db.exceptions import LabcontrolError
from labcontrol.db.study import Study
from labcontrol.db.user import User
from labcontrol.db.process import (QuantificationProcess, SamplePlatingProcess,
                               GDNAExtractionProcess)


class TestPlateConfiguration(LabcontrolTestCase):
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


class TestPlate(LabcontrolTestCase):
    def test_search(self):
        with self.assertRaises(ValueError):
            Plate.search()

        with self.assertRaises(ValueError):
            Plate.search(samples=['1.SKB1.640202'], query_type='WRONG')

        plate21 = Plate(21)
        plate22 = Plate(22)
        plate23 = Plate(23)
        plate27 = Plate(27)
        plate30 = Plate(30)
        plate33 = Plate(33)

        self.assertEqual(
            Plate.search(samples=['1.SKB1.640202', '1.SKB2.640194']),
            [plate21, plate27, plate30, plate33])
        self.assertEqual(Plate.search(samples=['1.SKB1.640202']),
                         [plate21, plate27, plate30, plate33])

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
        # sample '1.SKB1.640202' is on 4 sample plates, plus there is a
        # gdna plate with a note containing the word 'interesting'
        self.assertCountEqual(
            Plate.search(samples=['1.SKB1.640202'], plate_notes='interesting',
                         query_type='UNION'),
            [plate21, plate22, plate27, plate30, plate33])

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

    def strip_out_creation_timestamp(self, plates):
        """Kludge to remove creation_timestamp from plate list results"""
        obs_ = []
        for o in plates:
            o = o.copy()
            self.assertIn('creation_timestamp', o)
            o.pop('creation_timestamp')
            obs_.append(o)
        return obs_

    def test_list_plates(self):
        # Test returning all plates
        obs = self.strip_out_creation_timestamp(Plate.list_plates())

        # We are creating plates below, but at least we know there are 35
        # plates in the test database
        self.assertGreaterEqual(len(obs), 35)
        self.assertEqual(obs[0], {'plate_id': 1,
                                  'external_id': 'EMP 16S V4 primer plate 1'})
        self.assertEqual(
            obs[16], {'plate_id': 17,
                      'external_id': 'EMP 16S V4 primer plate 7 10/23/2017'})
        self.assertEqual(obs[20], {'plate_id': 21,
                                   'external_id': 'Test plate 1'})

        # Test returning sample plates
        obs = self.strip_out_creation_timestamp(Plate.list_plates(['sample']))
        self.assertGreaterEqual(len(obs), 4)
        self.assertEqual(obs[0], {'plate_id': 21,
                                  'external_id': 'Test plate 1'})
        obs = self.strip_out_creation_timestamp(Plate.list_plates(['sample'],
                                                include_study_titles=True))
        self.assertGreaterEqual(len(obs), 4)
        self.assertEqual(
            obs[0], {'plate_id': 21,
                     'external_id': 'Test plate 1',
                     'studies': ['Identification of the Microbiomes '
                                 'for Cannabis Soils']})

        # Test returning gDNA plates
        obs = self.strip_out_creation_timestamp(Plate.list_plates(['gDNA']))
        self.assertEqual(
            obs, [{'plate_id': 22,
                   'external_id': 'Test gDNA plate 1'},
                  {'external_id': 'Test gDNA plate 2', 'plate_id': 28},
                  {'external_id': 'Test gDNA plate 3', 'plate_id': 31},
                  {'external_id': 'Test gDNA plate 4', 'plate_id': 34}])

        obs = self.strip_out_creation_timestamp(
            Plate.list_plates(['compressed gDNA']))
        self.assertEqual(
            obs, [{'plate_id': 24,
                   'external_id': 'Test compressed gDNA plates 1-4'}])

        # Test returning primer plates
        obs = self.strip_out_creation_timestamp(Plate.list_plates(['primer']))
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
        obs = self.strip_out_creation_timestamp(
            Plate.list_plates(['gDNA', 'compressed gDNA']))
        self.assertEqual(
            obs, [{'plate_id': 22,
                   'external_id': 'Test gDNA plate 1'},
                  {'plate_id': 24,
                   'external_id': 'Test compressed gDNA plates 1-4'},
                  {'external_id': 'Test gDNA plate 2', 'plate_id': 28},
                  {'external_id': 'Test gDNA plate 3', 'plate_id': 31},
                  {'external_id': 'Test gDNA plate 4', 'plate_id': 34}
                  ])

        obs = self.strip_out_creation_timestamp(
            Plate.list_plates(['compressed gDNA', 'normalized gDNA']))
        self.assertEqual(
            obs, [{'plate_id': 24,
                   'external_id': 'Test compressed gDNA plates 1-4'},
                  {'plate_id': 25,
                   'external_id': 'Test normalized gDNA plates 1-4'}])

        obs = self.strip_out_creation_timestamp(
            Plate.list_plates(['compressed gDNA', 'normalized gDNA'],
                              only_quantified=True,
                              include_study_titles=True))
        self.assertEqual(
            obs, [{'plate_id': 24,
                   'external_id': 'Test compressed gDNA plates 1-4',
                   'studies': ['Identification of the Microbiomes '
                               'for Cannabis Soils']}])

    def test_plate_list_include_timestamp(self):
        # ...limit pathological failures by testing within an hour of creation
        exp = datetime.datetime.now()
        exp = str(datetime.datetime(exp.year,
                                    exp.month,
                                    exp.day)).split(None, 1)[0]

        for i in Plate.list_plates():
            obs = i['creation_timestamp'].split(None, 1)[0]
            self.assertEqual(obs, exp)

    def test_plate_list_discarded_functionality(self):
        # test case based on the test_list_plates
        obs = self.strip_out_creation_timestamp(Plate.list_plates())
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
        obs = self.strip_out_creation_timestamp(Plate.list_plates(['primer'],
                                                include_discarded=False))

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
        obs = self.strip_out_creation_timestamp(Plate.list_plates(['primer'],
                                                include_discarded=True))
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

        obs = tester.creation_timestamp
        obs = str(datetime.datetime(obs.year,
                                    obs.month,
                                    obs.day))
        exp = datetime.datetime.now()
        exp = str(datetime.datetime(exp.year, exp.month, exp.day))
        self.assertEqual(obs, exp)
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
        self.assertListEqual(tester.quantification_processes, [])
        self.assertEqual(tester.process, SamplePlatingProcess(11))

        # Test changing the name of the plate
        tester.external_id = 'Some new name'
        self.assertEqual(tester.external_id, 'Some new name')
        tester.external_id = 'Test plate 1'
        self.assertEqual(tester.external_id, 'Test plate 1')

        self.assertEqual(len(Plate(23).quantification_processes), 1)
        self.assertEqual(Plate(23).quantification_processes[0],
                         QuantificationProcess(1))
        self.assertEqual(Plate(22).process, GDNAExtractionProcess(1))

        exp = {'1.SKB1.640202': [[Well(3073), '1.SKB1.640202.Test.plate.1.A1'],
                                 [Well(3121), '1.SKB1.640202.Test.plate.1.A2'],
                                 [Well(3169), '1.SKB1.640202.Test.plate.1.A3'],
                                 [Well(3217), '1.SKB1.640202.Test.plate.1.A4'],
                                 [Well(3265), '1.SKB1.640202.Test.plate.1.A5'],
                                 [Well(3313), '1.SKB1.640202.Test.plate.1.A6'],
                                 [Well(3361), '1.SKB1.640202.Test.plate.1.A7'],
                                 [Well(3409), '1.SKB1.640202.Test.plate.1.A8'],
                                 [Well(3457), '1.SKB1.640202.Test.plate.1.A9'],
                                 [Well(3505),
                                  '1.SKB1.640202.Test.plate.1.A10'],
                                 [Well(3553),
                                  '1.SKB1.640202.Test.plate.1.A11'],
                                 [Well(3601),
                                  '1.SKB1.640202.Test.plate.1.A12']],
               '1.SKB2.640194': [[Well(3079), '1.SKB2.640194.Test.plate.1.B1'],
                                 [Well(3127), '1.SKB2.640194.Test.plate.1.B2'],
                                 [Well(3175), '1.SKB2.640194.Test.plate.1.B3'],
                                 [Well(3223), '1.SKB2.640194.Test.plate.1.B4'],
                                 [Well(3271), '1.SKB2.640194.Test.plate.1.B5'],
                                 [Well(3319), '1.SKB2.640194.Test.plate.1.B6'],
                                 [Well(3367), '1.SKB2.640194.Test.plate.1.B7'],
                                 [Well(3415), '1.SKB2.640194.Test.plate.1.B8'],
                                 [Well(3463), '1.SKB2.640194.Test.plate.1.B9'],
                                 [Well(3511),
                                  '1.SKB2.640194.Test.plate.1.B10'],
                                 [Well(3559),
                                  '1.SKB2.640194.Test.plate.1.B11'],
                                 [Well(3607),
                                  '1.SKB2.640194.Test.plate.1.B12']],
               '1.SKB3.640195': [[Well(3085), '1.SKB3.640195.Test.plate.1.C1'],
                                 [Well(3133), '1.SKB3.640195.Test.plate.1.C2'],
                                 [Well(3181), '1.SKB3.640195.Test.plate.1.C3'],
                                 [Well(3229), '1.SKB3.640195.Test.plate.1.C4'],
                                 [Well(3277), '1.SKB3.640195.Test.plate.1.C5'],
                                 [Well(3325), '1.SKB3.640195.Test.plate.1.C6'],
                                 [Well(3373), '1.SKB3.640195.Test.plate.1.C7'],
                                 [Well(3421), '1.SKB3.640195.Test.plate.1.C8'],
                                 [Well(3469), '1.SKB3.640195.Test.plate.1.C9'],
                                 [Well(3517),
                                  '1.SKB3.640195.Test.plate.1.C10'],
                                 [Well(3565),
                                  '1.SKB3.640195.Test.plate.1.C11'],
                                 [Well(3613),
                                  '1.SKB3.640195.Test.plate.1.C12']],
               '1.SKB4.640189': [[Well(3091), '1.SKB4.640189.Test.plate.1.D1'],
                                 [Well(3139), '1.SKB4.640189.Test.plate.1.D2'],
                                 [Well(3187), '1.SKB4.640189.Test.plate.1.D3'],
                                 [Well(3235), '1.SKB4.640189.Test.plate.1.D4'],
                                 [Well(3283), '1.SKB4.640189.Test.plate.1.D5'],
                                 [Well(3331), '1.SKB4.640189.Test.plate.1.D6'],
                                 [Well(3379), '1.SKB4.640189.Test.plate.1.D7'],
                                 [Well(3427), '1.SKB4.640189.Test.plate.1.D8'],
                                 [Well(3475), '1.SKB4.640189.Test.plate.1.D9'],
                                 [Well(3523),
                                  '1.SKB4.640189.Test.plate.1.D10'],
                                 [Well(3571),
                                  '1.SKB4.640189.Test.plate.1.D11'],
                                 [Well(3619),
                                  '1.SKB4.640189.Test.plate.1.D12']],
               '1.SKB5.640181': [[Well(3097), '1.SKB5.640181.Test.plate.1.E1'],
                                 [Well(3145), '1.SKB5.640181.Test.plate.1.E2'],
                                 [Well(3193), '1.SKB5.640181.Test.plate.1.E3'],
                                 [Well(3241), '1.SKB5.640181.Test.plate.1.E4'],
                                 [Well(3289), '1.SKB5.640181.Test.plate.1.E5'],
                                 [Well(3337), '1.SKB5.640181.Test.plate.1.E6'],
                                 [Well(3385), '1.SKB5.640181.Test.plate.1.E7'],
                                 [Well(3433), '1.SKB5.640181.Test.plate.1.E8'],
                                 [Well(3481), '1.SKB5.640181.Test.plate.1.E9'],
                                 [Well(3529),
                                  '1.SKB5.640181.Test.plate.1.E10'],
                                 [Well(3577),
                                  '1.SKB5.640181.Test.plate.1.E11'],
                                 [Well(3625),
                                  '1.SKB5.640181.Test.plate.1.E12']],
               '1.SKB6.640176': [[Well(3103), '1.SKB6.640176.Test.plate.1.F1'],
                                 [Well(3151), '1.SKB6.640176.Test.plate.1.F2'],
                                 [Well(3199), '1.SKB6.640176.Test.plate.1.F3'],
                                 [Well(3247), '1.SKB6.640176.Test.plate.1.F4'],
                                 [Well(3295), '1.SKB6.640176.Test.plate.1.F5'],
                                 [Well(3343), '1.SKB6.640176.Test.plate.1.F6'],
                                 [Well(3391), '1.SKB6.640176.Test.plate.1.F7'],
                                 [Well(3439), '1.SKB6.640176.Test.plate.1.F8'],
                                 [Well(3487), '1.SKB6.640176.Test.plate.1.F9'],
                                 [Well(3535),
                                  '1.SKB6.640176.Test.plate.1.F10'],
                                 [Well(3583),
                                  '1.SKB6.640176.Test.plate.1.F11']]}
        self.assertEqual(tester.duplicates, exp)
        self.assertEqual(tester.unknown_samples, [])
        exp = tester.get_well(1, 1)
        exp.composition.update('Unknown')
        self.assertEqual(tester.unknown_samples, [exp])
        exp.composition.update('1.SKB1.640202')

        # test that the quantification_processes attribute correctly
        # orders multiple processes in order from oldest to newest
        tester2 = Plate(26)
        self.assertEqual(len(tester2.quantification_processes), 2)
        # we are going to test the dates as string because in the database we
        # have the full date (including seconds)
        obs_date = str(tester2.quantification_processes[0].date)
        self.assertEqual(obs_date, "2017-10-25 19:10:25")
        obs_date = str(tester2.quantification_processes[1].date)
        self.assertEqual(obs_date, "2017-10-26 03:10:25")

    def test_get_well(self):
        # Plate 21 - Defined in the test DB
        tester = Plate(21)
        self.assertEqual(tester.get_well(1, 1), Well(3073))
        self.assertEqual(tester.get_well(1, 2), Well(3121))
        self.assertEqual(tester.get_well(7, 2), Well(3157))
        self.assertEqual(tester.get_well(8, 12), Well(3643))
        with self.assertRaises(LabcontrolError):
            tester.get_well(8, 13)
        with self.assertRaises(LabcontrolError):
            tester.get_well(9, 12)

    def test_get_wells_by_sample(self):
        tester = Plate(21)
        exp = [Well(3073), Well(3121), Well(3169), Well(3217), Well(3265),
               Well(3313), Well(3361), Well(3409), Well(3457), Well(3505),
               Well(3553), Well(3601)]
        self.assertEqual(tester.get_wells_by_sample('1.SKB1.640202'), exp)
        self.assertEqual(tester.get_wells_by_sample('1.SKM1.640183'), [])

    def test_get_previously_plated_wells(self):
        tester = Plate(21)
        three_plates_list = [Plate(27), Plate(30), Plate(33)]
        exp = {Well(3073): three_plates_list, Well(3079): three_plates_list,
               Well(3085): three_plates_list, Well(3091): three_plates_list,
               Well(3097): three_plates_list, Well(3103): three_plates_list,
               Well(3121): three_plates_list, Well(3127): three_plates_list,
               Well(3133): three_plates_list, Well(3139): three_plates_list,
               Well(3145): three_plates_list, Well(3151): three_plates_list,
               Well(3169): three_plates_list, Well(3175): three_plates_list,
               Well(3181): three_plates_list, Well(3187): three_plates_list,
               Well(3193): three_plates_list, Well(3199): three_plates_list,
               Well(3217): three_plates_list, Well(3223): three_plates_list,
               Well(3229): three_plates_list, Well(3235): three_plates_list,
               Well(3241): three_plates_list, Well(3247): three_plates_list,
               Well(3265): three_plates_list, Well(3271): three_plates_list,
               Well(3277): three_plates_list, Well(3283): three_plates_list,
               Well(3289): three_plates_list, Well(3295): three_plates_list,
               Well(3313): three_plates_list, Well(3319): three_plates_list,
               Well(3325): three_plates_list, Well(3331): three_plates_list,
               Well(3337): three_plates_list, Well(3343): three_plates_list,
               Well(3361): three_plates_list, Well(3367): three_plates_list,
               Well(3373): three_plates_list, Well(3379): three_plates_list,
               Well(3385): three_plates_list, Well(3391): three_plates_list,
               Well(3409): three_plates_list, Well(3415): three_plates_list,
               Well(3421): three_plates_list, Well(3427): three_plates_list,
               Well(3433): three_plates_list, Well(3439): three_plates_list,
               Well(3457): three_plates_list, Well(3463): three_plates_list,
               Well(3469): three_plates_list, Well(3475): three_plates_list,
               Well(3481): three_plates_list, Well(3487): three_plates_list,
               Well(3505): three_plates_list, Well(3511): three_plates_list,
               Well(3517): three_plates_list, Well(3523): three_plates_list,
               Well(3529): three_plates_list, Well(3535): three_plates_list,
               Well(3553): three_plates_list, Well(3559): three_plates_list,
               Well(3565): three_plates_list, Well(3571): three_plates_list,
               Well(3577): three_plates_list, Well(3583): three_plates_list,
               Well(3601): three_plates_list, Well(3607): three_plates_list,
               Well(3613): three_plates_list, Well(3619): three_plates_list,
               Well(3625): three_plates_list}
        obs = tester.get_previously_plated_wells()
        self.assertEqual(obs, exp)

        # Create another plate and put a sample on it that isn't anywhere else
        spp = SamplePlatingProcess.create(
            User('test@foo.bar'), PlateConfiguration(1), 'New Plate For Prev')
        spp.update_well(1, 1, '1.SKM1.640184')
        obs = spp.plate.get_previously_plated_wells()
        self.assertEqual(obs, {})


if __name__ == '__main__':
    main()
