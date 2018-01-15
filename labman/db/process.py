# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import date, datetime
from io import StringIO
from itertools import chain

import numpy as np
import pandas as pd

from . import base
from . import sql_connection
from . import user as user_module
from . import plate as plate_module
from . import container as container_module
from . import composition as composition_module
from . import equipment as equipment_module


class Process(base.LabmanObject):
    """Base process object

    Attributes
    ----------
    id
    date
    personnel
    """
    @staticmethod
    def factory(process_id):
        """Initializes the correct Process subclass

        Parameters
        ----------
        process_id : int
            The process id

        Returns
        -------
        An instance of a subclass of Process
        """
        factory_classes = {
            # 'primer template creation': TODO,
            # 'reagent creation': TODO,
            'primer working plate creation': PrimerWorkingPlateCreationProcess,
            'sample plating': SamplePlatingProcess,
            'reagent creation': ReagentCreationProcess,
            'gDNA extraction': GDNAExtractionProcess,
            '16S library prep': LibraryPrep16SProcess,
            'shotgun library prep': LibraryPrepShotgunProcess,
            'quantification': QuantificationProcess,
            'gDNA normalization': NormalizationProcess,
            'pooling': PoolingProcess,
            'sequencing': SequencingProcess}

        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM qiita.process_type
                        JOIN qiita.process USING (process_type_id)
                     WHERE process_id = %s"""
            TRN.add(sql, [process_id])
            p_type = TRN.execute_fetchlast()
            constructor = factory_classes[p_type]

            if constructor._table == 'qiita.process':
                instance = constructor(process_id)
            else:
                sql = """SELECT {}
                         FROM {}
                         WHERE process_id = %s""".format(
                            constructor._id_column, constructor._table)
                TRN.add(sql, [process_id])
                subclass_id = TRN.execute_fetchlast()
                instance = constructor(subclass_id)

        return instance

    @classmethod
    def _common_creation_steps(cls, user):
        with sql_connection.TRN as TRN:
            sql = """SELECT process_type_id
                     FROM qiita.process_type
                     WHERE description = %s"""
            TRN.add(sql, [cls._process_type])
            pt_id = TRN.execute_fetchlast()

            sql = """INSERT INTO qiita.process
                        (process_type_id, run_date, run_personnel_id)
                     VALUES (%s, %s, %s)
                     RETURNING process_id"""
            TRN.add(sql, [pt_id, date.today(), user.id])
            p_id = TRN.execute_fetchlast()
        return p_id

    def _get_process_attr(self, attr):
        """Returns the value of the given process attribute

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
                     FROM qiita.process
                        JOIN {} USING (process_id)
                     WHERE {} = %s""".format(attr, self._table,
                                             self._id_column)
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def date(self):
        return self._get_process_attr('run_date')

    @property
    def personnel(self):
        return user_module.User(self._get_process_attr('run_personnel_id'))

    @property
    def process_id(self):
        return self._get_process_attr('process_id')

    @property
    def plates(self):
        """The plates being extracted by this process

        Returns
        -------
        plate : list of labman.db.Plate
            The extracted plates
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM qiita.container
                        LEFT JOIN qiita.well USING (container_id)
                     WHERE latest_upstream_process_id = %s
                     ORDER BY plate_id"""
            TRN.add(sql, [self.process_id])
            plate_ids = TRN.execute_fetchflatten()
        return [plate_module.Plate(plate_id) for plate_id in plate_ids]


class _Process(Process):
    """Process object

    Not all processes have a specific subtable, so we need to override the
    date and personnel attributes

    Attributes
    ----------
    id
    date
    personnel
    """
    _table = 'qiita.process'
    _id_column = 'process_id'

    @property
    def date(self):
        return self._get_attr('run_date')

    @property
    def personnel(self):
        return user_module.User(self._get_attr('run_personnel_id'))

    @property
    def process_id(self):
        return self._get_attr('process_id')


class SamplePlatingProcess(_Process):
    """Sample plating process"""

    _process_type = 'sample plating'

    @classmethod
    def create(cls, user, plate_config, plate_ext_id, volume=None):
        """Creates a new sample plating process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the plating
        plate_config : labman.db.PlateConfiguration
            The sample plate configuration
        plate_ext_id : str
            The external plate id
        volume : float, optional
            Starting well volume

        Returns
        -------
        SamplePlatingProcess
        """
        with sql_connection.TRN:
            volume = volume if volume else 0
            # Add the row to the process table
            instance = cls(cls._common_creation_steps(user))

            # Create the plate
            plate = plate_module.Plate.create(plate_ext_id, plate_config)

            # By definition, all well plates are blank at the beginning
            # so populate all the wells in the plate with BLANKS
            for i in range(plate_config.num_rows):
                for j in range(plate_config.num_columns):
                    well = container_module.Well.create(
                        plate, instance, volume, i + 1, j + 1)
                    composition_module.SampleComposition.create(
                        instance, well, volume)

        return instance

    @property
    def plate(self):
        """The plate being plated by this process

        Returns
        -------
        plate : labman.db.Plate
            The plate being plated
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM qiita.container
                        LEFT JOIN qiita.well USING (container_id)
                        LEFT JOIN qiita.plate USING (plate_id)
                     WHERE latest_upstream_process_id = %s"""
            TRN.add(sql, [self.id])
            plate_id = TRN.execute_fetchlast()
        return plate_module.Plate(plate_id)

    def update_well(self, row, col, content):
        """Updates the content of a well

        Parameters
        ----------
        row: int
            The well row
        col: int
            The well column
        content: str
            The new contents of the well
        """
        self.plate.get_well(row, col).composition.update(content)


class ReagentCreationProcess(_Process):
    """Reagent creation process"""

    _process_type = 'reagent creation'

    @classmethod
    def create(cls, user, external_id, volume, reagent_type):
        """Creates a new reagent creation process

        Parameters
        ----------
        user : labman.db.user.User
            User adding the reagent to the system
        external_id: str
            The external id of the reagent
        volume: float
            Initial reagent volume
        reagent_type : str
            The type of the reagent

        Returns
        -------
        ReagentCreationProce
        """
        with sql_connection.TRN:
            # Add the row to the process table
            instance = cls(cls._common_creation_steps(user))

            # Create the tube and the composition
            tube = container_module.Tube.create(instance, external_id, volume)
            composition_module.ReagentComposition.create(
                instance, tube, volume, reagent_type, external_id)

        return instance

    @property
    def tube(self):
        """The tube storing the reagent"""
        with sql_connection.TRN as TRN:
            sql = """SELECT tube_id
                     FROM qiita.tube
                        LEFT JOIN qiita.container USING (container_id)
                     WHERE latest_upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            tube_id = TRN.execute_fetchlast()
        return container_module.Tube(tube_id)


class PrimerWorkingPlateCreationProcess(Process):
    """Primer working plate creation process object

    Attributes
    ----------
    primer_set
    master_set_order_number
    """
    _table = 'qiita.primer_working_plate_creation_process'
    _id_column = 'primer_working_plate_creation_process_id'
    _process_type = 'primer working plate creation'

    @property
    def primer_set(self):
        """The primer set template from which the working plates are created

        Returns
        -------
        PrimerSet
        """
        return composition_module.PrimerSet(self._get_attr('primer_set_id'))

    @property
    def master_set_order(self):
        """The master set order

        Returns
        -------
        str
        """
        return self._get_attr('master_set_order_number')


class GDNAExtractionProcess(Process):
    """gDNA extraction process object

    Attributes
    ----------
    robot
    kit
    tool

    See Also
    --------
    Process
    """
    _table = 'qiita.gdna_extraction_process'
    _id_column = 'gdna_extraction_process_id'
    _process_type = 'gDNA extraction'

    @property
    def robot(self):
        """The robot used during extraction

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(
            self._get_attr('extraction_robot_id'))

    @property
    def kit(self):
        """The kit used during extraction

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('extraction_kit_id'))

    @property
    def tool(self):
        """The tool used during extraction

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(self._get_attr('extraction_tool_id'))

    @classmethod
    def create(cls, user, robot, tool, kit, plates, volume):
        """Creates a new gDNA extraction process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the gDNA extraction
        robot: labman.db.equipment.Equipment
            The robot used for the extraction
        tool: labman.db.equipment.Equipment
            The tool used for the extraction
        kit : labman.db.composition.ReagentComposition
            The extraction kit used for the extraction
        plates: list of labman.db.plate.Plate
            The plates to be extracted
        volume : float
            The volume extracted

        Returns
        -------
        GDNAExtractionProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the gdna_extraction_process table
            sql = """INSERT INTO qiita.gdna_extraction_process
                        (process_id, extraction_robot_id, extraction_kit_id,
                         extraction_tool_id)
                     VALUES (%s, %s, %s, %s)
                     RETURNING gdna_extraction_process_id"""
            TRN.add(sql, [process_id, robot.id, kit.id, tool.id])
            instance = cls(TRN.execute_fetchlast())

            for plate in plates:
                # Create the extracted plate
                plate_ext_id = 'gdna - %s' % plate.external_id

                plate_config = plate.plate_configuration
                gdna_plate = plate_module.Plate.create(plate_ext_id,
                                                       plate_config)
                plate_layout = plate.layout

                # Add the wells to the new plate
                for i in range(plate_config.num_rows):
                    for j in range(plate_config.num_columns):
                        well = container_module.Well.create(
                            gdna_plate, instance, volume, i + 1, j + 1)
                        composition_module.GDNAComposition.create(
                            instance, well, volume,
                            plate_layout[i][j].composition)

        return instance


class GDNAPlateCompressionProcess(_Process):
    """Gets 2 to 4 96-well gDNA plates and remaps them in a 384-well plate

    The remapping schema follows this strucutre:
    A B A B A B A B ...
    C D C D C D C D ...
    A B A B A B A B ...
    C D C D C D C D ...
    ...
    """
    _process_type = "compress gDNA plates"

    def _compress_plate(self, out_plate, in_plate, row_pad, col_pad, volume=1):
        """Compresses the 94-well in_plate into the 384-well out_plate"""
        with sql_connection.TRN:
            layout = in_plate.layout
            for row in layout:
                for well in row:
                    # The row/col pair is stored in the DB starting at 1
                    # subtract 1 to make it start at 0 so the math works
                    # and re-add 1 at the end
                    out_well_row = (((well.row - 1) * 2) + row_pad) + 1
                    out_well_col = (((well.column - 1) * 2) + col_pad) + 1
                    out_well = container_module.Well.create(
                        out_plate, self, volume, out_well_row, out_well_col)
                    composition_module.GDNAComposition.create(
                        self, out_well, volume,
                        well.composition.sample_composition)

    @classmethod
    def create(cls, user, plates, plate_ext_id):
        """Creates a new gDNA compression process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the plating
        plates: list of labman.db.plate.Plate
            The plates to compress
        plate_ext_id : str
            The external plate id

        Raises
        ------
        ValueError

        Returns
        -------
        GDNAPlateCompressionProcess
        """
        if not (2 <= len(plates) <= 4):
            raise ValueError(
                'Cannot compress %s gDNA plates. Please provide 2 to 4 '
                'gDNA plates' % len(plates))
        with sql_connection.TRN:
            # Add the row to the process table
            instance = cls(cls._common_creation_steps(user))

            # Create the output plate
            # Magic number 3 -> 384-well plate
            plate = plate_module.Plate.create(
                plate_ext_id, plate_module.PlateConfiguration(3))

            # Compress the plates
            instance._compress_plate(plate, plates[0], 0, 0)
            instance._compress_plate(plate, plates[1], 0, 1)
            if len(plates) > 2:
                instance._compress_plate(plate, plates[2], 1, 0)
                if len(plates) > 3:
                    instance._compress_plate(plate, plates[3], 1, 1)

        return instance


class LibraryPrep16SProcess(Process):
    """16S Library Prep process object

    Attributes
    ----------
    master_mix
    tm300_8_tool
    tm50_8_tool
    water_lot
    processing_robot

    See Also
    --------
    Process
    """
    _table = 'qiita.library_prep_16s_process'
    _id_column = 'library_prep_16s_process_id'
    _process_type = '16S library prep'

    @classmethod
    def create(cls, user, master_mix, water, robot, tm300_8_tool, tm50_8_tool,
               volume, plates):
        """Creates a new 16S library prep process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the library prep
        master_mix : labman.db.composition.ReagentComposition
            The master mix used for preparing the library
        water : labman.db.composition.ReagentComposition
            The water used for preparing the library
        robot : labman.db.equipment.equipment
            The robot user for preparing the library
        tm300_8_tool : labman.db.equipment.equipment
            The tm300_8_tool user for preparing the library
        tm50_8_tool : labman.db.equipment.equipment
            The tm50_8_tool user for preparing the library
        volume : float
            The initial volume in the wells
        plates : list of tuples of (Plate, Plate)
            The firt plate of the tuple is the gDNA plate in which a new
            prepis going to take place and the second plate is the primer
            plate used.

        Returns
        -------
        LibraryPrep16SProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the library_prep_16s_process
            sql = """INSERT INTO qiita.library_prep_16s_process
                        (process_id, master_mix_id, tm300_8_tool_id,
                         tm50_8_tool_id, water_id, processing_robot_id)
                     VALUES (%s, %s, %s, %s, %s, %s)
                     RETURNING library_prep_16s_process_id"""
            TRN.add(sql, [process_id, master_mix.id, tm300_8_tool.id,
                          tm50_8_tool.id, water.id, robot.id])
            instance = cls(TRN.execute_fetchlast())

            for gdna_plate, primer_plate in plates:
                # Create the library plate
                plate_ext_id = '16S library - %s' % gdna_plate.external_id

                plate_config = gdna_plate.plate_configuration
                library_plate = plate_module.Plate.create(plate_ext_id,
                                                          plate_config)
                gdna_layout = gdna_plate.layout
                primer_layout = primer_plate.layout
                for i in range(plate_config.num_rows):
                    for j in range(plate_config.num_columns):
                        well = container_module.Well.create(
                            library_plate, instance, volume, i + 1, j + 1)
                        composition_module.LibraryPrep16SComposition.create(
                            instance, well, volume,
                            gdna_layout[i][j].composition,
                            primer_layout[i][j].composition)

        return instance

    @property
    def master_mix(self):
        """The master mix used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('master_mix_id'))

    @property
    def tm300_8_tool(self):
        """The tm300_8 tool used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(
            self._get_attr('tm300_8_tool_id'))

    @property
    def tm50_8_tool(self):
        """The tm50_8 tool used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(self._get_attr('tm50_8_tool_id'))

    @property
    def water_lot(self):
        """The water lot used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('water_id'))

    @property
    def processing_robot(self):
        """The processing robot used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(
            self._get_attr('processing_robot_id'))


class NormalizationProcess(Process):
    """Normalization process object

    Attributes
    ----------
    quantification_process
    water_lot

    See Also
    --------
    Process
    """
    _table = 'qiita.normalization_process'
    _id_column = 'normalization_process_id'
    _process_type = 'gDNA normalization'

    @staticmethod
    def _calculate_norm_vol(dna_concs, ng=5, min_vol=2.5, max_vol=3500,
                            resolution=2.5):
        """Calculates nanoliters of each sample to add to get a normalized pool

        Parameters
        ----------
        dna_concs : numpy array of float
            The concentrations calculated via PicoGreen (ng/uL)
        ng : float, optional
            The amount of DNA to pool (ng). Default: 5
        min_vol : float, optional
            The minimum volume to pool (nL). Default: 2.5
        max_vol : float, optional
            The maximum volume to pool (nL). Default: 3500
        resolution: float, optional
            Resolution to use (nL). Default: 2.5

        Returns
        -------
        sample_vols : numpy array of float
            The volumes to pool (nL)
        """
        sample_vols = ng / np.nan_to_num(dna_concs) * 1000
        sample_vols = np.clip(sample_vols, min_vol, max_vol)
        sample_vols = np.round(sample_vols / resolution) * resolution
        return sample_vols

    @classmethod
    def create(cls, user, quant_process, water, plate_name, total_vol=3500,
               ng=5, min_vol=2.5, max_vol=3500, resolution=2.5,
               reformat=False):
        """Creates a new normalization process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the gDNA extraction
        quant_process : QuantificationProcess
            The quantification process to use for normalization
        water: ReagentComposition
            The water lot used for the normalization
        plate_name: str
            The output plate name
        total_vol: float, optional
            The total volume of normalized DNA (nL). Default: 3500
        ng : float, optional
            The amount of DNA to pool (ng). Default: 5
        min_vol : float, optional
            The minimum volume to pool (nL). Default: 2.5
        max_vol : float, optional
            The maximum volume to pool (nL). Default: 3500
        resolution: float, optional
            Resolution to use. Default: 2.5
        reformat: bool, optional
            If true, reformat the plate from the interleaved format to the
            column format. Useful when 384-well plate is not full to save
            reagents. Default: False

        Returns
        -------
        NormalizationProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the normalization_process tables
            sql = """INSERT INTO qiita.normalization_process
                        (process_id, quantitation_process_id, water_lot_id)
                     VALUES (%s, %s, %s)
                     RETURNING normalization_process_id"""
            TRN.add(sql, [process_id, quant_process.id, water.id])
            instance = cls(TRN.execute_fetchlast())

            # Retrieve all the concentration values
            concs = quant_process.concentrations
            # Transform the concentrations to a numpy array
            np_conc = np.asarray([raw_con for _, raw_con in concs])
            dna_v = NormalizationProcess._calculate_norm_vol(
                np_conc, ng, min_vol, max_vol, resolution)
            water_v = total_vol - dna_v

            # Create the plate. 3 -> 384-well plate
            plate_config = plate_module.PlateConfiguration(3)
            plate = plate_module.Plate.create(plate_name, plate_config)
            for (comp, _), dna_vol, water_vol in zip(concs, dna_v, water_v):
                comp_well = comp.container
                row = comp_well.row
                column = comp_well.column

                if reformat:
                    row = row - 1
                    column = column - 1

                    roffset = row % 2
                    row = int(row - roffset + np.floor(column / 12)) + 1

                    coffset = column % 2 + (row % 2) * 2
                    column = int(coffset * 6 + (column / 2) % 6) + 1

                well = container_module.Well.create(
                    plate, instance, total_vol, row, column)
                composition_module.NormalizedGDNAComposition.create(
                    instance, well, total_vol, comp, dna_vol, water_vol)

        return instance

    @property
    def quantification_process(self):
        """The quantification process used

        Returns
        -------
        QuantificationProcess
        """
        return QuantificationProcess(self._get_attr('quantitation_process_id'))

    @property
    def water_lot(self):
        """The water lot used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('water_lot_id'))

    @staticmethod
    def _format_picklist(dna_vols, water_vols, wells, dest_wells=None,
                         dna_concs=None, sample_names=None,
                         dna_plate_name='Sample', water_plate_name='Water',
                         dna_plate_type='384PP_AQ_BP2_HT',
                         water_plate_type='384PP_AQ_BP2_HT',
                         dest_plate_name='NormalizedDNA',
                         dna_plate_names=None):
        """Formats Echo pick list to achieve a normalized input DNA pool

        Parameters
        ----------
        dna_vols:  numpy array of float
            The volumes of dna to add
        water_vols:  numpy array of float
            The volumes of water to add
        wells: numpy array of str
            The well codes in the same orientation as the DNA concentrations
        dest_wells: numpy array of str
            The well codes, in the same orientation as `wells`,
            in which to place each sample if reformatting
        dna_concs:  numpy array of float
            The concentrations calculated via PicoGreen (ng/uL)
        sample_names: numpy array of str
            The sample names in the same orientation as the DNA concentrations

        Returns
        -------
        picklist : str
            The Echo formatted pick list
        """
        # check that arrays are the right size
        if dna_vols.shape != wells.shape != water_vols.shape:
            raise ValueError(
                'dna_vols %r has a size different from wells %r or water_vols'
                % (dna_vols.shape, wells.shape, water_vols.shape))

        # if destination wells not specified, use source wells
        if dest_wells is None:
            dest_wells = wells

        if sample_names is None:
            sample_names = np.empty(dna_vols.shape) * np.nan
        if dna_concs is None:
            dna_concs = np.empty(dna_vols.shape) * np.nan
        if dna_concs.shape != sample_names.shape != dna_vols.shape:
            raise ValueError(
                'dna_vols %r has a size different from dna_concs %r or '
                'sample_names' % (dna_vols.shape, dna_concs.shape,
                                  sample_names.shape))

        # header
        picklist = [
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well'
            '\tConcentration\tTransfer Volume\tDestination Plate Name'
            '\tDestination Well']
        # water additions
        for index, sample in np.ndenumerate(sample_names):
            picklist.append('\t'.join(
                [str(sample), water_plate_name, water_plate_type,
                 str(wells[index]), str(dna_concs[index]),
                 str(water_vols[index]), dest_plate_name,
                 str(dest_wells[index])]))
        # DNA additions
        for index, sample in np.ndenumerate(sample_names):
            if dna_plate_names is not None:
                dna_plate_name = dna_plate_names[index]
            picklist.append('\t'.join(
                [str(sample), dna_plate_name, dna_plate_type,
                 str(wells[index]), str(dna_concs[index]),
                 str(dna_vols[index]), dest_plate_name,
                 str(dest_wells[index])]))

        return '\n'.join(picklist)

    def generate_echo_picklist(self):
        """Generates Echo pick list to achieve a normalized input DNA pool

        Returns
        -------
        str
            The echo-formatted pick list
        """
        concentrations = {
            comp: conc
            for comp, conc in self.quantification_process.concentrations}
        dna_vols = []
        water_vols = []
        wells = []
        dest_wells = []
        sample_names = []
        dna_concs = []
        layout = self.plates[0].layout
        for row in layout:
            for well in row:
                composition = well.composition
                dna_vols.append(composition.dna_volume)
                water_vols.append(composition.water_volume)
                # For the source well we need to take a look at the gdna comp
                gdna_comp = composition.gdna_composition
                wells.append(gdna_comp.container.well_id)
                dest_wells.append(well.well_id)
                # For the sample name we need to check the sample composition
                sample_comp = gdna_comp.sample_composition
                sample_names.append(sample_comp.content)
                # For the DNA concentrations we need to look at
                # the quantification process
                dna_concs.append(concentrations[gdna_comp])

        # _format_picklist expects numpy arrays
        dna_vols = np.asarray(dna_vols)
        water_vols = np.asarray(water_vols)
        wells = np.asarray(wells)
        dest_wells = np.asarray(dest_wells)
        sample_names = np.asarray(sample_names)
        dna_concs = np.asarray(dna_concs)

        return NormalizationProcess._format_picklist(
            dna_vols, water_vols, wells, dest_wells=dest_wells,
            sample_names=sample_names, dna_concs=dna_concs)


class LibraryPrepShotgunProcess(Process):
    """Shotgun Library Prep process object

    Attributes
    ----------
    kappa_hyper_plus_kit
    stub_lot
    normalization_process

    See Also
    --------
    Process
    """
    _table = 'qiita.library_prep_shotgun_process'
    _id_column = 'library_prep_shotgun_process_id'
    _process_type = 'shotgun library prep'

    @classmethod
    def create(cls, user, plate, plate_name, kappa_hyper_plus_kit, stub_lot,
               volume, i5_plate, i7_plate):
        """Creats a new LibraryPrepShotgunProcess

        Parameters
        ----------
        user : labman.db.user.User
            User performing the library prep
        plate: labman.db.plate.Plate
            The normalized gDNA plate of origin
        plate_name: str
            The library
        kappa_hyper_plus_kit: labman.db.composition.ReagentComposition
            The Kappa Hyper Plus kit used
        stub_lot: labman.db.composition.ReagentComposition
            The stub lot used
        volume : float
            The initial volume in the wells
        i5_plate: labman.db.plate.Plate
            The i5 primer working plate
        i7_plate: labman.db.plate.Plate
            The i7 primer working plate


        Returns
        -------
        LibraryPrepShotgunProcess
            The newly created process
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the library_prep_shotgun_process
            sql = """INSERT INTO qiita.library_prep_shotgun_process
                        (process_id, kappa_hyper_plus_kit_id, stub_lot_id,
                         normalization_process_id)
                     VALUES (%s, %s, %s, (
                        SELECT DISTINCT normalization_process_id
                            FROM qiita.normalization_process np
                                JOIN qiita.container c
                                    ON np.process_id =
                                        c.latest_upstream_process_id
                                JOIN qiita.well USING (container_id)
                                WHERE plate_id = %s))
                     RETURNING library_prep_shotgun_process_id"""
            TRN.add(sql, [process_id, kappa_hyper_plus_kit.id, stub_lot.id,
                          plate.id])
            instance = cls(TRN.execute_fetchlast())

            # Get the primer set for the plates
            sql = """SELECT DISTINCT shotgun_primer_set_id
                     FROM qiita.shotgun_combo_primer_set cps
                        JOIN qiita.primer_set_composition psc
                            ON cps.i5_primer_set_composition_id =
                                psc.primer_set_composition_id
                        JOIN qiita.primer_composition pc USING
                            (primer_set_composition_id)
                        JOIN qiita.composition c
                            ON pc.composition_id = c.composition_id
                        JOIN qiita.well USING (container_id)
                     WHERE plate_id = %s"""
            TRN.add(sql, [i5_plate.id])
            primer_set = composition_module.ShotgunPrimerSet(
                TRN.execute_fetchlast())

            # Get a list of wells that actually contain information
            wells = [well for well in chain.from_iterable(plate.layout)
                     if well is not None]
            # Get the list of index pairs to use
            idx_combos = primer_set.get_next_combos(len(wells))

            i5_layout = i5_plate.layout
            i7_layout = i7_plate.layout

            # Create the library plate
            lib_plate = plate_module.Plate.create(
                plate_name, plate.plate_configuration)
            for well, idx_combo in zip(wells, idx_combos):
                i5_well = idx_combo[0].container
                i7_well = idx_combo[1].container
                i5_comp = i5_layout[
                    i5_well.row - 1][i5_well.column - 1].composition
                i7_comp = i7_layout[
                    i7_well.row - 1][i7_well.column - 1].composition

                lib_well = container_module.Well.create(
                    lib_plate, instance, volume, well.row, well.column)
                composition_module.LibraryPrepShotgunComposition.create(
                    instance, lib_well, volume, well.composition,
                    i5_comp, i7_comp)

        return instance

    @property
    def kappa_hyper_plus_kit(self):
        """The Kappa Hyper plus kit used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('kappa_hyper_plus_kit_id'))

    @property
    def stub_lot(self):
        """The stub lot used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('stub_lot_id'))

    @property
    def normalization_process(self):
        """The normalization process used

        Returns
        -------
        NormalizationProcess
        """
        return NormalizationProcess(self._get_attr('normalization_process_id'))

    @staticmethod
    def _format_picklist(sample_names, sample_wells, indices, i5_vol=250,
                         i7_vol=250, i5_plate_type='384LDV_AQ_B2_HT',
                         i7_plate_type='384LDV_AQ_B2_HT',
                         dest_plate_name='IndexPCRPlate'):
        """Formats Echo-format pick list for preparing the shotgun library

        Parameters
        ----------
        sample_names:  array-like of str
            The sample names matching index order of indices
        sample_wells:  array-like of str
            The wells matching sample name order
        indices: pandas DataFrame
            The dataframe with index info matching sample_names
        i5_vol: int, optional
            The volume of i5 index to transfer. Default: 250
        i7_vol: int, optional
            The volume of i7 index to transfer. Default: 250
        i5_plate_type: str, optional
            The i5 plate type. Default: 384LDV_AQ_B2_HT
        i7_plate_type: str, optional
            The i7 plate type. Default: 384LDV_AQ_B2_HT
        dest_plate_name: str, optional
            The name of the destination plate. Default: IndexPCRPlate

        Returns
        -------
        str
            The Echo formatted pick list
        """
        # check that arrays are the right size
        if len(sample_names) != len(sample_wells) != len(indices):
            raise ValueError(
                'sample_names (%s) has a size different from sample_wells '
                '(%s) or index list (%s)'
                % (len(sample_names), len(sample_wells), len(indices)))

        # header
        picklist = [
            'Sample\tSource Plate Name\tSource Plate Type\tSource Well\t'
            'Transfer Volume\tIndex Name\tIndex Sequence\t'
            'Destination Plate Name\tDestination Well']

        # i5 additions
        for i, (sample, well) in enumerate(zip(sample_names, sample_wells)):
            picklist.append('\t'.join([
                str(sample), indices.iloc[i]['i5 plate'], i5_plate_type,
                indices.iloc[i]['i5 well'], str(i5_vol),
                indices.iloc[i]['i5 name'], indices.iloc[i]['i5 sequence'],
                dest_plate_name, well]))
        # i7 additions
        for i, (sample, well) in enumerate(zip(sample_names, sample_wells)):
            picklist.append('\t'.join([
                str(sample), indices.iloc[i]['i7 plate'], i7_plate_type,
                indices.iloc[i]['i7 well'], str(i7_vol),
                indices.iloc[i]['i7 name'], indices.iloc[i]['i7 sequence'],
                dest_plate_name, well]))

        return '\n'.join(picklist)

    def genereate_echo_picklist(self):
        """Generates Echo pick list for preparing the shotgun library

        Returns
        -------
        str
            The echo-formatted pick list
        """
        sample_names = []
        sample_wells = []
        indices = {'i5 name': {}, 'i5 plate': {}, 'i5 sequence': {},
                   'i5 well': {}, 'i7 name': {}, 'i7 plate': {},
                   'i7 sequence': {}, 'i7 well': {}, 'index combo': {},
                   'index combo seq': {}}

        for idx, well in enumerate(chain.from_iterable(self.plates[0].layout)):
            # Add the sample well
            sample_wells.append(well.well_id)
            # Get the sample name - we need to go back to the SampleComposition
            lib_comp = well.composition
            sample_comp = lib_comp.normalized_gdna_composition\
                .gdna_composition.sample_composition
            sample_names.append(sample_comp.content)
            # Retrieve all the information about the indices
            i5_comp = lib_comp.i5_composition.primer_set_composition
            i5_well = i5_comp.container
            indices['i5 name'][idx] = i5_comp.external_id
            indices['i5 plate'][idx] = i5_well.plate.external_id
            indices['i5 sequence'][idx] = i5_comp.barcode
            indices['i5 well'][idx] = i5_well.well_id

            i7_comp = lib_comp.i7_composition.primer_set_composition
            i7_well = i7_comp.container
            indices['i7 name'][idx] = i7_comp.external_id
            indices['i7 plate'][idx] = i7_well.plate.external_id
            indices['i7 sequence'][idx] = i7_comp.barcode
            indices['i7 well'][idx] = i7_well.well_id

            indices['index combo seq'][idx] = '%s%s' % (
                indices['i5 sequence'][idx], indices['i7 sequence'][idx])

        sample_names = np.asarray(sample_names)
        sample_wells = np.asarray(sample_wells)
        indices = pd.DataFrame(indices)

        return LibraryPrepShotgunProcess._format_picklist(
            sample_names, sample_wells, indices)


class QuantificationProcess(Process):
    """Quantification process object

    Attributes
    ----------
    concentrations

    See Also
    --------
    Process
    """
    _table = 'qiita.quantification_process'
    _id_column = 'quantification_process_id'
    _process_type = 'quantification'

    @staticmethod
    def _compute_pico_concentration(dna_vals, size=500):
        """Computes molar concentration of libraries from library DNA
        concentration values.

        Parameters
        ----------
        dna_vals : numpy array of float
            The DNA concentration in ng/uL
        size : int
            The average library molecule size in bp

        Returns
        -------
        np.array of floats
            Array of calculated concentrations, in nanomolar units
        """
        lib_concentration = (dna_vals / (660 * float(size))) * 10**6

        return lib_concentration

    @staticmethod
    def _make_2D_array(df, data_col='Sample DNA Concentration',
                       well_col='Well', rows=8, cols=12):
        """Pulls a column of data out of a dataframe and puts into array format
        based on well IDs in another column

        Parameters
        ----------
        df: Pandas DataFrame
            dataframe from which to pull values
        data_col: str, optional
            name of column with data. Default: Sample DNA Concentration
        well_col: str, optional
            name of column with well IDs, in 'A1,B12' format. Default: Well
        rows: int, optional
            number of rows in array to return. Default: 8
        cols: int, optional
            number of cols in array to return. Default: 12

        Returns
        -------
        numpy 2D array
        """
        # initialize empty Cp array
        cp_array = np.empty((rows, cols), dtype=object)

        # fill Cp array with the post-cleaned values from the right half of the
        # plate
        for record in df.iterrows():
            row = ord(str.upper(record[1][well_col][0])) - ord('A')
            col = int(record[1][well_col][1:]) - 1
            cp_array[row, col] = record[1][data_col]

        return cp_array

    @staticmethod
    def _parse_pico_csv(contents, sep='\t',
                        conc_col_name='Sample DNA Concentration'):
        """Reads tab-delimited pico quant

        Parameters
        ----------
        contents: fp or open filehandle
            pico quant file
        sep: str
            sep char used in quant file
        conc_col_name: str
            name to use for concentration column output

        Returns
        -------
        pico_df: pandas DataFrame object
            DataFrame relating well location and DNA concentration
        """
        raw_df = pd.read_csv(contents, sep=sep, skiprows=2, skipfooter=5,
                             engine='python')

        pico_df = raw_df[['Well', '[Concentration]']]
        pico_df = pico_df.rename(columns={'[Concentration]': conc_col_name})

        # coerce oddball concentrations to np.nan
        pico_df[conc_col_name] = pd.to_numeric(pico_df[conc_col_name],
                                               errors='coerce')

        return pico_df

    @staticmethod
    def parse(contents, file_format="minipico", rows=8, cols=12):
        """Parses the quantification output

        Parameters
        ----------
        contents : str
            The contents of the plate reader output
        file_format: str
            The quantification file format
        rows: int, optional
            The number of rows in the plate. Default: 8
        cols: int, optional
            The number of cols in the plate. Default: 12

        Returns
        -------
        DataFrame
        """
        parsers = {'minipico': QuantificationProcess._parse_pico_csv}
        contents_io = StringIO(contents)

        if file_format not in parsers:
            raise ValueError(
                'File format %s not recognized. Supported file formats: %s'
                % (file_format, ', '.join(parsers)))
        df = parsers[file_format](contents_io)
        array = QuantificationProcess._make_2D_array(df, rows=rows, cols=cols)
        return array.astype(float)

    @classmethod
    def create_manual(cls, user, quantifications):
        """Creates a new manual quantification process

        Parameters
        ----------
        user: labman.db.user.User
            User performing the quantification process
        quantifications: list of dict
            The quantifications in the form of {'composition': Composition,
            'conenctration': float}

        Returns
        -------
        QuantificationProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the quantification process table
            sql = """INSERT INTO qiita.quantification_process (process_id)
                     VALUES (%s) RETURNING quantification_process_id"""
            TRN.add(sql, [process_id])
            instance = cls(TRN.execute_fetchlast())

            sql = """INSERT INTO qiita.concentration_calculation
                        (quantitated_composition_id, upstream_process_id,
                         raw_concentration)
                     VALUES (%s, %s, %s)"""
            sql_args = []
            for quant in quantifications:
                sql_args.append([quant['composition'].composition_id,
                                 instance.id, quant['concentration']])

            TRN.add(sql, sql_args, many=True)
            TRN.execute()
        return instance

    @classmethod
    def create(cls, user, plate, concentrations, compute_concentrations=False,
               size=500):
        """Creates a new quantification process

        Parameters
        ----------
        user: labman.db.user.User
            User performing the quantification process
        plate: labman.db.plate.Plate
            The plate being quantified
        concentrations: 2D np.array
            The plate concentrations
        compute_concentrations: boolean, optional
            If true, compute library concentration
        size: int, optional
            If compute_concentrations is True, the average library molecule
            size, in bp.

        Returns
        -------
        QuantificationProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the quantification process table
            sql = """INSERT INTO qiita.quantification_process (process_id)
                     VALUES (%s) RETURNING quantification_process_id"""
            TRN.add(sql, [process_id])
            instance = cls(TRN.execute_fetchlast())

            sql = """INSERT INTO qiita.concentration_calculation
                        (quantitated_composition_id, upstream_process_id,
                         raw_concentration, computed_concentration)
                     VALUES (%s, %s, %s, %s)"""
            sql_args = []
            layout = plate.layout

            if compute_concentrations:
                comp_conc = QuantificationProcess._compute_pico_concentration(
                    concentrations, size)
            else:
                pc = plate.plate_configuration
                comp_conc = [[None] * pc.num_columns] * pc.num_rows

            for p_row, c_row, cc_row in zip(layout, concentrations, comp_conc):
                for well, conc, c_conc in zip(p_row, c_row, cc_row):
                    sql_args.append([well.composition.composition_id,
                                     instance.id, conc, c_conc])

            TRN.add(sql, sql_args, many=True)
            TRN.execute()

            return instance

    @property
    def concentrations(self):
        """The concentrations measured

        Returns
        -------
        list of (Composition, float, float)
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT quantitated_composition_id, raw_concentration,
                            computed_concentration
                     FROM qiita.concentration_calculation
                     WHERE upstream_process_id = %s
                     ORDER BY concentration_calculation_id"""
            TRN.add(sql, [self._id])
            return [
                (composition_module.Composition.factory(comp_id), r_con, c_con)
                for comp_id, r_con, c_con in TRN.execute_fetchindex()]


class PoolingProcess(Process):
    """Pooling process object

    Attributes
    ----------
    quantification_process
    robot

    See Also
    --------
    Process
    """
    _table = 'qiita.pooling_process'
    _id_column = 'pooling_process_id'
    _process_type = 'pooling'

    @staticmethod
    def _compute_shotgun_pooling_values_eqvol(sample_concs, total_vol=60.0):
        """Computes molar concentration of libraries from concentration values,
        using an even volume per sample

        Parameters
        ----------
        sample_concs : numpy array of float
            The concentrations calculated via qPCR (nM)
        total_vol : float, optional
            The total volume to pool (uL). Default: 60

        Returns
        -------
        np.array of floats
            A 2D array of floats
        """
        per_sample_vol = (total_vol / sample_concs.size) * 1000.0
        sample_vols = np.zeros(sample_concs.shape) + per_sample_vol
        return sample_vols

    @staticmethod
    def _compute_shotgun_pooling_values_minvol(
            sample_concs, sample_fracs=None, floor_vol=100, floor_conc=40,
            total_nmol=.01):
        """Computes pooling volumes for samples based on concentration
        estimates of nM concentrations (`sample_concs`), taking a minimum
        volume of samples below a threshold.

        Reads in concentration values in nM. Samples below a minimum
        concentration (`floor_conc`, default 40 nM) will be included, but at a
        decreased volume (`floor_vol`, default 100 nL) to avoid overdiluting
        the pool.

        Samples can be assigned a target molar fraction in the pool by passing
        a np.array (`sample_fracs`, same shape as `sample_concs`) with
        fractional values per sample. By default, will aim for equal molar
        pooling.

        Finally, total pooling size is determined by a target nanomolar
        quantity (`total_nmol`, default .01). For a perfect 384 sample library,
        in which you had all samples at a concentration of exactly 400 nM and
        wanted a total volume of 60 uL, this would be 0.024 nmol.

        For a Novaseq, we expect to need 150 uL at 4 nM, or about 0.0006 nmol.
        Taking into account sample loss on the pippin prep (1/2) and molar loss
        due to exclusion of primer dimers (1/2), figure we need 4 times that or
        0.0024.

        Parameters
        ----------
        sample_concs: 2D array of float
            nM sample concentrations
        sample_fracs: 2D of float, optional
            fractional value for each sample (default 1/N)
        floor_vol: float, optional
            volume (nL) at which samples below floor_conc will be pooled.
            Default: 100
        floor_conc: float, optional
            minimum value (nM) for pooling at real estimated value. Default: 40
        total_nmol : float, optional
            total number of nM to have in pool. Default: 0.01

        Returns
        -------
        sample_vols: np.array of floats
            the volumes in nL per each sample pooled
        """
        if sample_fracs is None:
            sample_fracs = np.ones(sample_concs.shape) / sample_concs.size

        # calculate volumetric fractions including floor val
        sample_vols = (total_nmol * sample_fracs) / sample_concs
        # convert L to nL
        sample_vols *= 10**9
        # drop volumes for samples below floor concentration to floor_vol
        sample_vols[sample_concs < floor_conc] = floor_vol
        return sample_vols

    @staticmethod
    def _compute_shotgun_pooling_values_floor(
            sample_concs, sample_fracs=None, min_conc=10, floor_conc=50,
            total_nmol=.01):
        """Computes pooling volumes for samples based on concentration
        estimates of nM concentrations (`sample_concs`).

        Reads in concentration values in nM. Samples must be above a minimum
        concentration threshold (`min_conc`, default 10 nM) to be included.
        Samples above this threshold but below a given floor concentration
        (`floor_conc`, default 50 nM) will be pooled as if they were at the
        floor concentration, to avoid overdiluting the pool.

        Samples can be assigned a target molar fraction in the pool by passing
        a np.array (`sample_fracs`, same shape as `sample_concs`) with
        fractional values per sample. By default, will aim for equal molar
        pooling.

        Finally, total pooling size is determined by a target nanomolar
        quantity (`total_nmol`, default .01). For a perfect 384 sample library,
        in which you had all samples at a concentration of exactly 400 nM and
        wanted a total volume of 60 uL, this would be 0.024 nmol.

        Parameters
        ----------
        sample_concs: 2D array of float
            nM calculated by compute_qpcr_concentration
        sample_fracs: 2D of float, optional
            fractional value for each sample (default 1/N)
        min_conc: float, optional
            minimum nM concentration to be included in pool. Default: 10
        floor_conc: float, optional
            minimum value for pooling for samples above min_conc. Default: 50
            corresponds to a maximum vol in pool
        total_nmol : float, optional
            total number of nM to have in pool. Default 0.01

        Returns
        -------
        sample_vols: np.array of floats
            the volumes in nL per each sample pooled
        """
        if sample_fracs is None:
            sample_fracs = np.ones(sample_concs.shape) / sample_concs.size

        # get samples above threshold
        sample_fracs_pass = sample_fracs.copy()
        sample_fracs_pass[sample_concs <= min_conc] = 0
        # renormalize to exclude lost samples
        sample_fracs_pass *= 1/sample_fracs_pass.sum()
        # floor concentration value
        sample_concs_floor = sample_concs.copy()
        sample_concs_floor[sample_concs < floor_conc] = floor_conc
        # calculate volumetric fractions including floor val
        sample_vols = (total_nmol * sample_fracs_pass) / sample_concs_floor
        # convert L to nL
        sample_vols *= 10**9
        return sample_vols

    @classmethod
    def create(cls, user, quantification_process, pool_name, volume,
               input_compositions, robot=None):
        """Creates a new pooling process

        Parameters
        ----------
        user: labman.db.user.User
            User performing the pooling process
        quantification_process: labman.db.process.QuantificationProcess
            The quantification process this pooling is based on
        pool_name: str
            The name of the new pool
        volume: float
            The initial volume
        input_compositions: list of dicts
            The input compositions for the pool {'composition': Composition,
            'input_volume': float, 'percentage_of_output': float}
        robot: labman.equipment.Equipment, optional
            The robot performing the pooling, if not manual

        Returns
        -------
        PoolingProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the pooling process table
            sql = """INSERT INTO qiita.pooling_process
                        (process_id, quantification_process_id, robot_id)
                     VALUES (%s, %s, %s)
                     RETURNING pooling_process_id"""
            r_id = robot.id if robot is not None else None
            TRN.add(sql, [process_id, quantification_process.id, r_id])
            instance = cls(TRN.execute_fetchlast())

            # Create the new pool
            tube = container_module.Tube.create(instance, pool_name, volume)
            pool = composition_module.PoolComposition.create(
                instance, tube, volume)

            # Link the pool with its contents
            sql = """INSERT INTO qiita.pool_composition_components
                        (output_pool_composition_id, input_composition_id,
                         input_volume, percentage_of_output)
                     VALUES (%s, %s, %s, %s)"""
            sql_args = []
            for in_comp in input_compositions:
                sql_args.append([pool.id,
                                 in_comp['composition'].composition_id,
                                 in_comp['input_volume'],
                                 in_comp['percentage_of_output']])
            TRN.add(sql, sql_args, many=True)
            TRN.execute()

        return instance

    @property
    def quantification_process(self):
        """The quantification process used

        Returns
        -------
        QuantificationProcess
        """
        return QuantificationProcess(
            self._get_attr('quantification_process_id'))

    @property
    def robot(self):
        """The robot used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(self._get_attr('robot_id'))

    @property
    def components(self):
        """The components of the pool

        Returns
        -------
        list of (Composition, float)
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT input_composition_id, input_volume
                     FROM qiita.pool_composition_components
                        JOIN qiita.pool_composition
                            ON output_pool_composition_id = pool_composition_id
                        JOIN qiita.composition USING (composition_id)
                     WHERE upstream_process_id = %s
                     ORDER BY pool_composition_components_id"""
            TRN.add(sql, [self.process_id])
            return [(composition_module.Composition.factory(comp_id), vol)
                    for comp_id, vol in TRN.execute_fetchindex()]

    @staticmethod
    def _format_picklist(vol_sample, max_vol_per_well=60000,
                         dest_plate_shape=None):
        """Format the contents of an echo pooling pick list

        Parameters
        ----------
        vol_sample : 2d numpy array of floats
            The per well sample volume, in nL
        max_vol_per_well : floats, optional
            Maximum destination well volume, in nL. Default: 60000
        dest_plate_shape: list of 2 elements
            The destination plate shape
        """
        if dest_plate_shape is None:
            dest_plate_shape = [16, 24]

        contents = ['Source Plate Name,Source Plate Type,Source Well,'
                    'Concentration,Transfer Volume,Destination Plate Name,'
                    'Destination Well']
        # Write the sample transfer volumes
        rows, cols = vol_sample.shape
        # replace NaN values with 0s to leave a trail of unpooled wells
        pool_vols = np.nan_to_num(vol_sample)
        running_tot = 0
        d = 1
        for i in range(rows):
            for j in range(cols):
                well_name = "%s%d" % (chr(ord('A') + i), j+1)
                # Machine will round, so just give it enough info to do the
                # correct rounding.
                val = "%.2f" % pool_vols[i][j]
                # test to see if we will exceed total vol per well
                if running_tot + pool_vols[i][j] > max_vol_per_well:
                    d += 1
                    running_tot = pool_vols[i][j]
                else:
                    running_tot += pool_vols[i][j]
                dest = "%s%d" % (chr(ord('A') +
                                 int(np.floor(d/dest_plate_shape[0]))),
                                 (d % dest_plate_shape[1]))
                contents.append(",".join(['1', '384LDV_AQ_B2_HT', well_name,
                                          "", val, 'NormalizedDNA', dest]))

        return "\n".join(contents)

    def generate_echo_picklist(self, max_vol_per_well=30000):
        """Generates Echo pick list for pooling the shotgun library

        Parameters
        ----------
        max_vol_per_well : floats, optional
            Maximum destination well volume, in nL. Default: 30000

        Returns
        -------
        str
            The echo-formatted pick list
        """
        vol_sample = np.zeros((16, 24))
        for comp, vol in self.components:
            well = comp.container
            vol_sample[well.row - 1][well.column - 1] = vol
        return PoolingProcess._format_picklist(vol_sample)


class SequencingProcess(Process):
    """Sequencing process object

    Attributes
    ----------

    See Also
    --------
    Process
    """
    _table = 'qiita.sequencing_process'
    _id_column = 'sequencing_process_id'
    _process_type = 'sequencing'

    @classmethod
    def create(cls, user, pool, run_name, sequencer, fwd_cycles, rev_cycles,
               assay, principal_investigator, contact_0, contact_1=None,
               contact_2=None):
        """Creates a new sequencing process

        Parameters
        ----------
        user : labman.db.user.User
            User preparing the sequencing
        pool: labman.db.composition.PoolComposition
            The pool being sequenced
        run_name: str
            The run name
        sequencer: labman.db.equipment.Equipment
            The sequencer used
        fwd_cycles : int
            The number of forward cycles
        rev_cycles : int
            The number of reverse cycles
        assay : str
            The assay instrument (e.g., Kapa Hyper Plus)
        principal_investigator : labman.db.user.User
            The principal investigator to list in the run
        contact_0 : labman.db.user.User
            Additional contact person
        contact_1 : labman.db.user.User, optional
            Additional contact person
        contact_2 : labman.db.user.User, optional
            Additional contact person

        Returns
        -------
        SequencingProcess

        Raises
        ------
        ValueError
            If the number of cycles are <= 0
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            if fwd_cycles <= 0 or not isinstance(fwd_cycles, int):
                raise ValueError("fwd_cycles must be > 0")
            if rev_cycles <= 0 or not isinstance(rev_cycles, int):
                raise ValueError("rev_cycles must be > 0")

            # Add the row to the sequencing table
            sql = """INSERT INTO qiita.sequencing_process
                        (process_id, pool_composition_id, sequencer_id,
                         fwd_cycles, rev_cycles, assay, principal_investigator,
                         contact_0, contact_1, contact_2, run_name)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                     RETURNING sequencing_process_id"""
            c1_id = contact_1.id if contact_1 is not None else None
            c2_id = contact_2.id if contact_2 is not None else None
            TRN.add(sql, [process_id, pool.id, sequencer.id, fwd_cycles,
                          rev_cycles, assay, principal_investigator.id,
                          contact_0.id, c1_id, c2_id, run_name])
            instance = cls(TRN.execute_fetchlast())
        return instance

    @property
    def run_name(self):
        return self._get_attr('run_name')

    @property
    def pool(self):
        return composition_module.PoolComposition(
            self._get_attr('pool_composition_id'))

    @property
    def sequencer(self):
        return equipment_module.Equipment(self._get_attr('sequencer_id'))

    @property
    def fwd_cycles(self):
        return self._get_attr('fwd_cycles')

    @property
    def rev_cycles(self):
        return self._get_attr('rev_cycles')

    @property
    def assay(self):
        return self._get_attr('assay')

    @property
    def principal_investigator(self):
        return user_module.User(self._get_attr('principal_investigator'))

    @property
    def contact_0(self):
        return user_module.User(self._get_attr('contact_0'))

    @property
    def contact_1(self):
        return user_module.User(self._get_attr('contact_1'))

    @property
    def contact_2(self):
        return user_module.User(self._get_attr('contact_2'))

    def format_sample_sheet(self, run_type='Target Gene'):
        """Writes a sample sheet

        Parameters
        ----------
        run_type : {"Target Gene", "Shotgun"}
            Which data sheet structure to use

        Sample Sheet Note
        -----------------
        If the instrument type is a MiSeq, any lane information per-sample will
        be disregarded. If instrument type is a HiSeq, each sample must include
        a "lane" key.
        If the run type is Target Gene, then sample details are disregarded
        with the exception of determining the lanes.
        IF the run type is shotgun, then the following keys are required:
            - sample-id
            - i7-index-id
            - i7-index
            - i5-index-id
            - i5-index

        Raises
        ------
        ValueError
            If an unknown run type is specified

        Return
        ------
        str
            The formatted sheet.
        """
        run_type = 'Target Gene'
        if run_type == 'Target Gene':
            sample_header = DATA_TARGET_GENE_STRUCTURE
            sample_detail = DATA_TARGET_GENE_SAMPLE_STRUCTURE
        elif run_type == 'Shotgun':
            sample_header = DATA_SHOTGUN_STRUCTURE
            sample_detail = DATA_SHOTGUN_SAMPLE_STRUCTURE
        else:
            raise ValueError("%s is not a known run type" %
                             run_type)

        # if its a miseq, there isn't lane information
        instrument_type = self.sequencer.equipment_type
        if instrument_type == 'miseq':
            header_prefix = ''
            header_suffix = ','
            sample_prefix = ''
            sample_suffix = ','
        elif instrument_type == 'hiseq':
            header_prefix = 'Lane,'
            header_suffix = ''
            sample_prefix = '%(lane)d,'
            sample_suffix = ''

        sample_header = header_prefix + sample_header + header_suffix
        sample_detail_fmt = sample_prefix + sample_detail + sample_suffix

        if run_type == 'Target Gene':
            if instrument_type == 'hiseq':
                pass
                # TODO: how to gather the lane information? is it a lane per
                # pool?
                # lanes = sorted({samp['lane'] for samp in sample_information})
                # sample_details = []
                # for idx, lane in enumerate(lanes):
                #     # make a unique run-name on the assumption
                #     this is required
                #     detail = {'lane': lane, 'run_name': run_name + str(idx)}
                #     sample_details.append(sample_detail_fmt % detail)
            else:
                sample_details = [sample_detail_fmt % {
                    'run_name': self.run_name}]
        else:
            pass
            # TODO: gather the information for shotgun
            # sample_details = [sample_detail_fmt % samp
            #                   for samp in sample_information]

        base_sheet = self._format_general()

        full_sheet = "%s%s\n%s\n" % (base_sheet, sample_header,
                                     '\n'.join(sample_details))

        return full_sheet

    def _format_general(self):
        """Format the initial parts of a sample sheet

        Returns
        -------
        str
            The populated non-sample parts of the sample sheet.
        """
        pi = self.principal_investigator
        c0 = self.contact_0
        fmt = {'run_name': self.run_name,
               'assay': self.assay,
               'date': datetime.now().strftime("%m/%d/%Y"),
               'fwd_cycles': self.fwd_cycles,
               'rev_cycles': self.rev_cycles,
               'labman_id': self.id,
               'pi_name': pi.name,
               'pi_email': pi.email,
               'contact_0_name': c0.name,
               'contact_0_email': c0.email}

        c1 = self.contact_1
        c2 = self.contact_2
        optional = {
            'contact_1_name': c1.name if c1 is not None else None,
            'contact_1_email': c1.email if c1 is not None else None,
            'contact_2_name': c2.name if c2 is not None else None,
            'contact_2_email': c2.email if c2 is not None else None}

        for k, v in fmt.items():
            if v is None or v == '':
                raise ValueError("%s is required")
        fmt.update(optional)

        return SHEET_STRUCTURE % fmt


SHEET_STRUCTURE = """[Header],,,,,,,,,,
IEMFileVersion,4,,,,,,,,,
Investigator Name,%(pi_name)s,,,,PI,%(pi_name)s,%(pi_email)s,,,
Experiment Name,%(run_name)s,,,,Contact,%(contact_0_name)s,%(contact_1_name)s,%(contact_2_name)s,,
Date,%(date)s,,,,,%(contact_0_email)s,%(contact_1_email)s,%(contact_2_email)s,,
Workflow,GenerateFASTQ,,,,,,,,,
Application,FASTQ Only,,,,,,,,,
Assay,%(assay)s,,,,,,,,,
Description,labman ID,%(labman_id)d,,,,,,,,
Chemistry,Default,,,,,,,,,
,,,,,,,,,,
[Reads],,,,,,,,,,
%(fwd_cycles)d,,,,,,,,,,
%(rev_cycles)d,,,,,,,,,,
,,,,,,,,,,
[Settings],,,,,,,,,,
ReverseComplement,0,,,,,,,,,
,,,,,,,,,,
[Data],,,,,,,,,,
"""  # noqa: E501

DATA_TARGET_GENE_STRUCTURE = "Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description,,"  # noqa: E501

DATA_TARGET_GENE_SAMPLE_STRUCTURE = "%(run_name)s,,,,,NNNNNNNNNNNN,,,,,"

DATA_SHOTGUN_STRUCTURE = "Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description"  # noqa: E501

DATA_SHOTGUN_SAMPLE_STRUCTURE = "%(sample_id)s,,,,%(i7_index_id)s,%(i7_index)s,%(i5_index_id)s,%(i5_index)s,,"  # noqa: E501
