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
        self.assertEqual(s.samples('SKB'), exp_samples)
        exp_samples = ['1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                       '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                       '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        self.assertEqual(s.samples('1.SKM'), exp_samples)
        exp_samples = ['1.SKB1.640202', '1.SKD1.640179', '1.SKM1.640183']
        self.assertEqual(s.samples('1.64'), exp_samples)


if __name__ == '__main__':
    main()
