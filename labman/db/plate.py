# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import container


class PlateConfiguration(base.LabmanObject):
    """Plate configuration object

    Attributes
    ----------
    id
    description
    num_rows
    num_columns

    Methods
    -------
    create
    """
    _table = "qiita.plate_configuration"
    _id_column = "plate_configuration_id"

    @classmethod
    def create(cls, description, num_rows, num_columns):
        """Creates a new plate configuration

        Parameters
        ----------
        description : str
            The description of the new plate configuration
        num_rows : int
            The number of rows
        num_columns : int
            The number of columns

        Returns
        -------
        PlateConfiguration
            The newly created plate configuration
        """
        with sql_connection.TRN as TRN:
            sql = """INSERT INTO qiita.plate_configuration
                        (description, num_rows, num_columns)
                    VALUES (%s, %s, %s)
                    RETURNING plate_configuration_id"""
            TRN.add(sql, [description, num_rows, num_columns])
            return cls(TRN.execute_fetchlast())

    @property
    def description(self):
        """The plate configuration description"""
        return self._get_attr('description')

    @property
    def num_rows(self):
        """The number of rows"""
        return self._get_attr('num_rows')

    @property
    def num_columns(self):
        """The number of columns"""
        return self._get_attr('num_columns')


class Plate(base.LabmanObject):
    """Plate object

    Attributes
    ----------
    id
    external_id
    plate_configuration
    discarded
    notes

    Methods
    -------
    create
    """
    _table = "qiita.plate"
    _id_column = "plate_id"

    @classmethod
    def create(cls, external_id, plate_configuration):
        """Creates a new plate

        Parameters
        ----------
        external_id : str
            The external identifier of the plate
        plate_configuration : PlateConfiguration
            The plate configuration

        Returns
        -------
        Plate
            The newly created plate
        """
        with sql_connection.TRN as TRN:
            sql = """INSERT INTO qiita.plate
                        (external_id, plate_configuration_id)
                    VALUES (%s, %s)
                    RETURNING plate_id"""
            TRN.add(sql, [external_id, plate_configuration.id])
            return cls(TRN.execute_fetchlast())

    @property
    def external_id(self):
        """The plate external identifier"""
        return self._get_attr('external_id')

    @property
    def plate_configuration(self):
        """The plate configuration"""
        return PlateConfiguration(self._get_attr('plate_configuration_id'))

    @property
    def discarded(self):
        """Whether the plate is discarded or not"""
        return self._get_attr('discarded')

    @property
    def notes(self):
        """The plate notes"""
        return self._get_attr('notes')

    @property
    def layout(self):
        """Returns a matrix containing the wells of the plate

        Returns
        -------
        list of list of labman.db.Well
        """
        with sql_connection.TRN as TRN:
            pc = self.plate_configuration
            layout = []
            for i in range(pc.num_rows):
                layout.append([None] * pc.num_columns)

            sql = """SELECT well_id, row_num, col_num
                     FROM qiita.well
                     WHERE plate_id = %s"""
            TRN.add(sql, [self.id])

            for well_id, row, col in TRN.execute_fetchindex():
                layout[row-1][col-1] = container.Well(well_id)

        return layout
