# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.base import LabmanObject
from labman.db.user import User
from labman.db.sql_connection import TRN


class Study(LabmanObject):
    """Study object

    Attributes
    ----------
    id
    title
    creator
    samples

    See Also
    --------
    labman.db.base.LabmanObject
    """
    _table = "qiita.study"
    _id_column = "study_id"

    @classmethod
    def list_studies(cls):
        """Generates a list of studies with some information about them

        Returns
        -------
        list of dicts
            The list of studies with a dictionary with the structure:
            {'study_id': int, 'study_title': string, 'study_alias': string,
             'owner': string, 'num_samples': int}
        """
        with TRN:
            sql = """SELECT study_id, study_title, study_alias, email as owner,
                            COUNT(sample_id) as num_samples
                     FROM qiita.study
                        LEFT JOIN qiita.study_sample USING (study_id)
                     GROUP BY study_id, study_title, study_alias, email
                     ORDER BY study_id"""
            TRN.add(sql)
            return [dict(r) for r in TRN.execute_fetchindex()]

    @property
    def title(self):
        """The study title"""
        return self._get_attr('study_title')

    @property
    def creator(self):
        """The user that created the study"""
        return User(self._get_attr('email'))

    @property
    def samples(self):
        """The study samples"""
        with TRN:
            sql = """SELECT sample_id
                     FROM qiita.study_sample
                     WHERE study_id = %s
                     ORDER BY sample_id"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchflatten()

    @property
    def num_samples(self):
        """The number of samples in the study"""
        with TRN:
            sql = """SELECT count(sample_id)
                     FROM qiita.study_sample
                     WHERE study_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()
