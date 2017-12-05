# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import plate
from . import process


class _Container(base.LabmanObject):
    """Container object

    Attributes
    ----------
    id
    remaining_volume
    notes
    latest_process
    """
    @classmethod
    def _common_creation_steps(cls, process, remaining_volume):
        with sql_connection.TRN as TRN:
            sql = """SELECT container_type_id
                     FROM qiita.container_type
                     WHERE description = %s"""
            TRN.add(sql, [cls._container_type])
            ct_id = TRN.execute_fetchlast()

            sql = """INSERT INTO qiita.container
                        (container_type_id, latest_upstream_process_id,
                         remaining_volume)
                     VALUES (%s, %s, %s)
                     RETURNING container_id"""
            TRN.add(sql, [ct_id, process.process_id, remaining_volume])
            container_id = TRN.execute_fetchlast()

        return container_id

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
        with sql_connection.TRN as TRN:
            sql = """SELECT {}
                     FROM qiita.container
                        JOIN {} USING (container_id)
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
        return process.Process.factory(
            self._get_container_attr('latest_upstream_process_id'))

    @property
    def container_id(self):
        return self._get_container_attr('container_id')


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

    def discard(self):
        """Discard the tube

        Raises
        ------
        ValueError
            If the tube was already discarded
        """
        if self.discarded:
            raise ValueError("Can't discard tube %s: it's already discarded."
                             % self.id)
        self._set_attr('discarded', True)


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
    _container_type = 'well'

    @classmethod
    def create(cls, plate, process, volume, row, col):
        """Creates a new well

        Parameters
        ----------
        plate: labman.db.Plate
            The plate to which this well belongs to
        process: labman.db.Process
            The process that generated this well
        volume : float
            The initial volume of the well
        row : int
            The row number of the well
        col : int
            The column number of the well

        Returns
        -------
        labman.db.Well
        """
        with sql_connection.TRN as TRN:
            container_id = cls._common_creation_steps(process, volume)
            sql = """INSERT INTO qiita.well
                        (container_id, plate_id, row_num, col_num)
                     VALUES (%s, %s, %s, %s)
                     RETURNING well_id"""
            TRN.add(sql, [container_id, plate.id, row, col])
            well_id = TRN.execute_fetchlast()
        return cls(well_id)

    @property
    def plate(self):
        """The plate the well belongs to"""
        return plate.Plate(self._get_attr('plate_id'))

    @property
    def row(self):
        """The well row"""
        return self._get_attr('row_num')

    @property
    def column(self):
        """The well column"""
        return self._get_attr('col_num')
