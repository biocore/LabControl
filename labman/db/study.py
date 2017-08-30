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
