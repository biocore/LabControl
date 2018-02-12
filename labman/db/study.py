# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import numpy as np

from . import base
from . import sql_connection
from . import user
from . import container as container_module


class Study(base.LabmanObject):
    """Study object

    Attributes
    ----------
    id
    title
    creator
    num_samples

    Methods
    -------
    list_studies
    samples

    See Also
    --------
    labman.db.base.LabmanObject
    """
    _table = "qiita.study"
    _id_column = "study_id"

    @classmethod
    def list_studies(cls):
        """Generates a list of studies with some information about them

        Returns
        -------
        list of dicts
            The list of studies with a dictionary with the structure:
            {'study_id': int, 'study_title': string, 'study_alias': string,
             'owner': string, 'num_samples': int}
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT study_id, study_title, study_alias, email as owner,
                            COUNT(sample_id) as num_samples
                     FROM qiita.study
                        LEFT JOIN qiita.study_sample USING (study_id)
                     GROUP BY study_id, study_title, study_alias, email
                     ORDER BY study_id"""
            TRN.add(sql)
            return [dict(r) for r in TRN.execute_fetchindex()]

    @property
    def title(self):
        """The study title"""
        return self._get_attr('study_title')

    @property
    def creator(self):
        """The user that created the study"""
        return user.User(self._get_attr('email'))

    def generate_sample_plate_maps(self):
        """Generates a string with the plate maps in a csv format

        Returns
        -------
        str
        """
        with sql_connection.TRN as TRN:
            # Retrieve all the plate layouts for all the sample plates in which
            # this study has been plated.
            sql = """SELECT plate_id, external_id AS plate_name,
                            num_rows, num_columns,
                            array_agg((content, row_num, col_num)
                                      ORDER BY row_num, col_num) AS layout
                     FROM qiita.well
                        JOIN qiita.composition USING (container_id)
                        JOIN qiita.sample_composition USING (composition_id)
                        JOIN qiita.plate USING (plate_id)
                        JOIN qiita.plate_configuration
                            USING (plate_configuration_id)
                     WHERE plate_id IN (SELECT DISTINCT plate_id
                                        FROM qiita.study_sample
                                            JOIN qiita.sample_composition
                                                USING (sample_id)
                                            JOIN qiita.composition
                                                USING (composition_id)
                                            JOIN qiita.well
                                                USING (container_id)
                                        WHERE study_id = %s)
                     GROUP BY plate_id, num_rows, num_columns
                     ORDER BY plate_id"""
            TRN.add(sql, [self.id])
            res = TRN.execute_fetchindex()
            # Create a list of numpy arrays to store the layouts
            layouts = [np.zeros((nr, nc), dtype=object)
                       for _, _, nr, nc, _ in res]
            # Loop through all the plates and populate the layouts with the
            # contents of the well
            for idx, (_, _, _, _, layout) in enumerate(res):
                # Description of the string mangling: The `array_agg` operation
                # in sql is generating a list of tuples. However, since it is
                # a composite type, psycopg2 it is not returning it as a list,
                # but just as a string with the following format:
                # {"(1.SKB1.640202.21.A1,1,1)","(1.SKB2.640194.21.A2,1,2)","...
                # ...","(blank.21.H11,8,11)","(empty.21.H12,8,12)"}
                # The slice [2:-2] removes the outter curly braces ({}) and the
                # outter double-quotes ("). By splitting the resulting string
                # at "," we are given a list of strings like:
                # ['(1.SKB1.640202.21.A1,1,1)', '(1.SKB2.640194.21.A2,1,2)',...
                # ...'(blank.21.H11,8,11)', '(empty.21.H12,8,12)'].
                # Then, the [1:-1] slice access for the well_string variable
                # is removing the outter parenthesis () of each element from
                # the list, and the split(',') is generating a list like:
                # ["1.SKB1.640202.21.A1", "1", "1"], which each element is then
                # stored in content, row_num, and col_num, respectivelly.
                # NOTE: in other cases we have been using "eval" to parse this
                # string. However, the eval will return a set, which will
                # destroy the ordering established on the SQL command.
                for well_string in layout[2:-2].split('","'):
                    content, row_num, col_num = well_string[1:-1].split(',')
                    layouts[idx][int(row_num) - 1][int(col_num) - 1] = content

            plate_layouts = []
            for idx, layout in enumerate(layouts):
                # Add two lines to the plate layout. First one indicates the
                # plate name and id, and the second one the column names
                plate_layout = [
                    'Plate "%s" (ID: %s)' % (res[idx]['plate_name'],
                                             res[idx]['plate_id']),
                    ',%s' % ','.join(
                        map(str, range(1, res[idx]['num_columns'] + 1)))]
                plate_layout.extend(
                    ['%s,%s' % (container_module.generate_row_id(ridx + 1),
                                ','.join(map(str, row)))
                     for ridx, row in enumerate(layout)])

                plate_layouts.append('\n'.join(plate_layout))

            return '\n\n\n'.join(plate_layouts)

    def samples(self, term=None, limit=None):
        """The study samples

        Parameters
        ----------
        term: str, optional
            If provided, return only the samples that contain the given term
        limit: int, optional
            If provided, don't return more than `limit` results

        Returns
        -------
        list of str
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT sample_id
                     FROM qiita.study_sample
                     WHERE study_id = %s {}
                     ORDER BY sample_id"""

            if term is not None:
                sql = sql.format("AND LOWER(sample_id) LIKE %s")
                # The resulting parameter for LIKE is of the form "%term%"
                sql_args = [self.id, '%%%s%%' % term.lower()]
            else:
                sql = sql.format("")
                sql_args = [self.id]

            if limit is not None:
                sql += " LIMIT %s"
                sql_args.append(limit)

            TRN.add(sql, sql_args)
            return TRN.execute_fetchflatten()

    @property
    def num_samples(self):
        """The number of samples in the study"""
        with sql_connection.TRN as TRN:
            sql = """SELECT count(sample_id)
                     FROM qiita.study_sample
                     WHERE study_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def sample_numbers_summary(self):
        """Retrieves a summary of the status of the samples"""
        with sql_connection.TRN as TRN:
            sql = """SELECT * FROM
                (SELECT COUNT(sample_id) AS num_samples
                         FROM qiita.study_sample
                         WHERE study_id = %s) ns,
                -- Number of samples plated
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_plated
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                         WHERE study_id = %s) nsp,
                -- Number of samples extracted
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_extracted
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                         WHERE study_id = %s) nse,
                -- Number of samples prepared for amplicon libraries
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_libraries
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.library_prep_16s_composition
                                USING (gdna_composition_id)
                         WHERE study_id = %s) nsal,
                -- Number of samples included in amplicon pools
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_pools
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.library_prep_16s_composition lib
                                USING (gdna_composition_id)
                            JOIN qiita.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                         WHERE study_id = %s) nsap,
                -- Number of samples included in amplicon sequencing pools
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_sequencing_pools
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.library_prep_16s_composition lib
                                USING (gdna_composition_id)
                            JOIN qiita.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                            JOIN qiita.pool_composition pc
                                ON p.output_pool_composition_id =
                                    pc.pool_composition_id
                            JOIN qiita.pool_composition_components p2
                                ON p2.input_composition_id = pc.composition_id
                         WHERE study_id = %s) nsasp,
                -- Number of samples amplicon sequenced
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_sequencing_runs
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.library_prep_16s_composition lib
                                USING (gdna_composition_id)
                            JOIN qiita.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                            JOIN qiita.pool_composition pc
                                ON p.output_pool_composition_id =
                                    pc.pool_composition_id
                            JOIN qiita.pool_composition_components p2
                                ON p2.input_composition_id = pc.composition_id
                            JOIN qiita.sequencing_process_lanes s
                                ON s.pool_composition_id =
                                    p2.output_pool_composition_id
                         WHERE study_id = %s) nsasr,
                -- Number of samples compressed
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_compressed
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.compressed_gdna_composition
                                USING (gdna_composition_id)
                         WHERE study_id = %s) nsc,
                -- Number of samples normalized
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_normalized
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN qiita.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                         WHERE study_id = %s) nsn,
                -- Number of samples prepared for shotgun libraries
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_shotgun_libraries
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN qiita.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                            JOIN qiita.library_prep_shotgun_composition
                                USING (normalized_gdna_composition_id)
                         WHERE study_id = %s) nssl,
                -- Number of samples included in a shotgun pool
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_shotgun_pool
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN qiita.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                            JOIN qiita.library_prep_shotgun_composition lib
                                USING (normalized_gdna_composition_id)
                            JOIN qiita.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                         WHERE study_id = %s) nssp,
                -- Number of samples shotgun sequenced
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_shotgun_sequencing_runs
                         FROM qiita.study_sample
                            JOIN qiita.sample_composition USING (sample_id)
                            JOIN qiita.gdna_composition
                                USING (sample_composition_id)
                            JOIN qiita.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN qiita.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                            JOIN qiita.library_prep_shotgun_composition lib
                                USING (normalized_gdna_composition_id)
                            JOIN qiita.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                            JOIN qiita.sequencing_process_lanes l
                                ON p.output_pool_composition_id =
                                    l.pool_composition_id
                         WHERE study_id = %s) nsssr"""
            # Magic number 12 -> the number of times the study id appears
            # as parameter in the previous query
            TRN.add(sql, [self.id] * 12)
            # Magic number 0 -> the previous query only outputs a single row
            return dict(TRN.execute_fetchindex()[0])
