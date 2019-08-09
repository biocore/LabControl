from datetime import datetime
from io import StringIO
import re
import pandas as pd
from . import sql_connection
from . import container as container_module


class Sheet:
    @staticmethod
    def get_date_format():
        return '%Y-%m-%d %H:%M'

    @staticmethod
    def _folder_scrub_name(x):
        """Modifies a string to be suitable for use as a directory name

        Multiple disallowed characters in a row are substituted with a single
        instance of the relevant replacement character: e.g.,
        Hello,,,,Sunshine
        becomes
        Hello-Sunshine

        Parameters
        ----------
        x : str

        Returns
        -------
        str
            the input string with whitespaces replaced with underscores and
            any other non-alphanumeric, non-hyphen, non-underscore characters
            replaced with a hyphen.
        """

        # Replace any whitespace(s) with underscore
        x = re.sub(r"\s+", '_', x)

        # Replace any other character that is not alphanumeric, an underscore,
        # or a hyphen (and thus valid in a folder name) with a hyphen
        x = re.sub('[^0-9a-zA-Z-_]+', '-', x)
        return x

    @staticmethod
    def _bcl_scrub_name(name):
        """Modifies a sample name to be BCL2fastq compatible

        Parameters
        ----------
        name : str
            the sample name

        Returns
        -------
        str
            the sample name, formatted for bcl2fastq
        """
        return re.sub('[^0-9a-zA-Z-_]+', '_', name)

    @staticmethod
    def _set_control_values_to_plate_value(input_df, plate_col_name,
                                           projname_col_name):
        """ Update project name for control samples

        Ensure that each sample plate included in the dataframe does not
        contain experimental samples with more than (or less than) one
        value in the column named projname_col_name. Assuming this is true, set
        the project column value for each non-experimental sample to the value
        of the project name for the (single) project on the non-experimental
        sample's plate.

        Parameters
        ----------
        input_df: pandas.DataFrame
            A dataframe containing (at least) a column of plate names (having
            the column name given in plate_col_name) and a column of project
            names (having the column name given in projname_col_name)--e.g.,
            Project Name on prep sheet or sample_proj_name on sample sheet--
            and one row for each sample (both experimental and non-
            experimental).  The value in the project name column must be None
            for control (blank/positive control/etc) samples.
        plate_col_name: str
            The name of the column in input_df that contains the name of the
            plate on which a given sample lies.
        projname_col_name: str
            The name of the column in input_df that contains the name of the
            project associated with the given sample.

        Returns
        -------
        result_df: pandas.DataFrame
            A copy of the input dataframe, modified so that the controls have
            the same (single) project name as the experimental samples on their
            sample plate.

        Raises
        ------
        ValueError
            If any plate contains experimental samples from more (or fewer)
            than one project.
        """

        assert plate_col_name in input_df.columns.values
        assert projname_col_name in input_df.columns.values

        result_df = input_df.copy()
        problem_plate_messages = []

        # create a mask to define all the NON-control rows for this plate
        non_controls_mask = input_df[projname_col_name].notnull()

        # get all the unique plates in the dataframe
        unique_plates = input_df[plate_col_name].unique()
        for curr_unique_plate in unique_plates:
            # create a mask to define all the rows for this plate
            plate_mask = input_df[plate_col_name] == curr_unique_plate

            # create a mask to define all the rows for this plate where the
            # project name is NOT the control value (None)
            plate_non_controls_mask = plate_mask & non_controls_mask

            # get unique project names for the part of df defined in the mask
            curr_plate_non_controls = input_df[plate_non_controls_mask]
            curr_plate_projnames = curr_plate_non_controls[projname_col_name]
            curr_unique_projnames = curr_plate_projnames.unique()

            if len(curr_unique_projnames) != 1:
                # Note that we don't error out the first time we find a
                # plate that doesn't meet expectations; instead we continue to
                # run through all the plates and identify ALL those that don't
                # meet expectations.  This way the user can correct all of them
                # at once.
                curr_err_msg = "Expected one unique value for plate '{0}' " \
                               "but received {1}: {2}"

                upn = ", ".join([str(x) for x in curr_unique_projnames])

                curr_err_msg = curr_err_msg.format(curr_unique_plate,
                                                   len(curr_unique_projnames),
                                                   upn)
                problem_plate_messages.append(curr_err_msg)
            else:
                # create a mask to define all the rows for this plate where the
                # projname IS the control value (None); ~ "nots" a whole series
                plate_controls_mask = plate_mask & (~non_controls_mask)

                # ok to just take first non-control projname because we
                # verified above there is only one value there anyway
                result_df.loc[plate_controls_mask, projname_col_name] = \
                    curr_unique_projnames[0]
            # end if
        # next unique plate

        if len(problem_plate_messages) > 0:
            raise ValueError("\n".join(problem_plate_messages))

        return result_df


class SampleSheet(Sheet):
    @staticmethod
    def factory(**kwargs):
        """Initializes the correct Process subclass

        Parameters
        ----------
        process_id : int
            The process id

        Returns
        -------
        An instance of a subclass of Process
        """
        # note that assay_type is needed for determining the correct object to
        # return, but it may also be needed by the object downstream for other
        # purposes. As much as possible, the string should not be hard-coded
        # within the code itself. It is only hardcoded in the factory methods
        # for SampleSheet and PrepInfoSheet to map to the correct objects.
        assay_type = kwargs['assay_type']

        factory_classes = {
            'Amplicon': SampleSheet16S,
            'Metagenomics': SampleSheetShotgun }

        constructor = factory_classes[assay_type]

        return constructor(**kwargs)

    @staticmethod
    def _format_sample_sheet_comments(principal_investigator=None,
                                      contacts=None, other=None, sep=','):
        """Formats the sample sheet comments

        Parameters
        ----------
        principal_investigator: dict, optional
            The principal investigator information: {name: email}
        contacts: dict, optional
            The contacts information: {name: email}
        other: str, optional
            Other information to include in the sample sheet comments
        sep: str, optional
            The sample sheet separator

        Returns
        -------
        str
            The formatted comments of the sample sheet
        """
        comments = []

        if principal_investigator is not None:
            comments.append('PI{0}{1}\n'.format(
                sep, sep.join(
                    '{0}{1}{2}'.format(x, sep, principal_investigator[x])
                    for x in principal_investigator.keys())))

        if contacts is not None:
            comments.append(
                'Contact{0}{1}\nContact emails{0}{2}\n'.format(
                    sep, sep.join(x for x in sorted(contacts.keys())),
                    sep.join(contacts[x] for x in sorted(contacts.keys()))))

        if other is not None:
            comments.append('%s\n' % other)

        return ''.join(comments)



    @staticmethod
    def _reverse_complement(seq):
        """Reverse-complement a sequence

        From http://stackoverflow.com/a/25189185/7146785

        Parameters
        ----------
        seq : str
            The sequence to reverse-complement

        Returns
        -------
        str
            The reverse-complemented sequence
        """
        complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
        rev_seq = "".join(complement.get(base, base) for base in reversed(seq))
        return rev_seq

    @staticmethod
    def _sequencer_i5_index(sequencer, indices):
        """Decides if the indices should be reversed based on the sequencer
        """
        revcomp_sequencers = ['HiSeq4000', 'MiniSeq', 'NextSeq', 'HiSeq3000']
        other_sequencers = ['HiSeq2500', 'HiSeq1500', 'MiSeq', 'NovaSeq']

        if sequencer in revcomp_sequencers:
            return [SampleSheet._reverse_complement(x) for x in indices]
        elif sequencer in other_sequencers:
            return indices
        else:
            raise ValueError(
                'Your indicated sequencer [%s] is not recognized.\nRecognized '
                'sequencers are: \n' %
                ' '.join(revcomp_sequencers + other_sequencers))


class PrepInfoSheet(Sheet):
    @staticmethod
    def factory(**kwargs):
        """Initializes the correct Process subclass

        Parameters
        ----------
        process_id : int
            The process id

        Returns
        -------
        An instance of a subclass of Process
        """
        assay_type = kwargs['assay_type']

        factory_classes = {
            'Amplicon': PrepInfoSheet16S,
            'Metagenomics': PrepInfoSheetShotgun }

        constructor = factory_classes[assay_type]

        return constructor(**kwargs)


class SampleSheet16S(SampleSheet):
    def __init__(self, **kwargs):
        # assume keys exist, and let KeyErrors pass up to the user
        self.include_lane = kwargs['include_lane']
        self.pools = kwargs['pools']
        self.principal_investigator = kwargs['principal_investigator']
        self.contacts = kwargs['contacts']
        self.experiment = kwargs['experiment']
        self.date = kwargs['date']
        self.fwd_cycles = kwargs['fwd_cycles']
        self.rev_cycles = kwargs['rev_cycles']
        self.run_name = kwargs['run_name']

    def generate(self):
        """Generates Illumina compatible sample sheets

        Returns
        -------
        str
            The illumina-formatted sample sheet
        """
        # the "Description" => "Well_Description" change was for the
        # compatibility with EBI submission
        data = ['%sSample_ID,Sample_Name,Sample_Plate,Sample_Well,'
                'I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,'
                'Well_Description,,'
                % ('Lane,' if self.include_lane else '')]
        for pool, lane in self.pools:
            data.append('%s%s,,,,,NNNNNNNNNNNN,,,,%s,,,'
                        % (('%s,' % lane) if self.include_lane else '',
                           self._bcl_scrub_name(pool.container.external_id),
                           pool.composition_id))
        return self._format_sample_sheet('\n'.join(data))

    def _format_sample_sheet(self, data, sep=','):
        """Formats Illumina-compatible sample sheet.

        Parameters
        ----------
        data: array-like of str
            A list of strings containing formatted strings to include in the
            [Data] component of the sample sheet

        Returns
        -------
        sample_sheet : str
            the sample sheet string
        """
        contacts = {c.name: c.email for c in self.contacts}
        principal_investigator = {self.principal_investigator.name:
                                      self.principal_investigator.email}
        sample_sheet_dict = {
            'comments': self._format_sample_sheet_comments(
                principal_investigator=principal_investigator,
                contacts=contacts),
            'IEMFileVersion': '4',
            'Investigator Name': self.principal_investigator.name,
            'Experiment Name': self.experiment,
            'Date': datetime.strftime(self.date, Sheet.get_date_format()),
            'Workflow': 'GenerateFASTQ',
            'Application': 'FASTQ Only',
            'Assay': 'TruSeq HT',
            'Description': '',
            'Chemistry': 'Amplicon',
            'read1': self.fwd_cycles,
            'read2': self.rev_cycles,
            'ReverseComplement': '0',
            'data': data}

        # these sequences are constant for all TruSeq HT assays
        # https://support.illumina.com/bulletins/2016/12/what-sequences-do-
        # i-use-for-adapter-trimming.html
        sample_sheet_dict['Adapter'] = 'AGATCGGAAGAGCACACGTCTGAACTCCAGTCA'
        sample_sheet_dict['AdapterRead2'] = (
            'AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGT')

        template = (
            '{comments}[Header]\nIEMFileVersion{sep}{IEMFileVersion}\n'
            'Investigator Name{sep}{Investigator Name}\n'
            'Experiment Name{sep}{Experiment Name}\nDate{sep}{Date}\n'
            'Workflow{sep}{Workflow}\nApplication{sep}{Application}\n'
            'Assay{sep}{Assay}\nDescription{sep}{Description}\n'
            'Chemistry{sep}{Chemistry}\n\n[Reads]\n{read1}\n{read2}\n\n'
            '[Settings]\nReverseComplement{sep}{ReverseComplement}\n'
            'Adapter{sep}{Adapter}\nAdapterRead2{sep}{AdapterRead2}\n\n'
            '[Data]\n{data}'
        )

        if sample_sheet_dict['comments']:
            sample_sheet_dict['comments'] = re.sub(
                '^', '# ', sample_sheet_dict['comments'].rstrip(),
                flags=re.MULTILINE) + '\n'

        sample_sheet = template.format(**sample_sheet_dict, **{'sep': sep})
        return sample_sheet


class PrepInfoSheet16S(PrepInfoSheet):
    def __init__(self, **kwargs):
        # assume keys exist, and let KeyErrors pass up to the user
        self.sequencing_process_id = kwargs['sequencing_process_id']
        self.include_lane = kwargs['include_lane']
        self.pools = kwargs['pools']
        self.principal_investigator = kwargs['principal_investigator']
        self.contacts = kwargs['contacts']
        self.experiment = kwargs['experiment']
        self.date = kwargs['date']
        self.fwd_cycles = kwargs['fwd_cycles']
        self.rev_cycles = kwargs['rev_cycles']
        self.run_name = kwargs['run_name']


    def _get_additional_prep_metadata(self):
        """Gathers additional prep_info metadata for file generation

        Gathers additional prep_info metadata used in the generation of files
        using additional SQL queries. The data is returned as a tuple of
        dictionaries that can be used to map additional metadata into the
        results of the primary prep info query.

        Returns
        -------
        tuple: (str: The model of instrument for the sequencing run
                dict: equipment_id/dict pairs used to map equipment_id to info
                dict: reagent_id/dict pairs used to map reagent_id to info
               )
        """
        with sql_connection.TRN as TRN:
            # Let's cache some data to avoid querying the DB multiple times:
            # sequencing run - this is definitely still applicable
            TRN.add("""SELECT et.description AS instrument_model
                        FROM labcontrol.sequencing_process sp
                        LEFT JOIN labcontrol.process process USING (process_id)
                        LEFT JOIN labcontrol.equipment e ON (
                            sequencer_id = equipment_id)
                        LEFT JOIN labcontrol.equipment_type et ON (
                            e.equipment_type_id = et.equipment_type_id)
                        LEFT JOIN labcontrol.sequencing_process_lanes spl USING (
                            sequencing_process_id)
                        WHERE sequencing_process_id = %s""", [self.sequencing_process_id])

            instrument_model = [row['instrument_model']
                                for row in TRN.execute_fetchindex()]

            if len(instrument_model) != 1:
                raise ValueError("Expected 1 and only 1 value for sequencing "
                                 "run instrument_model, but received "
                                 "{}".format(len(instrument_model)))

            instrument_model = instrument_model[0]

            TRN.add("""SELECT equipment_id, external_id, notes, description
                                   FROM labcontrol.equipment
                                   LEFT JOIN labcontrol.equipment_type
                                   USING (equipment_type_id)""")

            equipment = {dict(row)['equipment_id']: dict(row)
                         for row in TRN.execute_fetchindex()}

            TRN.add("""SELECT reagent_composition_id, composition_id,
                                       external_lot_id, description
                                   FROM labcontrol.reagent_composition
                                   LEFT JOIN labcontrol.reagent_composition_type
                                   USING (reagent_composition_type_id)""")

            reagent = {dict(row)['reagent_composition_id']: dict(row)
                       for row in TRN.execute_fetchindex()}

        return (instrument_model, equipment, reagent)

    def generate(self):
        """Generates prep information for Amplicon workflows

        An internal method used to implement the generation of prep information
        files for Amplicon workflows. This method is called by
        generate_prep_information() only.

        Returns
        -------
        dict: { int: str,
                int: str,
                int: str,
                .
                .
                .
                int: str,
                str: str }

        where 'int: str' represents either a Study ID and a TSV file (in string
        form), or a Prep ID and TSV file (in string form).

        'str: str' represents controls data; the key is the constant
        'Controls', and the value is a TSV file (in string form).
        """
        data = {}

        extra_fields = [
            # 'e'/'r': equipment/reagent
            ('e', 'lepmotion_robot_id', 'epmotion_robot'),
            ('e', 'epmotion_tm300_8_tool_id', 'epmotion_tm300_8_tool'),
            ('e', 'epmotion_tm50_8_tool_id', 'epmotion_tm50_8_tool'),
            ('e', 'gepmotion_robot_id', 'gdata_robot'),
            ('e', 'epmotion_tool_id', 'epmotion_tool'),
            ('e', 'kingfisher_robot_id', 'kingfisher_robot'),
            ('r', 'extraction_kit_id', 'extraction_kit'),
            ('r', 'master_mix_id', 'master_mix'),
            ('r', 'water_lot_id', 'water_lot'),
        ]

        sql = """
            -- Naming convention: xcpcp means 'the generic composition
            -- that is associated to specialized composition aliased as xcp'.
            -- Likewise, xprpr means 'the generic process that is
            -- associated with the specialized process aliased as xpr'.

            -- Get the prep sheet info for all wells on any of the library prep
            -- plates (INCLUDING those that weren't pooled in this pool).
            SELECT
                study.study_id, study_sample.sample_id,
                study.study_alias AS project_name,
                study_sample.sample_id AS orig_name,
                study.study_description AS experiment_design_description,
                samplewell.row_num AS row_num,
                samplewell.col_num AS col_num,
                samplecp.content,
                sampleplate.external_id AS sample_plate,
                platingprpr.run_personnel_id AS plating,
                -- all the below are internal ids, which are linked to and
                -- converted to human-readable external ids later, outside
                -- of this query
                gdnaextractpr.extraction_kit_id,
                gdnaextractpr.epmotion_robot_id AS gepmotion_robot_id,
                gdnaextractpr.epmotion_tool_id,
                gdnaextractpr.kingfisher_robot_id,
                libpreppr.master_mix_id,
                libpreppr.water_lot_id,
                libpreppr.epmotion_robot_id AS lepmotion_robot_id,
                libpreppr.epmotion_tm300_8_tool_id,
                libpreppr.epmotion_tm50_8_tool_id,
                primersetcp.barcode_seq AS barcode,
                -- this is an internal id, which is linked later (outside
                -- of this query) to marker_gene_primer_set_id, from which
                -- we can get the linker/primer
                primersetcp.primer_set_id,
                primersetplate.external_id AS primer_plate,
                primerworkingplateprpr.run_date AS primer_date
            -- Retrieve the amplicon library prep information
            FROM labcontrol.plate libprepplate
            LEFT JOIN labcontrol.well libprepwell ON (
                libprepplate.plate_id = libprepwell.plate_id)
            LEFT JOIN labcontrol.composition libprepcpcp ON (
                libprepwell.container_id = libprepcpcp.container_id)
            LEFT JOIN labcontrol.library_prep_16s_process libpreppr ON (
                libprepcpcp.upstream_process_id = libpreppr.process_id)
            LEFT JOIN labcontrol.library_prep_16s_composition libprepcp ON (
                --used to get primer later
                libprepcpcp.composition_id = libprepcp.composition_id)
            -- Retrieve the gdna extraction information
            LEFT JOIN labcontrol.gdna_composition gdnacp
                USING (gdna_composition_id)
            LEFT JOIN labcontrol.composition gdnacpcp ON (
                gdnacp.composition_id = gdnacpcp.composition_id)
            LEFT JOIN labcontrol.gdna_extraction_process gdnaextractpr ON (
                gdnacpcp.upstream_process_id = gdnaextractpr.process_id)
            -- Retrieve the sample information
            LEFT JOIN labcontrol.sample_composition samplecp USING (
                sample_composition_id)
            LEFT JOIN labcontrol.composition samplecpcp ON (
                samplecp.composition_id = samplecpcp.composition_id)
            LEFT JOIN labcontrol.well samplewell ON (
                samplecpcp.container_id = samplewell.container_id)
            LEFT JOIN labcontrol.plate sampleplate ON (
                samplewell.plate_id = sampleplate.plate_id)
            LEFT JOIN labcontrol.process platingprpr ON (
                --all plating processes are generic--there is no
                -- specialized plating process table
                samplecpcp.upstream_process_id = platingprpr.process_id)
            -- Retrieve the primer information
            LEFT JOIN labcontrol.primer_composition primercp ON (
                libprepcp.primer_composition_id =
                primercp.primer_composition_id)
            LEFT JOIN labcontrol.composition primercpcp on (
                primercp.composition_id = primercpcp.composition_id)
            LEFT JOIN labcontrol.process primerworkingplateprpr ON (
                primercpcp.upstream_process_id =
                primerworkingplateprpr.process_id)
            LEFT JOIN labcontrol.primer_set_composition primersetcp ON (
                --gives access to barcode
                primercp.primer_set_composition_id =
                primersetcp.primer_set_composition_id)
            LEFT JOIN labcontrol.composition primersetcpcp ON (
                primersetcp.composition_id = primersetcpcp.composition_id)
            LEFT JOIN labcontrol.well primersetwell ON (
                primersetcpcp.container_id = primersetwell.container_id)
            LEFT JOIN labcontrol.plate primersetplate ON (
                --note: NOT the name of the primer working plate, but the
                -- name of the primer plate plate map
                primersetwell.plate_id = primersetplate.plate_id)
            -- Retrieve the study information
            FULL JOIN qiita.study_sample USING (sample_id)
            LEFT JOIN qiita.study as study USING (study_id)
            WHERE libprepplate.plate_id IN (
                -- get the plate ids of the library prep plates that had ANY
                -- wells included in this pool
                SELECT distinct libprepplate2.plate_id
                -- Retrieve sequencing information
                FROM labcontrol.sequencing_process sp
                LEFT JOIN labcontrol.sequencing_process_lanes spl USING (
                    sequencing_process_id)
                -- Retrieve pooling information
                LEFT JOIN labcontrol.pool_composition_components pcc1 ON (
                    spl.pool_composition_id = pcc1.output_pool_composition_id)
                LEFT JOIN labcontrol.pool_composition pccon ON (
                    pcc1.input_composition_id = pccon.composition_id)
                 LEFT JOIN labcontrol.pool_composition_components pcc2 ON (
                    pccon.pool_composition_id =
                    pcc2.output_pool_composition_id)
                -- Retrieve amplicon library prep information
                LEFT JOIN labcontrol.library_prep_16s_composition libprepcp2 ON (
                    pcc2.input_composition_id = libprepcp2.composition_id)
                LEFT JOIN labcontrol.composition libprepcpcp2 ON (
                    libprepcp2.composition_id = libprepcpcp2.composition_id)
                LEFT JOIN labcontrol.library_prep_16s_process libpreppr2 ON (
                    libprepcpcp2.upstream_process_id= libpreppr2.process_id)
                LEFT JOIN labcontrol.well libprepwell2 ON (
                    libprepcpcp2.container_id = libprepwell2.container_id)
                LEFT JOIN labcontrol.plate libprepplate2 ON (
                    libprepwell2.plate_id = libprepplate2.plate_id)
                WHERE sequencing_process_id = %s
            )"""

        with sql_connection.TRN as TRN:
            # The additional SQL queries previously here have been moved into
            # _get_additional_prep_metadata(), as they are also used to support
            # _generate_metagenomics_prep_information().
            inst_mdl, equipment, reagent = self._get_additional_prep_metadata()

            # marker gene primer sets
            TRN.add("""SELECT marker_gene_primer_set_id, primer_set_id,
                           target_gene, target_subfragment, linker_sequence,
                           fwd_primer_sequence, rev_primer_sequence, region
                       FROM labcontrol.marker_gene_primer_set""")
            marker_gene_primer_set = {dict(row)['primer_set_id']: dict(row)
                                      for row in TRN.execute_fetchindex()}

            TRN.add(sql, [self.sequencing_process_id])
            for result in TRN.execute_fetchindex():
                result = dict(result)
                study_id = result.pop('study_id')
                content = result.pop('content')

                # format well
                col = result['col_num']
                row = result['row_num']
                well = []
                while row:
                    row, rem = divmod(row - 1, 26)
                    well[:0] = container_module.LETTERS[rem]
                result['well_id'] = ''.join(well) + str(col)

                # format extra fields list
                for t, k, nk in extra_fields:
                    _id = result.pop(k)
                    if _id is not None:
                        if t == 'e':
                            val = equipment[_id]['external_id']
                        else:
                            val = reagent[_id]['external_lot_id']
                    else:
                        val = ''
                    result[nk] = val

                # format some final fields
                result['platform'] = 'Illumina'
                result['instrument_model'] = ''
                result['extraction_robot'] = '%s_%s' % (
                    result.pop('epmotion_robot'),
                    result.pop('kingfisher_robot'))
                result['primer_plate'] = result[
                    'primer_plate'].split(' ')[-1]
                mgps = marker_gene_primer_set[result.pop('primer_set_id')]
                result['PRIMER'] = '%s%s' % (
                    mgps['linker_sequence'], mgps['fwd_primer_sequence'])
                result['pcr_primers'] = 'FWD:%s; REV:%s' % (
                    mgps['fwd_primer_sequence'],
                    mgps['rev_primer_sequence'])
                result['linker'] = mgps['linker_sequence']
                result['target_gene'] = mgps['target_gene']
                result['target_subfragment'] = mgps['target_subfragment']
                result['library_construction_protocol'] = (
                    'Illumina EMP protocol {0} amplification of {1}'
                    ' {2}'.format(mgps['region'], mgps['target_gene'],
                                  mgps['target_subfragment']))
                result['run_center'] = 'UCSDMI'
                result['run_date'] = ''
                result['run_prefix'] = ''
                result['sequencing_meth'] = 'Sequencing by synthesis'
                result['center_name'] = 'UCSDMI'
                result['center_project_name'] = ''
                result['runid'] = ''
                result['instrument_model'] = inst_mdl
                result['orig_name2'] = result['orig_name']

                if result['orig_name2'] is not None and study_id is not None:
                    # strip the prepended study id from orig_name2, but only
                    # if this is an 'experimental sample' row, and not a
                    # 'control' row. (captured here w/orig_name2 and study_id
                    # not equaling None.) This also prevents interference w/the
                    # population of the DataFrame index below, using the
                    # existing list comprehension.
                    result['orig_name2'] = re.sub("^%s\." % study_id,
                                                  '',
                                                  result['orig_name2'])

                # Note: currently we have reverted to generating just one prep
                # sheet for all items in run, but we anticipate that may change
                # back in the near future.  That is why we retain the return
                # structure of a dictionary holding prep sheet strings rather
                # than returning a single prep sheet string even though, at the
                # moment, the dictionary will always have only one entry.
                curr_prep_sheet_id = self.run_name
                if curr_prep_sheet_id not in data:
                    data[curr_prep_sheet_id] = {}

                # if we want the sample_name.well_id, just replace sid
                # for content
                data[curr_prep_sheet_id][content] = result

        plate_col_name = 'Sample_Plate'
        proj_col_name = 'Project_name'

        # converting from dict to pandas and then to tsv
        for curr_prep_sheet_id, vals in data.items():
            df = pd.DataFrame.from_dict(vals, orient='index')
            # the index/sample_name should be the original name if
            # it's not duplicated or None (blanks/spikes)
            dup_names = df[df.orig_name.duplicated()].orig_name.unique()
            df.index = [v if v and v not in dup_names else k
                        for k, v in df.orig_name.iteritems()]
            # If orig_name2 is none (because this item is a control),
            # use its content
            df.orig_name2 = [v if v else k for k, v in
                             df.orig_name2.iteritems()]

            df['well_description'] = ['%s_%s_%s' % (
                x.sample_plate, i, x.well_id) for i, x in df.iterrows()]

            # 1/3. renaming columns so they match expected casing
            mv = {
                'barcode': 'BARCODE', 'master_mix': 'MasterMix_lot',
                'platform': 'PLATFORM', 'sample_plate': plate_col_name,
                'run_prefix': 'RUN_PREFIX', 'primer_date': 'Primer_date',
                'extraction_robot': 'Extraction_robot',
                'runid': 'RUNID', 'epmotion_tm50_8_tool': 'TM50_8_tool',
                'library_construction_protocol':
                    'LIBRARY_CONSTRUCTION_PROTOCOL',
                'plating': 'Plating', 'linker': 'LINKER',
                'project_name': proj_col_name, 'orig_name2': 'Orig_name',
                'well_id': 'Well_ID', 'water_lot': 'Water_Lot',
                'well_description': 'Well_description',
                'run_center': 'RUN_CENTER',
                'epmotion_tool': 'TM1000_8_tool',
                'extraction_kit': 'ExtractionKit_lot',
                'primer_plate': 'Primer_Plate', 'run_date': 'RUN_DATE',
                'gdata_robot': 'Processing_robot',
                'epmotion_tm300_8_tool': 'TM300_8_tool',
                'instrument_model': 'INSTRUMENT_MODEL',
                'experiment_design_description':
                    'EXPERIMENT_DESIGN_DESCRIPTION'
            }
            df.rename(index=str, columns=mv, inplace=True)
            # as orig_name2 has been transformed into Orig_name, and
            # the original orig_name column has been used to generate df.index,
            # which will be used as the sample name, there is no longer a
            # purpose for the original orig_name column, hence drop it from the
            # final output.
            df.drop(['orig_name'], axis=1)

            # Set the project column value for each non-experimental sample to
            # the value of the project name for the (single) qiita study on
            # that sample's plate.
            df = self._set_control_values_to_plate_value(df, plate_col_name,
                                                         proj_col_name)

            # 2/3. sorting rows
            rows_order = [plate_col_name, 'row_num', 'col_num']
            df.sort_values(by=rows_order, inplace=True)
            # 3/3. sorting and keeping only required columns
            order = [
                'BARCODE', 'PRIMER', 'Primer_Plate', 'Well_ID', 'Plating',
                'ExtractionKit_lot', 'Extraction_robot', 'TM1000_8_tool',
                'Primer_date', 'MasterMix_lot', 'Water_Lot',
                'Processing_robot', 'TM300_8_tool', 'TM50_8_tool',
                plate_col_name, proj_col_name, 'Orig_name',
                'Well_description', 'EXPERIMENT_DESIGN_DESCRIPTION',
                'LIBRARY_CONSTRUCTION_PROTOCOL', 'LINKER', 'PLATFORM',
                'RUN_CENTER', 'RUN_DATE', 'RUN_PREFIX', 'pcr_primers',
                'sequencing_meth', 'target_gene', 'target_subfragment',
                'center_name', 'center_project_name', 'INSTRUMENT_MODEL',
                'RUNID']
            df = df[order]
            sio = StringIO()
            df.to_csv(sio, sep='\t', index_label='sample_name')
            data[curr_prep_sheet_id] = sio.getvalue()

        return data


class SampleSheetShotgun(SampleSheet):
    def __init__(self, **kwargs):
        # assume keys exist, and let KeyErrors pass up to the user
        self.sequencing_process_id = kwargs['sequencing_process_id']
        self.include_lane = kwargs['include_lane']
        self.pools = kwargs['pools']
        self.principal_investigator = kwargs['principal_investigator']
        self.contacts = kwargs['contacts']
        self.experiment = kwargs['experiment']
        self.date = kwargs['date']
        self.fwd_cycles = kwargs['fwd_cycles']
        self.rev_cycles = kwargs['rev_cycles']
        self.run_name = kwargs['run_name']
        self.sequencer = kwargs['sequencer']
        # although we know that assay_type is likely 'Metagenomic' etc.
        # because this is the SampleSheetShotgun class, we will centralize
        # the string value assignment upstream and simply use what is passed
        # by the factory.
        self.assay_type = kwargs['assay_type']

    @staticmethod
    def _format_sample_sheet_data(sample_ids, i7_name, i7_seq, i5_name, i5_seq,
                                  sample_projs, wells=None, sample_plates=None,
                                  description=None, lanes=None, sep=',',
                                  include_header=True, include_lane=True):
        """Creates the [Data] component of the Illumina sample sheet

        Parameters
        ----------
        sample_ids: array-like
            The bcl2fastq-compatible sample ids
        i7_name: array-like
            The i7 index name, in sample_ids order
        i7_seq: array-like
            The i7 sequences, in sample_ids order
        i5_name: array-like
            The i5 index name, in sample_ids order
        i5_seq: array-like
            The i5 sequences, in sample_ids order
        wells: array-like, optional
            The well in which the sample is found on the compressed gDNA plate,
            in sample_ids order. Default: None
        sample_plate: str, optional
            The human-readable *sample* plate name. Default: ''
            NB: This is NOT the plate that the well, above, is relevant to.
            This fact is not a bug but rather a user requirement per Greg
            Humphrey.
        sample_projs: array-like
            The per-sample short project names for use in grouping
            demultiplexed samples
        description: array-like, optional
            The original sample ids, in sample_ids order. Default: None
        lanes: array-like, optional
            The lanes in which the pool will be sequenced. Default: [1]
        sep: str, optional
            The file-format separator. Default: ','
        include_header: bool, optional
            Whether to include the header or not. Default: true
        include_lane: bool, optional
            Whether to include lane index as the first column. Default: true

        Returns
        -------
        str
            The formatted [Data] component of the Illumina sample sheet

        Raises
        ------
        ValueError
            If sample_ids, i7_name, i7_seq, i5_name and i5_seq do not have all
            the same length
        """
        if sample_plates is None:
            sample_plates = [''] * len(sample_ids)

        if (len(sample_ids) != len(i7_name) != len(i7_seq) !=
                len(i5_name) != len(i5_seq) != len(sample_plates)):
            raise ValueError('Sample information lengths are not all equal')

        if wells is None:
            wells = [''] * len(sample_ids)
        if description is None:
            description = [''] * len(sample_ids)

        if lanes is None:
            lanes = [1]

        data = []
        for lane in lanes:
            for i, sample in enumerate(sample_ids):
                row = [sample, sample, sample_plates[i], wells[i], i7_name[i],
                       i7_seq[i], i5_name[i], i5_seq[i], sample_projs[i],
                       description[i]]
                if include_lane:
                    row.insert(0, str(lane))
                data.append(sep.join(row))

        data = sorted(data)
        if include_header:
            columns = [
                'Sample_ID', 'Sample_Name', 'Sample_Plate',
                'Sample_Well', 'I7_Index_ID', 'index', 'I5_Index_ID', 'index2',
                'Sample_Project', 'Well_Description']
            if include_lane:
                columns.insert(0, 'Lane')
            data.insert(0, sep.join(columns))

        return '\n'.join(data)

    def generate(self):
        """Generates Illumina compatible shotgun sample sheets

        Returns
        -------
        str
            The illumina-formatted sample sheet
        """
        bcl2fastq_sample_ids = []
        i7_names = []
        i7_sequences = []
        i5_names = []
        i5_sequences = []
        wells = []
        samples_contents = []
        sample_proj_values = []
        sample_plates = []
        sequencer_type = self.sequencer.equipment_type

        data = []
        include_header = True
        for pool, lane in self.pools:
            for component in pool.components:
                libprepshotgun_composition = component['composition']
                compressed_gdna_composition = libprepshotgun_composition. \
                    normalized_gdna_composition.compressed_gdna_composition
                # Get the well of this component ON THE COMPRESSED GDNA PLATE
                well = compressed_gdna_composition.container
                wells.append(well.well_id)
                # Get the human-readable name of the SAMPLE plate from which
                # this component came
                sample_composition = compressed_gdna_composition. \
                    gdna_composition.sample_composition
                sample_well = sample_composition.container
                sample_plates.append(sample_well.plate.external_id)
                # Get the i7 index information
                i7_comp = libprepshotgun_composition. \
                    i7_composition.primer_set_composition
                i7_names.append(i7_comp.external_id)
                i7_sequences.append(i7_comp.barcode)
                # Get the i5 index information
                i5_comp = libprepshotgun_composition. \
                    i5_composition.primer_set_composition
                i5_names.append(i5_comp.external_id)
                i5_sequences.append(i5_comp.barcode)

                # Get the sample content (used as description)
                sample_content = sample_composition.content
                # sample_content is the labcontrol.sample_composition.content
                # value, which is the "true" sample_id plus a "." plus the
                # plate id of the plate on which the sample was plated, plus
                # another "." and the well (e.g., "A1") into which the sample
                # was plated on that plate.
                samples_contents.append(sample_content)

                true_sample_id = sample_composition.sample_id
                sample_proj_values.append(self._generate_sample_proj_value(
                    true_sample_id))

            # Transform the sample ids to be bcl2fastq-compatible
            bcl2fastq_sample_ids = [
                Sheet._bcl_scrub_name(sid) for sid in
                samples_contents]
            bcl2fastq_sample_plates = [
                Sheet._bcl_scrub_name(sid) for sid in
                sample_plates]
            # Reverse the i5 sequences if needed based on the sequencer
            i5_sequences = SampleSheet._sequencer_i5_index(
                sequencer_type, i5_sequences)

            # Note: laundering arrays into a dataframe and back is not optimal.
            # However, the "parallel arrays" data structure used here would
            # itself make more sense as a dataframe, so it seems undesirable
            # to change _set_conrol_values_to_plate_value to use arrays.
            plate = "plate"
            proj = "proj"
            plate_proj_df = pd.DataFrame({plate: bcl2fastq_sample_plates,
                                          proj: sample_proj_values})
            adj_plate_proj_df = self._set_control_values_to_plate_value(
                plate_proj_df, plate, proj)
            sample_proj_values = adj_plate_proj_df[proj].tolist()

            # add the data of the current pool
            data.append(self._format_sample_sheet_data(
                bcl2fastq_sample_ids, i7_names, i7_sequences, i5_names,
                i5_sequences, sample_proj_values, wells=wells,
                sample_plates=bcl2fastq_sample_plates,
                description=samples_contents, lanes=[lane], sep=',',
                include_header=include_header, include_lane=self.include_lane))
            include_header = False

        data = '\n'.join(data)
        return self._format_sample_sheet(data)

    @staticmethod
    def _generate_sample_proj_value(sample_id):
        """Generate a short name for the project from which the sample came.

        This value is intended to be placed in the sample sheet in the
        sample_proj field as a unique reference allowing demultiplexing to
        assign demuxed fastq files automatically to their project folder.

        The value is expected to be the same for each sample that comes
        from the same project.

        Parameters
        ----------
        sample_id : str or NoneType
            The value of the sample_id column from qiita.study_sample for the
            sample of interest. For samples with no sample_id (e.g., controls,
            blanks, empties), the value is None.

        Raises
        ------
        ValueError
            If the sample_id is associated with more than one study--
            this should never happen.


        Returns
        -------
        str
            A short name for the project from which the sample comes.
        """

        result = None

        with sql_connection.TRN as TRN:
            sql = """
                SELECT study_id, sp1.name as lab_person_name,
                        sp2.name as principal_investigator_name
                FROM qiita.study_sample
                INNER JOIN qiita.study st USING (study_id)
                -- Self-join qiita.study_person to get both
                -- lab person id and study person id in one record
                INNER JOIN qiita.study_person sp1 ON (
                    st.lab_person_id = sp1.study_person_id)
                INNER JOIN qiita.study_person sp2 ON (
                    st.principal_investigator_id = sp2.study_person_id)
                WHERE sample_id = %s
                """
            TRN.add(sql, [sample_id])

            for study_id, lab_person_name, principal_investigator_name in \
                    TRN.execute_fetchindex():
                # If we already set the result, then there is more than one
                # record pulled back by the query, and this means we have a
                # data integrity problem!
                if result is not None:
                    raise ValueError(
                        "Sample id {0} is associated with multiple"
                        "combinations of study id, lab person id, and "
                        "principal investigator id.".format(sample_id))

                result = "{0}_{1}_{2}".format(
                    lab_person_name, principal_investigator_name, study_id)
                result = Sheet._folder_scrub_name(result)

        return result

    def _format_sample_sheet(self, data, sep=','):
        """Formats Illumina-compatible sample sheet.

        Parameters
        ----------
        data: array-like of str
            A list of strings containing formatted strings to include in the
            [Data] component of the sample sheet

        Returns
        -------
        sample_sheet : str
            the sample sheet string
        """
        contacts = {c.name: c.email for c in self.contacts}
        principal_investigator = {self.principal_investigator.name:
                                      self.principal_investigator.email}
        sample_sheet_dict = {
            'comments': self._format_sample_sheet_comments(
                principal_investigator=principal_investigator,
                contacts=contacts),
            'IEMFileVersion': '4',
            'Investigator Name': self.principal_investigator.name,
            'Experiment Name': self.experiment,
            'Date': datetime.strftime(self.date, Sheet.get_date_format()),
            'Workflow': 'GenerateFASTQ',
            'Application': 'FASTQ Only',
            'Assay': self.assay_type,
            'Description': '',
            'Chemistry': 'Default',
            'read1': self.fwd_cycles,
            'read2': self.rev_cycles,
            'ReverseComplement': '0',
            'data': data}

        template = (
            '{comments}[Header]\nIEMFileVersion{sep}{IEMFileVersion}\n'
            'Investigator Name{sep}{Investigator Name}\n'
            'Experiment Name{sep}{Experiment Name}\nDate{sep}{Date}\n'
            'Workflow{sep}{Workflow}\nApplication{sep}{Application}\n'
            'Assay{sep}{Assay}\nDescription{sep}{Description}\n'
            'Chemistry{sep}{Chemistry}\n\n[Reads]\n{read1}\n{read2}\n\n'
            '[Settings]\nReverseComplement{sep}{ReverseComplement}\n\n'
            '[Data]\n{data}'
        )

        if sample_sheet_dict['comments']:
            sample_sheet_dict['comments'] = re.sub(
                '^', '# ', sample_sheet_dict['comments'].rstrip(),
                flags=re.MULTILINE) + '\n'
        sample_sheet = template.format(**sample_sheet_dict, **{'sep': sep})
        return sample_sheet


class PrepInfoSheetShotgun(PrepInfoSheet):
    def __init__(self, **kwargs):
        # assume keys exist, and let KeyErrors pass up to the user
        self.sequencing_process_id = kwargs['sequencing_process_id']
        self.include_lane = kwargs['include_lane']
        self.pools = kwargs['pools']
        self.principal_investigator = kwargs['principal_investigator']
        self.contacts = kwargs['contacts']
        self.experiment = kwargs['experiment']
        self.date = kwargs['date']
        self.fwd_cycles = kwargs['fwd_cycles']
        self.rev_cycles = kwargs['rev_cycles']
        self.run_name = kwargs['run_name']
        self.sequencer = kwargs['sequencer']

    def _get_metagenomics_data_for_prep(self):
        """Gathers prep_info metadata for Metagenomics file generation

        A support method for Metagenomics prep info file generation. This
        method is only called by _generate_metagenomics_prep_information().
        Gathers metadata used by above method and performs initial munging
        for clarity.

        Returns
        -------
        list: dict, each one representing a row of results.

        Notes
        -----
        This fetchall() seemed appropriate, as we only expect to return several
        hundred results at most. This allows us to capture the results and
        clean them up before handing them off. This also allows us to refactor
        this query in time without touching the rest of the code.
        """
        inst_mdl, equipment, reagent = self._get_additional_prep_metadata()

        sql = """
                SELECT
                    study.study_id,
                    study_sample.sample_id,
                    study.study_alias AS project_name,
                    study_sample.sample_id AS orig_name,
                    study.study_description AS experiment_design_description,
                    samplewell.row_num AS row_num,
                    samplewell.col_num AS col_num,
                    samplecp.content,
                    sampleplate.external_id AS sample_plate,
                    platingprpr.run_personnel_id AS plating,
                    gdnaextractpr.extraction_kit_id,
                    gdnaextractpr.epmotion_robot_id AS gepmotion_robot_id,
                    gdnaextractpr.epmotion_tool_id,
                    gdnaextractpr.kingfisher_robot_id,
                    libpreppr.kapa_hyperplus_kit_id,
                    libpreppr.stub_lot_id,
                    primersetcp.barcode_seq AS barcode_i5,
                    primersetcp2.barcode_seq AS barcode_i7,
                    primersetcp.primer_set_id AS primer_set_id_i5,
                    primersetcp2.primer_set_id AS primer_set_id_i7,
                    primersetcp.external_id AS i5_index_id,
                    primersetcp2.external_id AS i7_index_id,
                    primersetplate.external_id AS primer_plate_i5,
                    primersetplate2.external_id AS primer_plate_i7,
                    primerworkingplateprpr.run_date AS primer_date_i5,
                    primerworkingplateprpr2.run_date AS primer_date_i7
                FROM labcontrol.plate libprepplate
                LEFT JOIN labcontrol.well libprepwell ON (
                    libprepplate.plate_id = libprepwell.plate_id)
                LEFT JOIN labcontrol.composition libprepcpcp ON (
                    libprepwell.container_id = libprepcpcp.container_id)
                LEFT JOIN labcontrol.library_prep_shotgun_process libpreppr ON (
                    libprepcpcp.upstream_process_id = libpreppr.process_id)
                LEFT JOIN labcontrol.library_prep_shotgun_composition libprepcp ON
                    (libprepcpcp.composition_id = libprepcp.composition_id)
                LEFT JOIN labcontrol.normalized_gdna_composition normgdnacp ON (
                    libprepcp.normalized_gdna_composition_id =
                    normgdnacp.normalized_gdna_composition_id)
                LEFT JOIN labcontrol.compressed_gdna_composition compgdnacp ON (
                    normgdnacp.compressed_gdna_composition_id =
                    compgdnacp.compressed_gdna_composition_id)
                LEFT JOIN labcontrol.gdna_composition gdnacp USING (
                    gdna_composition_id)
                LEFT JOIN labcontrol.composition gdnacpcp ON (
                    gdnacp.composition_id = gdnacpcp.composition_id)
                LEFT JOIN labcontrol.gdna_extraction_process gdnaextractpr ON (
                    gdnacpcp.upstream_process_id = gdnaextractpr.process_id)
                LEFT JOIN labcontrol.sample_composition samplecp USING (
                    sample_composition_id)
                LEFT JOIN labcontrol.composition samplecpcp ON (
                    samplecp.composition_id = samplecpcp.composition_id)
                LEFT JOIN labcontrol.well samplewell ON (
                    samplecpcp.container_id = samplewell.container_id)
                LEFT JOIN labcontrol.plate sampleplate ON (
                    samplewell.plate_id = sampleplate.plate_id)
                LEFT JOIN labcontrol.process platingprpr ON (
                    samplecpcp.upstream_process_id = platingprpr.process_id)
                LEFT JOIN labcontrol.primer_composition primercp ON (
                    libprepcp.i5_primer_composition_id =
                    primercp.primer_composition_id)
                LEFT JOIN labcontrol.primer_composition primercp2 ON (
                    libprepcp.i7_primer_composition_id =
                    primercp2.primer_composition_id)
                LEFT JOIN labcontrol.composition primercpcp ON (
                    primercp.composition_id = primercpcp.composition_id)
                LEFT JOIN labcontrol.composition primercpcp2 ON (
                    primercp2.composition_id = primercpcp2.composition_id)
                LEFT JOIN labcontrol.process primerworkingplateprpr ON (
                    primercpcp.upstream_process_id =
                    primerworkingplateprpr.process_id)
                LEFT JOIN labcontrol.process primerworkingplateprpr2 ON (
                    primercpcp2.upstream_process_id =
                    primerworkingplateprpr2.process_id)
                LEFT JOIN labcontrol.primer_set_composition primersetcp ON (
                    primercp.primer_set_composition_id =
                    primersetcp.primer_set_composition_id)
                LEFT JOIN labcontrol.primer_set_composition primersetcp2 ON (
                    primercp2.primer_set_composition_id =
                    primersetcp2.primer_set_composition_id)
                LEFT JOIN labcontrol.composition primersetcpcp ON (
                    primersetcp.composition_id = primersetcpcp.composition_id)
                LEFT JOIN labcontrol.composition primersetcpcp2 ON (
                    primersetcp2.composition_id =
                    primersetcpcp2.composition_id)
                LEFT JOIN labcontrol.well primersetwell ON (
                    primersetcpcp.container_id = primersetwell.container_id)
                LEFT JOIN labcontrol.well primersetwell2 ON (
                    primersetcpcp2.container_id = primersetwell2.container_id)
                LEFT JOIN labcontrol.plate primersetplate ON (
                    primersetwell.plate_id = primersetplate.plate_id)
                LEFT JOIN labcontrol.plate primersetplate2 ON (
                    primersetwell2.plate_id = primersetplate2.plate_id)
                FULL JOIN qiita.study_sample USING (sample_id)
                LEFT JOIN qiita.study as study USING (study_id)
                WHERE libprepplate.plate_id IN (
                    SELECT distinct libprepplate2.plate_id
                    FROM labcontrol.sequencing_process sp
                    LEFT JOIN labcontrol.sequencing_process_lanes spl USING (
                        sequencing_process_id)
                    LEFT JOIN labcontrol.pool_composition_components pcc ON (
                        spl.pool_composition_id =
                        pcc.output_pool_composition_id)
                   LEFT JOIN labcontrol.library_prep_shotgun_composition libprepcp2
                        ON (
                        pcc.input_composition_id = libprepcp2.composition_id)
                    LEFT JOIN labcontrol.composition libprepcpcp2 ON (
                        libprepcp2.composition_id =
                        libprepcpcp2.composition_id)
                    LEFT JOIN labcontrol.library_prep_shotgun_process libpreppr2
                        ON (libprepcpcp2.upstream_process_id =
                        libpreppr2.process_id)
                    LEFT JOIN labcontrol.well libprepwell2 ON (
                        libprepcpcp2.container_id = libprepwell2.container_id)
                    LEFT JOIN labcontrol.plate libprepplate2 ON (
                        libprepwell2.plate_id = libprepplate2.plate_id)
                    WHERE sequencing_process_id = %s)
                """

        with sql_connection.TRN as TRN:
            TRN.add(sql, [self.sequencing_process_id])

            results = [dict(r) for r in TRN.execute_fetchindex()]

            for d in results:
                d['primer_date_i5'] = \
                    d['primer_date_i5'].strftime(Sheet.get_date_format())
                d['primer_date_i7'] = \
                    d['primer_date_i7'].strftime(Sheet.get_date_format())

                # instrument_model remains the same across all rows in this
                # query.
                d['instrument_model'] = inst_mdl

                id = d['kapa_hyperplus_kit_id']
                d['kapa_hyperplus_kit_lot'] = reagent[id]['external_lot_id']

                id = d['stub_lot_id']
                d['stub_lot_id'] = reagent[id]['external_lot_id']

                # refer to https://github.com/jdereus/labman/issues/324
                # for discussion on robot_id columns
                id = d['gepmotion_robot_id']
                epm_robot = equipment[id]['external_id']
                id = d['kingfisher_robot_id']
                kf_robot = equipment[id]['external_id']
                d['extraction_robot'] = '%s_%s' % (epm_robot, kf_robot)

                # Note extraction_kit_id references (as in foreign-key)
                # reagent_composition(reagent_composition_id).
                id = d['extraction_kit_id']
                d['extraction_kit_lot'] = reagent[id]['external_lot_id']

                id = d['epmotion_tool_id']
                d['epmotion_tool_name'] = equipment[id]['external_id']

                # for now, platform is hard-coded to 'Illumina'
                # will need to change once Nanopore is supported by LC
                # and we have a column to record one or the other.
                # See also: https://github.com/jdereus/labman/issues/507
                d['platform'] = 'Illumina'

                # these key/value pairs are tentatively hard-coded for now.
                d['sequencing_method'] = 'sequencing by synthesis'
                d['run_center'] = 'UCSDMI'
                d['library_construction_protocol'] = 'KL KHP'

                # EXPERIMENT_DESIGN_DESCRIPTION as with Amplicon, will remain
                # empty when NULL.

                # Replicating logic from Amplicon pre-processing
                # TODO: refactor to a shared method
                d['orig_name2'] = d['orig_name']

                if d['study_id'] is not None and d['orig_name2'] is not None:
                    # strip the prepended study id from orig_name2, but only
                    # if this is an 'experimental sample' row, and not a
                    # 'control' row. (captured here w/orig_name2 and study_id
                    # not equaling None. This also prevents interference w/the
                    # population of the DataFrame index below, using the
                    # existing list comprehension.
                    d['orig_name2'] = re.sub("^%s\." % d['study_id'],
                                             '',
                                             d['orig_name2'])

            return results

    def _get_additional_prep_metadata(self):
        """Gathers additional prep_info metadata for file generation

        Gathers additional prep_info metadata used in the generation of files
        using additional SQL queries. The data is returned as a tuple of
        dictionaries that can be used to map additional metadata into the
        results of the primary prep info query.

        Returns
        -------
        tuple: (str: The model of instrument for the sequencing run
                dict: equipment_id/dict pairs used to map equipment_id to info
                dict: reagent_id/dict pairs used to map reagent_id to info
               )
        """
        with sql_connection.TRN as TRN:
            # Let's cache some data to avoid querying the DB multiple times:
            # sequencing run - this is definitely still applicable
            TRN.add("""SELECT et.description AS instrument_model
                        FROM labcontrol.sequencing_process sp
                        LEFT JOIN labcontrol.process process USING (process_id)
                        LEFT JOIN labcontrol.equipment e ON (
                            sequencer_id = equipment_id)
                        LEFT JOIN labcontrol.equipment_type et ON (
                            e.equipment_type_id = et.equipment_type_id)
                        LEFT JOIN labcontrol.sequencing_process_lanes spl USING (
                            sequencing_process_id)
                        WHERE sequencing_process_id = %s""", [self.sequencing_process_id])

            instrument_model = [row['instrument_model']
                                for row in TRN.execute_fetchindex()]

            if len(instrument_model) != 1:
                raise ValueError("Expected 1 and only 1 value for sequencing "
                                 "run instrument_model, but received "
                                 "{}".format(len(instrument_model)))

            instrument_model = instrument_model[0]

            TRN.add("""SELECT equipment_id, external_id, notes, description
                                   FROM labcontrol.equipment
                                   LEFT JOIN labcontrol.equipment_type
                                   USING (equipment_type_id)""")

            equipment = {dict(row)['equipment_id']: dict(row)
                         for row in TRN.execute_fetchindex()}

            TRN.add("""SELECT reagent_composition_id, composition_id,
                                       external_lot_id, description
                                   FROM labcontrol.reagent_composition
                                   LEFT JOIN labcontrol.reagent_composition_type
                                   USING (reagent_composition_type_id)""")

            reagent = {dict(row)['reagent_composition_id']: dict(row)
                       for row in TRN.execute_fetchindex()}

        return (instrument_model, equipment, reagent)

    def generate(self):
        """Generates prep information for Metagenomics workflows

        An internal method used to implement the generation of prep information
        files for Metagenomics workflows. This method is called by
        generate_prep_information() only.

        Returns
        -------
        dict: { int: str,
                int: str,
                int: str,
                .
                .
                .
                int: str,
                str: str }

        where 'int: str' represents either a Study ID and a TSV file (in string
        form), or a Prep ID and TSV file (in string form).

        'str: str' represents controls data; the key is the constant
        'Controls', and the value is a TSV file (in string form).
        """
        results = self._get_metagenomics_data_for_prep()

        data = {}

        for item in results:
            # format well
            well = []
            col = item['col_num']
            row = item['row_num']
            while row:
                row, rem = divmod(row - 1, 26)
                well[:0] = container_module.LETTERS[rem]

            # adding a new field to the item
            item['well_id'] = ''.join(well) + str(col)

            # Note: currently we have reverted to generating just one prep
            # sheet for all items in run, but we anticipate that may change
            # back in the near future.  That is why we retain the return
            # structure of a dictionary holding prep sheet strings rather
            # than returning a single prep sheet string even though, at the
            # moment, the dictionary will always have only one entry.
            curr_prep_sheet_id = self.run_name
            if curr_prep_sheet_id not in data:
                data[curr_prep_sheet_id] = {}

            content = item['content']

            # adding item to the data (organized by prep_sheet_id and
            # content string.
            if content in data[curr_prep_sheet_id]:
                s = "'%s' appears more than once in prep_sheet '%s'"
                s = s % (content, curr_prep_sheet_id)
                raise ValueError(s)

            data[curr_prep_sheet_id][content] = item

        # right now, there will only be one prep_sheet_id
        for prep_sheet_id, prep_sheet in data.items():
            prep_sheet = pd.DataFrame.from_dict(prep_sheet, orient='index')

            # If orig_name2 is none (because this item is a control),
            # use its content. Note that if v (the value of orig_name2 at that
            # row) is None, then the value for orig_name2 at that row will
            # become the value of the index (k) for that row. Note that we
            # are not currently using the value of 'is_control'.
            prep_sheet.orig_name2 = [v if v else k for k, v in
                                     prep_sheet.orig_name2.iteritems()]

            # Set the project column value for each non-experimental sample to
            # the value of the project name for the (single) qiita study on
            # that sample's plate.
            prep_sheet = \
                self._set_control_values_to_plate_value(prep_sheet,
                                                        'sample_plate',
                                                        'project_name')

            # mapping keys to expected names for columns in the final output
            mv = {"orig_name2": "Orig_name",
                  "well_id": "Well_ID",
                  "sample_plate": "Sample_Plate",
                  "project_name": "Project_name",
                  "plating": "Plating",
                  "barcode_i7": "index",
                  "barcode_i5": "index2",
                  "primer_plate_i7": "i7_Primer_Plate",
                  "primer_plate_i5": "i5_Primer_Plate",
                  "primer_date_i7": "i7_Primer_date",
                  "primer_date_i5": "i5_Primer_date",
                  "experiment_design_description":
                      "EXPERIMENT_DESIGN_DESCRIPTION",
                  "instrument_model": "INSTRUMENT_MODEL",
                  "kapa_hyperplus_kit_lot": "KAPAHyperPlusKit_lot",
                  "stub_lot_id": "Stub_lot",
                  "platform": "PLATFORM",
                  "sequencing_method": "sequencing_meth",
                  "run_center": "RUN_CENTER",
                  "extraction_robot": "Extraction_robot",
                  "extraction_kit_lot": "ExtractionKit_lot",
                  "epmotion_tool_name": "TM1000_8_tool",
                  "i5_index_id": "i5_Index_ID",
                  "i7_index_id": "i7_Index_ID",
                  "library_construction_protocol":
                      "LIBRARY_CONSTRUCTION_PROTOCOL"}
            prep_sheet = prep_sheet.rename(columns=mv)

            prep_sheet['Orig_Sample_ID'] = [
                self._bcl_scrub_name(id) for id in
                prep_sheet.content]

            prep_sheet['Well_description'] = \
                ['%s_%s_%s' % (x.Sample_Plate, i, x.Well_ID)
                 for i, x in prep_sheet.iterrows()]

            # re-order columns, keeping only what is needed
            order = [
                'Orig_Sample_ID',
                'Orig_name',
                'Well_ID',
                'Well_description',
                'Sample_Plate',
                'Project_name',
                'Plating',
                'ExtractionKit_lot',
                'Extraction_robot',
                'TM1000_8_tool',
                'KAPAHyperPlusKit_lot',
                'Stub_lot',
                'i7_Index_ID',
                'index',
                'i7_Primer_Plate',
                'i7_Primer_date',
                'i5_Index_ID',
                'index2',
                'i5_Primer_Plate',
                'i5_Primer_date',
                'EXPERIMENT_DESIGN_DESCRIPTION',
                'LIBRARY_CONSTRUCTION_PROTOCOL',
                'PLATFORM',
                'RUN_CENTER',
                'RUN_DATE',
                'RUN_PREFIX',
                'sequencing_meth',
                'center_name',
                'center_project_name',
                'INSTRUMENT_MODEL',
                'Lane',
                'forward_read',
                'reverse_read']

            # These columns are to be supplied blank
            prep_sheet['RUN_DATE'] = None
            prep_sheet['RUN_PREFIX'] = None
            prep_sheet['Lane'] = None
            prep_sheet['forward_read'] = None
            prep_sheet['reverse_read'] = None
            prep_sheet['center_name'] = None
            prep_sheet['center_project_name'] = None

            prep_sheet = prep_sheet[order]

            # write out the DataFrame to TSV format
            o = StringIO()

            # Note: this is how the required 'sample_name' column is added to
            # the final output TSV as well.
            prep_sheet.to_csv(o, sep='\t', index_label='sample_name')
            data[prep_sheet_id] = o.getvalue()

        return data

