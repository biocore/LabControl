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

    @property
    def specimen_id_column(self):
        """Returns the specimen identifier column

        Returns
        -------
        str
            The name of the specimen id column

        Notes
        -----
        Copied from qiita_db/study.py
        """
        with sql_connection.TRN:
            sql = """SELECT specimen_id_column
                     FROM qiita.study
                     WHERE study_id = %s"""
            sql_connection.TRN.add(sql, [self._id])
            return sql_connection.TRN.execute_fetchlast()

    def specimen_id_to_sample_id(self, specimen):
        """Search for a specimen and retrieve its sample identifier

        Parameters
        ----------
        specimen: str
            The name of the specimen.

        Returns
        -------
        str
            The sample identifier for this specimen.

        Raises
        ------
        ValueError
            If no matches are found.
        RuntimeError
            If more than one match is found.

        Notes
        -----
        If the specimen_id_column is not set, the specimen_id is assumed to be
        the sample_id, and it will be verified against the list of known
        samples.
        """
        specimen_id_column = self.specimen_id_column

        with sql_connection.TRN as TRN:
            if specimen_id_column is None:
                # assuming specimen_id_column should be sample_id column,
                # verify that the sample_id exists in study_sample.
                sql = """SELECT sample_id
                         FROM qiita.study_sample
                         WHERE
                         sample_id = %s
                         """
            else:
                sql = """SELECT sample_id
                         FROM qiita.sample_{0} as {1}
                         WHERE
                         sample_values->>'{1}' = %s
                         """.format(self._id, specimen_id_column)
            print("SQL2: %s" % sql)
            TRN.add(sql, [specimen])
            res = TRN.execute_fetchflatten()

            if len(res) == 0:
                raise ValueError('Could not find "%s"' % specimen)
            # if a specimen_id_column is not unique (since this is softly
            # enforced), then there can be more than one match
            elif len(res) > 1:
                raise RuntimeError('There are several matches found for "%s"; '
                                   'there is a problem with the specimen id '
                                   'column' % specimen)
            return res.pop()

    def sample_id_to_specimen_id(self, sample_id):
        """Search for a sample identifier and retrieve its specimen identifier

        Parameters
        ----------
        sample_id: str
            The name of the specimen.

        Returns
        -------
        str
            The specimen identifier for this sample identifier.

        Raises
        ------
        ValueError
            If not matches are found (when a specimen_id_column is set).

        Notes
        -----
        If a specimen identifier column hasn't been set, this method will
        return the input value.
        """
        specimen_id_column = self.specimen_id_column
        if specimen_id_column is None:
            return sample_id

        #CHARLIE
        with sql_connection.TRN as TRN:
            sql = """SELECT sample_values->'{0}'
                     FROM qiita.sample_{1} as {0}
                     WHERE
                     sample_id = %s
                     """.format(specimen_id_column, self.id)
            print("SQL3: %s" % sql)
            TRN.add(sql, [sample_id])
            res = TRN.execute_fetchflatten()

            # res is length zero or one; the column has a unique constraint
            if len(res) == 0:
                raise ValueError('Could not find "%s"' % sample_id)
            return res.pop()

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
            Returns tube identifiers if the `specimen_id_column` has been set
            (in Qiita), or alternatively returns the sample identifier.
        """
        # acts as the tube identifier, if it isn't present use the sample id
        column = self.specimen_id_column
        column = column if column is not None else 'sample_id'

        # an empty wildcard will match all samples i.e. when term is None
        term = '%%' if term is None else '%%%s%%' % term.lower()

        with sql_connection.TRN as TRN:
            sql = """SELECT sample_values->'{0}' as {0}
                     FROM qiita.sample_{1}
                     WHERE LOWER(sample_values->>'{0}') LIKE %s
                     ORDER BY sample_values->'{0}'
                     LIMIT %s
                     """.format(column, self._id)
            print("SQL1: %s" % sql)
            sql_args = [term, limit]
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
                            JOIN labman.sample_composition USING (sample_id)
                         WHERE study_id = %s) nsp,
                -- Number of samples extracted
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_extracted
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                         WHERE study_id = %s) nse,
                -- Number of samples prepared for amplicon libraries
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_libraries
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.library_prep_16s_composition
                                USING (gdna_composition_id)
                         WHERE study_id = %s) nsal,
                -- Number of samples included in amplicon pools
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_pools
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.library_prep_16s_composition lib
                                USING (gdna_composition_id)
                            JOIN labman.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                         WHERE study_id = %s) nsap,
                -- Number of samples included in amplicon sequencing pools
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_sequencing_pools
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.library_prep_16s_composition lib
                                USING (gdna_composition_id)
                            JOIN labman.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                            JOIN labman.pool_composition pc
                                ON p.output_pool_composition_id =
                                    pc.pool_composition_id
                            JOIN labman.pool_composition_components p2
                                ON p2.input_composition_id = pc.composition_id
                         WHERE study_id = %s) nsasp,
                -- Number of samples amplicon sequenced
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_amplicon_sequencing_runs
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.library_prep_16s_composition lib
                                USING (gdna_composition_id)
                            JOIN labman.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                            JOIN labman.pool_composition pc
                                ON p.output_pool_composition_id =
                                    pc.pool_composition_id
                            JOIN labman.pool_composition_components p2
                                ON p2.input_composition_id = pc.composition_id
                            JOIN labman.sequencing_process_lanes s
                                ON s.pool_composition_id =
                                    p2.output_pool_composition_id
                         WHERE study_id = %s) nsasr,
                -- Number of samples compressed
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_compressed
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.compressed_gdna_composition
                                USING (gdna_composition_id)
                         WHERE study_id = %s) nsc,
                -- Number of samples normalized
                (SELECT COUNT(DISTINCT sample_id) AS number_samples_normalized
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN labman.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                         WHERE study_id = %s) nsn,
                -- Number of samples prepared for shotgun libraries
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_shotgun_libraries
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN labman.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                            JOIN labman.library_prep_shotgun_composition
                                USING (normalized_gdna_composition_id)
                         WHERE study_id = %s) nssl,
                -- Number of samples included in a shotgun pool
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_shotgun_pool
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN labman.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                            JOIN labman.library_prep_shotgun_composition lib
                                USING (normalized_gdna_composition_id)
                            JOIN labman.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                         WHERE study_id = %s) nssp,
                -- Number of samples shotgun sequenced
                (SELECT COUNT(DISTINCT sample_id) AS
                    number_samples_shotgun_sequencing_runs
                         FROM qiita.study_sample
                            JOIN labman.sample_composition USING (sample_id)
                            JOIN labman.gdna_composition
                                USING (sample_composition_id)
                            JOIN labman.compressed_gdna_composition
                                USING (gdna_composition_id)
                            JOIN labman.normalized_gdna_composition
                                USING (compressed_gdna_composition_id)
                            JOIN labman.library_prep_shotgun_composition lib
                                USING (normalized_gdna_composition_id)
                            JOIN labman.pool_composition_components p
                                ON lib.composition_id = p.input_composition_id
                            JOIN labman.sequencing_process_lanes l
                                ON p.output_pool_composition_id =
                                    l.pool_composition_id
                         WHERE study_id = %s) nsssr"""
            # Magic number 12 -> the number of times the study id appears
            # as parameter in the previous query
            TRN.add(sql, [self.id] * 12)
            # Magic number 0 -> the previous query only outputs a single row
            return dict(TRN.execute_fetchindex()[0])
