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
from . import user
from . import plate as plate_mod
from . import container
from . import composition
from . import equipment


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
            'gDNA extraction': GDNAExtractionProcess,
            '16S library prep': LibraryPrep16SProcess,
            'shotgun library prep': LibraryPrepShotgunProcess,
            'pico green quantification': QuantificationProcess,
            'qpcr_quantification': QuantificationProcess,
            'gDNA normalization': NormalizationProcess,
            'manual pooling': PoolingProcess,
            'automated pooling': PoolingProcess}

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
                        JOIN {} USING process_id
                     WHERE {} = %s""".format(attr, self._table,
                                             self._id_column)
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def date(self):
        return self._get_process_attr('run_date')

    @property
    def personnel(self):
        return self._get_process_attr('run_personnel_id')

    @property
    def process_id(self):
        return self._get_process_attr('process_id')


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

    @property
    def date(self):
        return self._get_attr('run_date')

    @property
    def personnel(self):
        return user.User(self._get_attr('run_personnel_id'))

    @property
    def process_id(self):
        return self._get_attr('process_id')


class SamplePlatingProcess(_Process):
    """Sample plating process"""

    _process_type = 'sample plating'

    @classmethod
    def create(cls, user, plate_config, plate_ext_id, volume):
        """Creates a new sample plating process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the plating
        plate_config : labman.db.PlateConfiguration
            The sample plate configuration
        plate_ext_id : str
            The external plate id
        volume : float
            Starting well volume

        Returns
        -------
        SamplePlatingProcess
        """
        with sql_connection.TRN:
            # Add the row to the process table
            instance = cls(cls._common_creation_steps(user))

            # Create the plate
            plate = plate_mod.Plate.create(plate_ext_id, plate_config)

            # By definition, all well plates are blank at the beginning
            # so populate all the wells in the plate with BLANKS
            for i in range(plate_config.num_rows):
                for j in range(plate_config.num_columns):
                    well = container.Well.create(
                        plate, instance, volume, i + 1, j + 1)
                    composition.SampleComposition.create(
                        instance, well, volume, control='blank')

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
        return plate_mod.Plate(plate_id)


class PrimerWorkingPlateCreationProcess(Process):
    """Primer working plate creation process object

    Attributes
    ----------
    primer_set
    master_set_order_number
    """
    _table = 'qiita.primer_working_plate_creation_process'
    _id_column = 'primer_working_plate_creation_process_id'

    @property
    def primer_set(self):
        """The primer set template from which the working plates are created

        Returns
        -------
        PrimerSet
        """
        return composition.PrimerSet(self._get_attr('primer_set_id'))

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

    @property
    def robot(self):
        """The robot used during extraction

        Returns
        -------
        Equipment
        """
        return equipment.Equipment(self._get_attr('extraction_robot_id'))

    @property
    def kit(self):
        """The kit used during extraction

        Returns
        -------
        ReagentComposition
        """
        return composition.ReagentComposition(
            self._get_attr('extraction_kit_id'))

    @property
    def tool(self):
        """The tool used during extraction

        Returns
        -------
        Equipment
        """
        return equipment.Equipment(self._get_attr('extraction_tool_id'))


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

    @property
    def master_mix(self):
        """The master mix used

        Returns
        -------
        ReagentComposition
        """
        return composition.ReagentComposition(self._get_attr('master_mix_id'))

    @property
    def tm300_8_tool(self):
        """The tm300_8 tool used

        Returns
        -------
        Equipment
        """
        return equipment.Equipment(self._get_attr('tm300_8_tool_id'))

    @property
    def tm50_8_tool(self):
        """The tm50_8 tool used

        Returns
        -------
        Equipment
        """
        return equipment.Equipment(self._get_attr('tm50_8_tool_id'))

    @property
    def water_lot(self):
        """The water lot used

        Returns
        -------
        ReagentComposition
        """
        return composition.ReagentComposition(self._get_attr('water_id'))

    @property
    def processing_robot(self):
        """The processing robot used

        Returns
        -------
        Equipment
        """
        return equipment.Equipment(self._get_attr('processing_robot_id'))


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
        return composition.ReagentComposition(self._get_attr('water_lot_id'))


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

    @property
    def kappa_hyper_plus_kit(self):
        """The Kappa Hyper plus kit used

        Returns
        -------
        ReagentComposition
        """
        return composition.ReagentComposition(
            self._get_attr('kappa_hyper_plus_kit_id'))

    @property
    def stub_lot(self):
        """The stub lot used

        Returns
        -------
        ReagentComposition
        """
        return composition.ReagentComposition(self._get_attr('stub_lot_id'))

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
        return equipment.Equipment(self._get_attr('robot_id'))
