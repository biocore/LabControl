# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import date

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
            'pico green quantification': QuantificationProcess,
            'qpcr_quantification': QuantificationProcess,
            'gDNA normalization': NormalizationProcess,
            'pooling': PoolingProcess}

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
                     WHERE latest_upstream_process_id = %s"""
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
    def water_lot(self):
        """The water lot used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('water_lot_id'))


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

    @property
    def concentrations(self):
        """The concentrations measured

        Returns
        -------
        list of (Composition, float)
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT quantitated_composition_id, raw_concentration
                     FROM qiita.concentration_calculation
                     WHERE upstream_process_id = %s
                     ORDER BY concentration_calculation_id"""
            TRN.add(sql, [self._id])
            # TODO: return the Composition object rather than the ID
            return [(comp_id, raw_con)
                    for comp_id, raw_con in TRN.execute_fetchindex()]


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
