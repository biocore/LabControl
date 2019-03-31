# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from collections import defaultdict

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
    _table = "labman.plate_configuration"
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
                     FROM labman.plate_configuration
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
            sql = """INSERT INTO labman.plate_configuration
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
    _table = "labman.plate"
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
                'Search error: "samples", "plate_notes" and "well_notes" is '
                'None, please provide at least one of them.')

        if query_type not in ('INTERSECT', 'UNION'):
            raise ValueError('query_type should be INTERSECT or UNION. Found:'
                             ' %s' % query_type)

        with sql_connection.TRN as TRN:
            sql_queries = []
            sql_args = []
            if samples:
                sql_queries.append(
                    """SELECT DISTINCT plate_id
                       FROM labman.well
                            JOIN labman.composition USING (container_id)
                            JOIN labman.sample_composition
                                USING (composition_id)
                       WHERE sample_id IN %s""")
                sql_args.append(tuple(samples))
            if plate_notes:
                sql_queries.append(
                    """SELECT plate_id
                       FROM labman.plate
                       WHERE notes @@ to_tsquery(%s)""")
                sql_args.append(
                    ' & '.join([w for w in plate_notes.split()]))
            if well_notes:
                sql_queries.append(
                    """SELECT plate_id
                       FROM labman.well
                            JOIN labman.composition USING (container_id)
                       WHERE notes @@ to_tsquery(%s)""")
                sql_args.append(
                    ' & '.join([w for w in well_notes.split()]))

            if len(sql_queries) > 1:
                sql = (" %s " % query_type).join(sql_queries)
            else:
                sql = sql_queries[0]
            TRN.add(sql, sql_args)

            # explicitly sorting to ensure a deterministic result.
            # sorting ids in python rather than with a SQL ORDER BY since
            # there are several different SQL queries potentially being run.
            sorted_pids = sorted(TRN.execute_fetchflatten())
            res = [Plate(pid) for pid in sorted_pids]
        return res

    @staticmethod
    def list_plates(plate_types=None, only_quantified=False,
                    include_discarded=False,
                    include_study_titles=False):
        """Generates a list of plates with some information about them

        Parameters
        ----------
        plate_types: list, optional
            If provided, limit the plate list to the given types
        only_quantified: bool, optional
            If true, return only those plates that have been quantified
            Default: false.
        include_discarded: bool, optional
            If true, plates that have been marked as discarded will be
            included in this list, otherwise they won't.
        include_study_titles: bool, optional
            If true, return also the studies included in each plate

        Returns
        -------
        list of dicts
            The list of plate information with the structure:
            [{'plate_id': int, 'external_id': string}]
        """
        with sql_connection.TRN as TRN:
            sql_where, sql_discard, sql_plate_types = '', '', ''
            sql_args = []
            sql_join = ''

            # do not include discarded plates
            if not include_discarded:
                sql_discard = 'discarded = FALSE '

            # Not using if plate_type is not None cause I also want to cover
            # the case in which the list is empty
            sql_studies = ''
            if plate_types:
                sql_plate_types = 'description IN %s'
                sql_args.append(tuple(plate_types))

            # The WHERE clause is only needed if we have to filter plates
            # (which may depend on multiple conditions)
            if sql_discard != '' or sql_plate_types != '':
                sql_where = 'WHERE '
                if sql_discard != '' and sql_plate_types != '':
                    sql_where += sql_discard + ' AND ' + sql_plate_types
                else:
                    sql_where += sql_discard + ' ' + sql_plate_types

            if only_quantified:
                sql_join = ("JOIN labman.concentration_calculation "
                            "ON quantitated_composition_id = composition_id")
            if include_study_titles:
                sql_studies = (', labman.get_plate_studies(p.plate_id) '
                               'AS studies')

            sql = """SELECT p.plate_id, p.external_id, p.creation_timestamp {}
                        FROM (SELECT DISTINCT plate_id, external_id,
                                              creation_timestamp
                              FROM labman.plate
                                JOIN labman.well USING (plate_id)
                                JOIN labman.composition USING (container_id)
                                JOIN labman.composition_type USING
                                    (composition_type_id)
                                {}
                             {}) AS p
                     ORDER BY plate_id""".format(sql_studies, sql_join,
                                                 sql_where)
            TRN.add(sql, sql_args)
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
            sql = """SELECT EXISTS(SELECT 1 FROM labman.plate
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
            sql = """INSERT INTO labman.plate
                        (external_id, plate_configuration_id)
                    VALUES (%s, %s)
                    RETURNING plate_id"""
            TRN.add(sql, [external_id, plate_configuration.id])
            return cls(TRN.execute_fetchlast())

    @property
    def creation_timestamp(self):
        return self._get_attr('creation_timestamp')

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

    @discarded.setter
    def discarded(self, value):
        """Updates the discarded status of the plate"""
        self._set_attr('discarded', value)

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
                     FROM labman.well
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
            sql = "SELECT well_id FROM labman.well WHERE plate_id = %s"
            TRN.add(sql, [self.id])
            res = set(container_module.Well(well_id).composition.study
                      for well_id in TRN.execute_fetchflatten())
            # If there are controls, those return None as the study, remove it
            # from the list
            res.discard(None)
        return res

    @property
    def process(self):
        """Returns the process that generated this plate

        Returns
        -------
        labman.db.process.Process
            The process that generated this plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT latest_upstream_process_id
                     FROM labman.container
                        JOIN labman.well USING (container_id)
                     WHERE plate_id = %s"""
            TRN.add(sql, [self.id])
            return process_module.Process.factory(TRN.execute_fetchlast())

    @property
    def quantification_processes(self):
        """The quantification process(es) applied to (wells on) the plate

        Returns
        -------
        list of QuantificationProcess
            The quantification processes applied to (wells on) the plate,
            in order from least to most recent. Empty list if none exist.
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT cc.upstream_process_id
                     FROM labman.concentration_calculation cc
                        JOIN labman.composition
                            ON quantitated_composition_id = composition_id
                        JOIN labman.well USING (container_id)
                     WHERE plate_id = %s
                     ORDER BY cc.upstream_process_id"""
            TRN.add(sql, [self.id])
            res = [process_module.QuantificationProcess(process_id)
                   for process_id in TRN.execute_fetchflatten()]
            res.sort(key=lambda x: x.date)
        return res

    @property
    def duplicates(self):
        """Get the wells with duplicated samples

        Returns
        -------
        dict of {str: list of wells}
            The duplicated wells, keyed by the sample id
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT sample_id, array_agg(well_id ORDER BY well_id),
                                array_agg(content ORDER BY well_id)
                     FROM labman.well
                        JOIN labman.composition USING (container_id)
                        JOIN labman.sample_composition USING (composition_id)
                     WHERE sample_id IS NOT NULL AND plate_id = %s
                     GROUP BY sample_id
                     HAVING array_length(array_agg(well_id), 1) > 1
                     ORDER BY sample_id"""
            TRN.add(sql, [self.id])
            res = {sample_id: [[container_module.Well(w), c]
                               for w, c in zip(wells, contents)]
                   for sample_id, wells, contents in TRN.execute_fetchindex()}
        return res

    @property
    def unknown_samples(self):
        """Get the wells holding unknown samples

        Returns
        -------
        list of Well
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT well_id
                     FROM labman.well
                        JOIN labman.composition USING (container_id)
                        JOIN labman.sample_composition USING (composition_id)
                        JOIN labman.sample_composition_type
                            USING (sample_composition_type_id)
                     WHERE plate_id = %s AND
                           external_id = 'experimental sample' AND
                           sample_id IS NULL
                     ORDER BY well_id"""
            TRN.add(sql, [self.id])
            res = [container_module.Well(w)
                   for w in TRN.execute_fetchflatten()]
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
            sql = """SELECT well_id FROM labman.well
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
                     FROM labman.well
                        JOIN labman.composition USING (container_id)
                        JOIN labman.sample_composition USING (composition_id)
                     WHERE plate_id = %s AND sample_id = %s
                     ORDER BY well_id"""
            TRN.add(sql, [self.id, sample_id])
            res = [container_module.Well(well)
                   for well in TRN.execute_fetchflatten()]
        return res

    def get_previously_plated_wells(self):
        """Get wells with samples that have been previously plated

        Returns
        -------
        dict of {well: list of plates}
            The wells that contain samples that have been previously plated
            and the plates in which they're found
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT plate_id, array_agg(sample_id)
                     FROM labman.sample_composition
                        JOIN labman.composition USING (composition_id)
                        JOIN labman.well USING (container_id)
                     WHERE plate_id <> %s AND sample_id IN (
                        SELECT sample_id
                        FROM labman.sample_composition
                            JOIN labman.composition USING (composition_id)
                            JOIN labman.well USING (container_id)
                            WHERE plate_id = %s)
                     GROUP BY plate_id"""
            TRN.add(sql, [self.id, self.id])
            prev_plated = TRN.execute_fetchindex()
            res = defaultdict(list)
            for plate_id, samples in prev_plated:
                for sample in samples:
                    for well in self.get_wells_by_sample(sample):
                        res[well].append(plate_id)
            res = {well: [Plate(x) for x in sorted(list(set(plate_ids)))]
                   for well, plate_ids in res.items()}
        return res
