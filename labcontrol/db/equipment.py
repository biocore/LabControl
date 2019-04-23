# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import exceptions


class Equipment(base.LabControlObject):
    """Equipment object

    Attributes
    ----------
    id
    external_id
    equipment_type
    notes
    """
    _table = 'labman.equipment'
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
                     FROM labman.equipment
                        JOIN labman.equipment_type USING (equipment_type_id)
                     {}
                     ORDER BY external_id""".format(sql_where)
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
                     FROM labman.equipment_type
                     ORDER BY description"""
            TRN.add(sql)
            result = TRN.execute_fetchflatten()

            # Ugh--whether or not postgres sort results are case-sensitive
            # depends on the OS on which postgres is run (see
            # https://dba.stackexchange.com/questions/106964/why-is-my-
            # postgresql-order-by-case-insensitive ) so on mac they
            # are and on linux they aren't.  Equipment types are being named
            # according to manufacturer branding (e.g., it is a "mosquito", not
            # a "Mosquito", but a "MiSeq" not a "miSeq") so sort
            # explicitly to ensure same results regardless of OS, mostly for
            # the benefit of the unit tests.
            return sorted(result, key=str.lower)

    @classmethod
    def create_type(cls, description):
        """Creates a new equipment type in the system

        Parameters
        ----------
        description : str
            The description of the new type

        Raises
        ------
        LabControlDuplicateError
            If the given type already exists
        """
        with sql_connection.TRN as TRN:
            # Check if the equipment type already exists
            sql = """SELECT EXISTS(SELECT 1 FROM labman.equipment_type
                                   WHERE description = %s)"""
            TRN.add(sql, [description])
            if TRN.execute_fetchlast():
                raise exceptions.LabControlDuplicateError(
                    'Equipment type', [('description', description)])

            # Proceed to create the new type
            sql = "INSERT INTO labman.equipment_type (description) VALUES (%s)"
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
        LabControlUnknownIdError
            If the equipment_type is not recognized
        LabControlDuplicateError
            If an equipment with the given external id already exists
        """
        with sql_connection.TRN as TRN:
            # Check if the equipment type exists by getting his id
            sql = """SELECT equipment_type_id
                     FROM labman.equipment_type
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
                raise exceptions.LabControlUnknownIdError(
                    'Equipment type', equipment_type)

            # Check if there is already an equipment with the external id
            if cls._attr_exists('external_id', external_id):
                raise exceptions.LabControlDuplicateError(
                    'Equipment', [('external id', external_id)])

            # Proceed to create the new quipment
            sql = """INSERT INTO labman.equipment
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
                     FROM labman.equipment_type
                        JOIN labman.equipment USING (equipment_type_id)
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
