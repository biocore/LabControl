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
from labman.db import sql_connection


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
               'number_samples_plated': 10,
               'number_samples_extracted': 10,
               'number_samples_amplicon_libraries': 10,
               'number_samples_amplicon_pools': 10,
               'number_samples_amplicon_sequencing_pools': 10,
               'number_samples_amplicon_sequencing_runs': 10,
               'number_samples_compressed': 10,
               'number_samples_normalized': 10,
               'number_samples_shotgun_libraries': 10,
               'number_samples_shotgun_pool': 10,
               'number_samples_shotgun_sequencing_runs': 10}
        self.assertEqual(s.sample_numbers_summary, exp)

    def test_samples_with_sample_id(self):
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

    def test_samples_with_specimen_id(self):
        s = Study(1)

        # HACK: the Study object in labman can't modify specimen_id_column
        # hence we do this directly in SQL, if a test fails the transaction
        # will rollback, otherwise we reset the column to NULL.
        sql = """UPDATE qiita.study
                 SET specimen_id_column = %s
                 WHERE study_id = 1"""
        with sql_connection.TRN as TRN:
            TRN.add(sql, ['anonymized_name'])

            exp_samples = ['SKB1', 'SKB2', 'SKB3',
                           'SKB4', 'SKB5', 'SKB6',
                           'SKB7', 'SKB8', 'SKB9',
                           'SKD1', 'SKD2', 'SKD3',
                           'SKD4', 'SKD5', 'SKD6',
                           'SKD7', 'SKD8', 'SKD9',
                           'SKM1', 'SKM2', 'SKM3',
                           'SKM4', 'SKM5', 'SKM6',
                           'SKM7', 'SKM8', 'SKM9']
            self.assertEqual(s.samples(), exp_samples)
            exp_samples = ['SKB1', 'SKB2', 'SKB3',
                           'SKB4', 'SKB5', 'SKB6',
                           'SKB7', 'SKB8', 'SKB9']
            self.assertEqual(s.samples(limit=9), exp_samples)
            exp_samples = ['SKB1', 'SKB2', 'SKB3',
                           'SKB4', 'SKB5', 'SKB6',
                           'SKB7', 'SKB8', 'SKB9']
            self.assertEqual(s.samples('SKB'), exp_samples)
            exp_samples = ['SKB1', 'SKB2', 'SKB3']
            self.assertEqual(s.samples('SKB', limit=3), exp_samples)
            exp_samples = ['SKM1', 'SKM2', 'SKM3',
                           'SKM4', 'SKM5', 'SKM6',
                           'SKM7', 'SKM8', 'SKM9']
            self.assertEqual(s.samples('SKM'), exp_samples)
            exp_samples = ['SKM1', 'SKM2', 'SKM3',
                           'SKM4', 'SKM5', 'SKM6',
                           'SKM7', 'SKM8', 'SKM9']
            # case insensitive
            self.assertEqual(s.samples('Skm'), exp_samples)
            self.assertEqual(s.samples('64'), [])

            TRN.add(sql, [None])

    def test_specimen_id_column(self):
        s = Study(1)
        self.assertIsNone(s.specimen_id_column)

    def test_translate_ids_with_sample_id(self):
        # Tests sample_id_to_specimen_id and specimen_id_to_sample_id when
        # there is no specimen identifier set for the study
        s = Study(1)

        obs = s.sample_id_to_specimen_id('1.SKM4.640180')
        self.assertEqual(obs, '1.SKM4.640180')

        # doesn't even need to be a valid sample id
        obs = s.sample_id_to_specimen_id('SKM3')
        self.assertEqual(obs, 'SKM3')

        with self.assertRaisesRegex(ValueError, 'Could not find "SKM4"'):
            s.specimen_id_to_sample_id('SKM4')

        with self.assertRaisesRegex(ValueError, 'Could not find "SSSS"'):
            s.specimen_id_to_sample_id('SSSS')

    def test_translate_ids_with_specimen_id(self):
        s = Study(1)
        # HACK: the Study object in labman can't modify specimen_id_column
        # hence we do this directly in SQL, if a test fails the transaction
        # will rollback, otherwise we reset the column to NULL.
        sql = """UPDATE qiita.study
                 SET specimen_id_column = %s
                 WHERE study_id = 1"""
        with sql_connection.TRN as TRN:
            TRN.add(sql, ['anonymized_name'])

            obs = s.sample_id_to_specimen_id('1.SKM4.640180')
            self.assertEqual(obs, 'SKM4')

            obs = s.specimen_id_to_sample_id('SKM4')
            self.assertEqual(obs, '1.SKM4.640180')

            # should be an exact match
            with self.assertRaisesRegex(ValueError,
                                        ('Could not find '
                                         '\"1.skm4.640180\"')):
                s.sample_id_to_specimen_id('1.skm4.640180')
            with self.assertRaisesRegex(ValueError,
                                        'Could not find \"skm4\"'):
                s.specimen_id_to_sample_id('skm4')

            # raise an error in the rare case that the specimen_id_column was
            # set to something that's not unique (this could only accidentally
            # happen)
            TRN.add(sql, ['taxon_id'])
            with self.assertRaisesRegex(RuntimeError, 'There are several '
                                        'matches found for "1118232"; there is'
                                        ' a problem with the specimen id '
                                        'column'):
                s.specimen_id_to_sample_id('1118232')

            TRN.add(sql, [None])


if __name__ == '__main__':
    main()
