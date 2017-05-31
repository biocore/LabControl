# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.sql_connection import TRN
from labman.db.exceptions import LabmanUnknownIdError


class LabmanObject(object):
    """Base class for any Labman object

    Parameters
    ----------
    id_: int
        The object id

    Attributes
    ----------
    id

    Methods
    -------
    exists

    Raises
    ------
    LabmanUnknownIdError
        If the id does not reference a known object
    """

    _table = None
    _id_column = None

    def __init__(self, id_):
        if not self.exists(id_):
            raise LabmanUnknownIdError(self._table, id_)
        self._id = id_

    @classmethod
    def _attr_exists(cls, attr, value):
        """Returns whether the attribute with the given value exists

        Parameters
        ----------
        attr: str
            The attribute to check
        value : object
            The value to check for

        Returns
        -------
        bool
            Whether the given attribute value exists
        """
        with TRN:
            sql = "SELECT EXISTS(SELECT 1 FROM {} WHERE {} = %s)".format(
                cls._table, attr)
            TRN.add(sql, [value])
            return TRN.execute_fetchlast()

    @classmethod
    def exists(cls, id_):
        """Returns whether an object with the given id exists or not

        Parameters
        ----------
        id_ : int
            The id to test for

        Returns
        -------
        bool
            Whether the object with the given id exists or not
        """
        return cls._attr_exists(cls._id_column, id_)

    @property
    def id(self):
        """The object id"""
        return self._id

    def __eq__(self, other):
        """Self and other are equal based on type and id"""
        if type(self) != type(other):
            return False
        if other._id != self._id:
            return False
        return True

    def __ne__(self, other):
        """Self and other are not equal based on type and id"""
        return not self.__eq__(other)

    def __hash__(self, other):
        """The hash of an object is based on the type and id"""
        return hash(b"%s: %d" % (self._table, self.id))
