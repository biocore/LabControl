# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import container as container_module
from . import exceptions as exceptions_module
from . import process as process_module


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
    def iter(cls):
        """Returns a generator over all the plate configurations available

        Returns
        -------
        Generator of labman.db.plate.PlateConfiguration
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT plate_configuration_id
                     FROM qiita.plate_configuration
                     ORDER BY plate_configuration_id"""
            TRN.add(sql)
            for pc_id in TRN.execute_fetchflatten():
                yield cls(pc_id)

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

    @staticmethod
    def search(samples=None, plate_notes=None, well_notes=None,
               query_type='INTERSECT'):
        """Search plates

        Parameters
        ----------
        samples: list of str, optional
            The samples to find in the plates
        plate_notes : str, optional
            The plate notes string to search for. Default: None
        well_notes : str, optional
            The well notes string to search for. Default: None
        query_type : {INTERSECT, UNION}
            Whether to return the results that fullfill all of the search
            restrictions or just one of them. Defaul: INTERSECT
        """
        if samples is None and plate_notes is None and well_notes is None:
            raise ValueError(
                'Please, provide at least on of samples, plate_notes or '
                'well_notes to perform a plate search.')

        if query_type not in ('INTERSECT', 'UNION'):
            raise ValueError('query_type should be INTERSECT or UNION. Found:'
                             ' %s' % query_type)

        with sql_connection.TRN as TRN:
            sql_queries = []
            sql_args = []
            if samples:
                sql_queries.append(
                    """SELECT DISTINCT plate_id
                       FROM qiita.well
                            JOIN qiita.composition USING (container_id)
                            JOIN qiita.sample_composition
                                USING (composition_id)
                       WHERE sample_id IN %s""")
                sql_args.append(tuple(samples))
            if plate_notes:
                sql_queries.append(
                    """SELECT plate_id
                       FROM qiita.plate
                       WHERE notes @@ to_tsquery(%s)""")
                sql_args.append(
                    ' & '.join([w for w in plate_notes.split(' ') if w]))
            if well_notes:
                sql_queries.append(
                    """SELECT plate_id
                       FROM qiita.well
                            JOIN qiita.composition USING (container_id)
                       WHERE notes @@ to_tsquery(%s)""")
                sql_args.append(
                    ' & '.join([w for w in well_notes.split(' ') if w]))

            if len(sql_queries) > 1:
                sql = (" %s " % query_type).join(sql_queries)
            else:
                sql = sql_queries[0]
            TRN.add(sql, sql_args)
            res = [Plate(pid) for pid in TRN.execute_fetchflatten()]
        return res

    @staticmethod
    def list_plates(plate_type=None):
        """Generates a list of plates with some information about them

        Parameters
        ----------
        plate_type: str, optional
            If provided, limit the plate list to the given type

        Returns
        -------
        list of dicts
            The list of plate information with the structure:
            [{'plate_id': int, 'external_id': string}]
        """
        with sql_connection.TRN as TRN:
            sql_where = ('WHERE description = %s'
                         if plate_type is not None else '')
            sql = """SELECT DISTINCT plate_id, external_id
                        FROM qiita.plate
                            LEFT JOIN qiita.well USING (plate_id)
                            LEFT JOIN qiita.composition USING (container_id)
                            LEFT JOIN qiita.composition_type USING
                                (composition_type_id)
                     {}
                     ORDER BY plate_id""".format(sql_where)
            TRN.add(sql, [plate_type])
            return [dict(r) for r in TRN.execute_fetchindex()]

    @staticmethod
    def external_id_exists(external_id):
        """Checks if the given external id exists in the database

        Parameters
        ----------
        external_id : str
            The external id to check

        Returns
        -------
        boolean
            Whether the given external_id exists or not
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT EXISTS(SELECT 1 FROM qiita.plate
                                   WHERE external_id = %s)"""
            TRN.add(sql, [external_id])
            return TRN.execute_fetchlast()

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

    @external_id.setter
    def external_id(self, value):
        """Updates the external id of the plate"""
        self._set_attr('external_id', value)

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

    @notes.setter
    def notes(self, value):
        return self._set_attr('notes', value)

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
                layout[row-1][col-1] = container_module.Well(well_id)

        return layout

    @property
    def studies(self):
        """The studies present in the plate

        Returns
        -------
        set of labman.db.study.Study
        """
        with sql_connection.TRN as TRN:
            sql = "SELECT well_id FROM qiita.well WHERE plate_id = %s"
            TRN.add(sql, [self.id])
            res = set(container_module.Well(well_id).composition.study
                      for well_id in TRN.execute_fetchflatten())
            # If there are controls, those return None as the study, remove it
            # from the list
            res.discard(None)
        return res

    @property
    def quantification_process(self):
        """The quantification process of the plate

        Returns
        -------
        QuantificationProcess
            The quantification process of the plate, if exists. None, otherwise
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT cc.upstream_process_id
                     FROM qiita.concentration_calculation cc
                        JOIN qiita.composition
                            ON quantitated_composition_id = composition_id
                        JOIN qiita.well USING (container_id)
                     WHERE plate_id = %s"""
            TRN.add(sql, [self.id])
            res = TRN.execute_fetchindex()
            if res:
                return process_module.QuantificationProcess(res[0][0])
            return None

    @property
    def duplicates(self):
        """Get the wells with duplicated samples

        Returns
        -------
        dict of {str: list of wells}
            The duplicated wells, keyed by the sample id
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT sample_id, array_agg(well_id ORDER BY well_id)
                     FROM qiita.well
                        JOIN qiita.composition USING (container_id)
                        JOIN qiita.sample_composition USING (composition_id)
                     WHERE sample_id IS NOT NULL AND plate_id = %s
                     GROUP BY sample_id
                     HAVING array_length(array_agg(well_id), 1) > 1"""
            TRN.add(sql, [self.id])
            res = {sample_id: [container_module.Well(w) for w in wells]
                   for sample_id, wells in TRN.execute_fetchindex()}
        return res

    def get_well(self, row, column):
        """Returns the well at the (row, column) position in the plate

        Parameters
        ----------
        row: int
            The row number
        column: int
            The column number

        Returns
        -------
        labman.db.container.well
            The requested well

        Raises
        ------
        LabmanError
            If the plate doesn't have a well at (row, column)
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT well_id FROM qiita.well
                     WHERE plate_id = %s AND row_num = %s AND col_num = %s"""
            TRN.add(sql, [self.id, row, column])
            res = TRN.execute_fetchindex()
            if not res:
                # The well doesn't exist, raise an error
                raise exceptions_module.LabmanError(
                    "Well (%s, %s) doesn't exist in plate %s"
                    % (row, column, self.id))

            return container_module.Well(res[0][0])

    def get_wells_by_sample(self, sample_id):
        """Returns the list of wells containing the given sample

        Parameters
        ----------
        sample_id : str
            The sample to search for

        Returns
        -------
        list of labman.db.container.Well
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT well_id
                     FROM qiita.well
                        JOIN qiita.composition USING (container_id)
                        JOIN qiita.sample_composition USING (composition_id)
                     WHERE plate_id = %s AND sample_id = %s
                     ORDER BY well_id"""
            TRN.add(sql, [self.id, sample_id])
            res = [container_module.Well(well)
                   for well in TRN.execute_fetchflatten()]
        return res
