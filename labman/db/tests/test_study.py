# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from unittest import main

from labman.db.testing import LabmanTestCase
from labman.db.exceptions import LabmanUnknownIdError
from labman.db.study import Study
from labman.db.user import User


class TestStudy(LabmanTestCase):
    def test_list_studies(self):
        obs = Study.list_studies()
        exp = [{'study_id': 1,
                'study_title': 'Identification of the Microbiomes for '
                               'Cannabis Soils',
                'study_alias': 'Cannabis Soils',
                'owner': 'test@foo.bar',
                'num_samples': 27}]
        self.assertEqual(obs, exp)

    def test_init(self):
        with self.assertRaises(LabmanUnknownIdError):
            Study(1000000)

    def test_attributes(self):
        s = Study(1)
        self.assertEqual(s.title, 'Identification of the Microbiomes '
                                  'for Cannabis Soils')
        self.assertEqual(s.creator, User('test@foo.bar'))
        self.assertEqual(s.num_samples, 27)
        exp = {'num_samples': 27,
               'number_samples_plated': 12,
               'number_samples_extracted': 12,
               'number_samples_amplicon_libraries': 12,
               'number_samples_amplicon_pools': 12,
               'number_samples_amplicon_sequencing_pools': 12,
               'number_samples_amplicon_sequencing_runs': 12,
               'number_samples_compressed': 12,
               'number_samples_normalized': 12,
               'number_samples_shotgun_libraries': 12,
               'number_samples_shotgun_pool': 12,
               'number_samples_shotgun_sequencing_runs': 12}
        self.assertEqual(s.sample_numbers_summary, exp)

    def test_samples(self):
        s = Study(1)
        exp_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                       '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                       '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                       '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                       '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                       '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                       '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                       '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                       '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        self.assertEqual(s.samples(), exp_samples)
        exp_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                       '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                       '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200']
        self.assertEqual(s.samples(limit=9), exp_samples)
        exp_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                       '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                       '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200']
        self.assertEqual(s.samples('SKB'), exp_samples)
        exp_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195']
        self.assertEqual(s.samples('SKB', limit=3), exp_samples)
        exp_samples = ['1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                       '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                       '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        self.assertEqual(s.samples('1.SKM'), exp_samples)
        exp_samples = ['1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                       '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                       '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        self.assertEqual(s.samples('1.Skm'), exp_samples)  # case insensitive
        exp_samples = ['1.SKB1.640202', '1.SKD1.640179', '1.SKM1.640183']
        self.assertEqual(s.samples('1.64'), exp_samples)

    def test_generate_sample_plate_maps(self):
        obs = Study(1).generate_sample_plate_maps()
        exp = (
            'Plate "Test plate 1" (ID: 21)\n'
            ',1,2,3,4,5,6,7,8,9,10,11,12\n'
            'A,1.SKB1.640202.21.A1,1.SKB2.640194.21.A2,1.SKB3.640195.21.A3'
            ',1.SKB4.640189.21.A4,1.SKB5.640181.21.A5,1.SKB6.640176.21.A6,'
            '1.SKB7.640196.21.A7,1.SKB8.640193.21.A8,1.SKB9.640200.21.A9,'
            '1.SKD1.640179.21.A10,1.SKD2.640178.21.A11,'
            '1.SKD3.640198.21.A12\n'
            'B,1.SKB1.640202.21.B1,1.SKB2.640194.21.B2,1.SKB3.640195.21.B3'
            ',1.SKB4.640189.21.B4,1.SKB5.640181.21.B5,1.SKB6.640176.21.B6,'
            '1.SKB7.640196.21.B7,1.SKB8.640193.21.B8,1.SKB9.640200.21.B9,'
            '1.SKD1.640179.21.B10,1.SKD2.640178.21.B11,'
            '1.SKD3.640198.21.B12\n'
            'C,1.SKB1.640202.21.C1,1.SKB2.640194.21.C2,1.SKB3.640195.21.C3'
            ',1.SKB4.640189.21.C4,1.SKB5.640181.21.C5,1.SKB6.640176.21.C6,'
            '1.SKB7.640196.21.C7,1.SKB8.640193.21.C8,1.SKB9.640200.21.C9,'
            '1.SKD1.640179.21.C10,1.SKD2.640178.21.C11,'
            '1.SKD3.640198.21.C12\n'
            'D,1.SKB1.640202.21.D1,1.SKB2.640194.21.D2,1.SKB3.640195.21.D3'
            ',1.SKB4.640189.21.D4,1.SKB5.640181.21.D5,1.SKB6.640176.21.D6,'
            '1.SKB7.640196.21.D7,1.SKB8.640193.21.D8,1.SKB9.640200.21.D9,'
            '1.SKD1.640179.21.D10,1.SKD2.640178.21.D11,'
            '1.SKD3.640198.21.D12\n'
            'E,1.SKB1.640202.21.E1,1.SKB2.640194.21.E2,1.SKB3.640195.21.E3'
            ',1.SKB4.640189.21.E4,1.SKB5.640181.21.E5,1.SKB6.640176.21.E6,'
            '1.SKB7.640196.21.E7,1.SKB8.640193.21.E8,1.SKB9.640200.21.E9,'
            '1.SKD1.640179.21.E10,1.SKD2.640178.21.E11,'
            '1.SKD3.640198.21.E12\n'
            'F,1.SKB1.640202.21.F1,1.SKB2.640194.21.F2,1.SKB3.640195.21.F3'
            ',1.SKB4.640189.21.F4,1.SKB5.640181.21.F5,1.SKB6.640176.21.F6,'
            '1.SKB7.640196.21.F7,1.SKB8.640193.21.F8,1.SKB9.640200.21.F9,'
            '1.SKD1.640179.21.F10,1.SKD2.640178.21.F11,'
            '1.SKD3.640198.21.F12\n'
            'G,vibrio.positive.control.21.G1,vibrio.positive.control.21.G2,'
            'vibrio.positive.control.21.G3,vibrio.positive.control.21.G4,'
            'vibrio.positive.control.21.G5,vibrio.positive.control.21.G6,'
            'vibrio.positive.control.21.G7,vibrio.positive.control.21.G8,'
            'vibrio.positive.control.21.G9,vibrio.positive.control.21.G10,'
            'vibrio.positive.control.21.G11,vibrio.positive.control.21.G12\n'
            'H,blank.21.H1,blank.21.H2,blank.21.H3,blank.21.H4,'
            'blank.21.H5,blank.21.H6,blank.21.H7,blank.21.H8,blank.21.H9,'
            'blank.21.H10,blank.21.H11,empty.21.H12')
        self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
