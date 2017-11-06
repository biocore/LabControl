# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------


from labman.db.base import LabmanObject
from labman.db.sql_connection import TRN
from labman.db.plate import Plate


class _Container(LabmanObject):
    """Container object

    Attributes
    ----------
    id
    remaining_volume
    notes
    latest_process
    """
    def _get_container_attr(self, attr):
        """Returns the value of the given container attribute

        Parameters
        ----------
        attr : str
            The attribute to retrieve

        Returns
        -------
        Object
            The attribute
        """
        with TRN:
            sql = """SELECT {}
                     FROM qiita.container
                        JOIN {} USING container_id
                     WHERE {} = %s""".format(attr, self._table,
                                             self._id_column)
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def remaining_volume(self):
        """The remaining volume of the container"""
        return self._get_container_attr('remaining_volume')

    @property
    def notes(self):
        """The container notes"""
        return self._get_container_attr('notes')

    @property
    def latest_process(self):
        """The latest process applied to the container"""
        # TODO: Once the process object exists, return the process object
        # instead of the id
        return self._get_container_attr('latest_upstream_process_id')


class Tube(_Container):
    """Tube object

    Attributes
    ----------
    external_id
    discarded

    See Also
    --------
    _Container
    """

    _table = "qiita.tube"
    _id_column = "tube_id"

    @property
    def external_id(self):
        """The tube external identifier"""
        return self._get_attr('external_id')

    @property
    def discarded(self):
        """Whether the tube is discarded or not"""
        return self._get_attr('discarded')


class Well(_Container):
    """Well object

    Attributes
    ----------
    plate
    row
    column

    See Also
    --------
    _Container
    """
    _table = "qiita.well"
    _id_column = "well_id"

    @property
    def plate(self):
        """The plate the well belongs to"""
        return Plate(self._get_attr('plate_id'))

    @property
    def row(self):
        """The well row"""
        return self._get_attr('row_num')

    @property
    def column(self):
        """The well column"""
        return self._get_attr('col_num')
