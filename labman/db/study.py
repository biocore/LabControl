# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.base import LabmanObject


class Study(LabmanObject):
    """Study object

    Attributes
    ----------
    id
    title
    creator
    creation_timestamp
    qiita_study_id
    jira_key

    Methods
    -------
    create
    title_exists
    """
    _table = "study.study"
    _id_columns = "study_id"

    @classmethod
    def title_exists(cls, title):
        """Checks if the provided title already exists

        Parameters
        ----------
        title : str
            The title to check for

        Returns
        -------
        bool
            Whether the title exists or not
        """
        pass

    @classmethod
    def create(cls, title, creator):
        """Creates a new study in the system

        Parameters
        ----------
        title : str
            The study title
        creator : User
            The user creating the study

        Returns
        -------
        Study
            The newly created study

        Raises
        ------
        LabmanDuplicateError
            If the given title already exists
        """
        pass

    @property
    def title(self):
        """The study title"""
        pass

    @property
    def creator(self):
        """The user that created the study"""
        pass

    @property
    def creation_timestamp(self):
        """Creation timestamp"""
        pass

    @property
    def qiita_study_id(self):
        """The qiita study id"""
        pass

    @property
    def jira_key(self):
        """The jira key"""
        pass
