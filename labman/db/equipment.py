# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import exceptions


class Equipment(base.LabmanObject):
    """Equipment object

    Attributes
    ----------
    id
    external_id
    equipment_type
    notes
    """
    _table = 'qiita.equipment'
    _id_column = 'equipment_id'

    @staticmethod
    def list_equipment(equipment_type=None):
        """Generates a list of equipment

        Parameters
        ----------
        equipment_type: str, optional
            If provided, limit the equipment list to the given type

        Returns
        -------
        list of dicts
            The list of equipment information with the structure:
            [{'equipment_id': int, 'external_id': string}]
        """
        with sql_connection.TRN as TRN:
            sql_where = ('WHERE description = %s'
                         if equipment_type is not None else '')
            sql = """SELECT equipment_id, external_id
                     FROM qiita.equipment
                        JOIN qiita.equipment_type USING (equipment_type_id)
                     {}
                     ORDER BY equipment_id""".format(sql_where)
            TRN.add(sql, [equipment_type])
            return [dict(r) for r in TRN.execute_fetchindex()]

    @staticmethod
    def list_equipment_types():
        """Generates a list of equipment types

        Returns
        -------
        list of str
            The list of equipment type strings
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM qiita.equipment_type
                     ORDER BY equipment_type_id"""
            TRN.add(sql)
            return TRN.execute_fetchflatten()

    @classmethod
    def create_type(cls, description):
        """Creates a new equipment type in the system

        Parameters
        ----------
        description : str
            The description of the new type

        Raises
        ------
        LabmanDuplicateError
            If the given type already exists
        """
        with sql_connection.TRN as TRN:
            # Check if the equipment type already exists
            sql = """SELECT EXISTS(SELECT 1 FROM qiita.equipment_type
                                   WHERE description = %s)"""
            TRN.add(sql, [description])
            if TRN.execute_fetchlast():
                raise exceptions.LabmanDuplicateError(
                    'Equipment type', [('description', description)])

            # Proceed to create the new type
            sql = "INSERT INTO qiita.equipment_type (description) VALUES (%s)"
            TRN.add(sql, [description])
            TRN.execute()

    @classmethod
    def create(cls, equipment_type, external_id, notes=None):
        """Creates a new equipment item in the system

        Parameters
        ----------
        equipment_type : str
            The equipment type
        external_id : str
            The equipment's external id
        notes : str, optional
            Equipments notes

        Returns
        -------
        Equipment
            The newly created equipment

        Raises
        ------
        LabmanUnknownIdError
            If the equipment_type is not recognized
        LabmanDuplicateError
            If an equipment with the given external id already exists
        """
        with sql_connection.TRN as TRN:
            # Check if the equipment type exists by getting his id
            sql = """SELECT equipment_type_id
                     FROM qiita.equipment_type
                     WHERE description = %s"""
            TRN.add(sql, [equipment_type])
            res = TRN.execute_fetchindex()
            if res:
                # Fetchindex returns a list of results. If the previous call
                # didn't return anything the list would be empty, and accessing
                # to this values would've generated and IndexError. By the DB
                # constraints, the above query can at most return one result
                # with a single value, hence the [0][0]
                equipment_type_id = res[0][0]
            else:
                raise exceptions.LabmanUnknownIdError(
                    'Equipment type', equipment_type)

            # Check if there is already an equipment with the external id
            if cls._attr_exists('external_id', external_id):
                raise exceptions.LabmanDuplicateError(
                    'Equipment', [('external id', external_id)])

            # Proceed to create the new quipment
            sql = """INSERT INTO qiita.equipment
                        (external_id, equipment_type_id, notes)
                     VALUES (%s, %s, %s)
                     RETURNING equipment_id"""
            TRN.add(sql, [external_id, equipment_type_id, notes])
            return cls(TRN.execute_fetchlast())

    @property
    def external_id(self):
        """The equipment's external identifier"""
        return self._get_attr('external_id')

    @property
    def equipment_type(self):
        """The type of the equipment"""
        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM qiita.equipment_type
                        JOIN qiita.equipment USING (equipment_type_id)
                     WHERE equipment_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def notes(self):
        """The equipment notes"""
        return self._get_attr('notes')

    @notes.setter
    def notes(self, value):
        """Set the new value for the notes attribute"""
        self._set_attr('notes', value)
