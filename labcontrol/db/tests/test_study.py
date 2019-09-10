# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from math import floor
from unittest import main

from labcontrol.db.testing import LabControlTestCase
from labcontrol.db.exceptions import LabControlUnknownIdError
from labcontrol.db.study import Study
from labcontrol.db.user import User
from labcontrol.db import sql_connection


class TestStudy(LabControlTestCase):
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
        with self.assertRaises(LabControlUnknownIdError):
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
        self.assertEqual(s.samples(limit='9'), exp_samples)
        exp_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                       '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                       '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200']
        self.assertEqual(s.samples('SKB'), exp_samples)
        exp_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195']
        self.assertEqual(s.samples('SKB', limit='3'), exp_samples)
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

    def test_samples_with_limit(self):
        """Unit-tests the `limit` argument of Study.samples() in particular.

        It's worth noting that the `limit` value that StudySamplesHandler.get()
        uses when calling Study.samples() is actually a string -- this is due
        to our use of tornado.web.RequestHandler.get_argument().
        Study.samples() only cares that `int(limit)` succeeds, and is otherwise
        agnostic to the actual input type of `limit`.

        (For the sake of caution, we test a couple of types besides purely
        `str` values within this function.)
        """
        s = Study(1)
        all_samples = ['1.SKB1.640202', '1.SKB2.640194', '1.SKB3.640195',
                       '1.SKB4.640189', '1.SKB5.640181', '1.SKB6.640176',
                       '1.SKB7.640196', '1.SKB8.640193', '1.SKB9.640200',
                       '1.SKD1.640179', '1.SKD2.640178', '1.SKD3.640198',
                       '1.SKD4.640185', '1.SKD5.640186', '1.SKD6.640190',
                       '1.SKD7.640191', '1.SKD8.640184', '1.SKD9.640182',
                       '1.SKM1.640183', '1.SKM2.640199', '1.SKM3.640197',
                       '1.SKM4.640180', '1.SKM5.640177', '1.SKM6.640187',
                       '1.SKM7.640188', '1.SKM8.640201', '1.SKM9.640192']
        # Check cases where the limit is valid but doesn't actually result in
        # any filtering being done.
        self.assertEqual(s.samples(), all_samples)
        for i in [27, 28, 50, 100, 10000]:
            self.assertEqual(s.samples(limit=i), all_samples)
            self.assertEqual(s.samples(limit=str(i)), all_samples)
        # limit=None is the default, but we check it here explicitly anyway.
        self.assertEqual(s.samples(limit=None), all_samples)

        # Check *all* limit values in the inclusive range [1, 27] -- these
        # should, well, limit the output list of samples accordingly
        for i in range(1, len(all_samples)):
            self.assertEqual(s.samples(limit=i), all_samples[:i])
            self.assertEqual(s.samples(limit=str(i)), all_samples[:i])

        float_limits_to_test = [1.0, 1.2, 3.0, 27.0, 29.1, 1000.0]
        str_of_float_limits_to_test = [str(f) for f in float_limits_to_test]

        # Test that various not-castable-to-a-base-10-int inputs don't work
        # (This includes string representations of floats, e.g. "1.0", since
        # such a string is not a valid "integer literal" -- see
        # https://docs.python.org/3/library/functions.html#int.
        uncastable_limits_to_test = [
            [1, 2, 3], "abc", "gibberish", "ten", (1,), "0xBEEF", "0b10101",
            "0o123", float("inf"), float("-inf"), float("nan"), "None", "inf"
        ]
        for i in uncastable_limits_to_test + str_of_float_limits_to_test:
            with self.assertRaisesRegex(
                ValueError, "limit must be castable to an int"
            ):
                s.samples(limit=i)

        # Calling int(x) where x is a float just truncates x "towards zero"
        # according to https://docs.python.org/3/library/functions.html#int.
        #
        # This behavior is tested, but it should never happen (one, because
        # as of writing Study.samples() is only called with a string limit
        # value, and two because I can't imagine why someone would pass a float
        # in for the "limit" argument).
        for i in float_limits_to_test:
            self.assertEqual(s.samples(limit=i), all_samples[:floor(i)])

        # Check that limits <= 0 cause an error
        nonpositive_limits = [0, -1, -2, -27, -53, -100]
        for i in nonpositive_limits:
            with self.assertRaisesRegex(
                ValueError, "limit must be greater than zero"
            ):
                s.samples(limit=i)

        # Check evil corner case where the limit is nonpositive and not
        # castable to an int (this should fail first on the castable check)
        with self.assertRaisesRegex(
            ValueError, "limit must be castable to an int"
        ):
            s.samples(limit="-1.0")

    def test_samples_with_specimen_id(self):
        s = Study(1)

        # HACK: the Study object in labcontrol can't modify specimen_id_column
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
        # HACK: the Study object in labcontrol can't modify specimen_id_column
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
                                        'Could not find \"1\.skm4\.640180\"'):
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
