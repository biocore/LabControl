# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import user


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
