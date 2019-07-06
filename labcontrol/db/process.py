# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from collections import namedtuple
from datetime import datetime
from io import StringIO
from itertools import chain
from random import randrange
import re
from json import dumps
import numpy as np
import pandas as pd

from . import base
from . import sql_connection
from . import user as user_module
from . import plate as plate_module
from . import container as container_module
from . import composition as composition_module
from . import equipment as equipment_module


def _format_name_for_picklist(comp):
    "Helper function to avoid including redundant information"
    content, specimen_id = comp.content, comp.specimen_id
    if content != specimen_id:
        name = '%s (%s)' % (content, specimen_id)
    else:
        name = '%s' % content
    return name


class Process(base.LabControlObject):
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
            'primer working plate creation': PrimerWorkingPlateCreationProcess,
            'sample plating': SamplePlatingProcess,
            'reagent creation': ReagentCreationProcess,
            'gDNA extraction': GDNAExtractionProcess,
            '16S library prep': LibraryPrep16SProcess,
            'shotgun library prep': LibraryPrepShotgunProcess,
            'quantification': QuantificationProcess,
            'gDNA normalization': NormalizationProcess,
            'compressed gDNA plates': GDNAPlateCompressionProcess,
            'pooling': PoolingProcess,
            'sequencing': SequencingProcess}

        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM labcontrol.process_type
                        JOIN labcontrol.process USING (process_type_id)
                     WHERE process_id = %s"""
            TRN.add(sql, [process_id])
            p_type = TRN.execute_fetchlast()
            constructor = factory_classes[p_type]

            if constructor._table == 'labcontrol.process':
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

    @staticmethod
    def get_date_format():
        return '%Y-%m-%d %H:%M'

    @staticmethod
    def get_filename_date_format():
        return '%Y-%m-%d'

    @classmethod
    def _common_creation_steps(cls, user, process_date=None, notes=None):
        if process_date is None:
            process_date = datetime.now()

        with sql_connection.TRN as TRN:
            sql = """SELECT process_type_id
                     FROM labcontrol.process_type
                     WHERE description = %s"""
            TRN.add(sql, [cls._process_type])
            pt_id = TRN.execute_fetchlast()

            sql = """INSERT INTO labcontrol.process
                        (process_type_id, run_date, run_personnel_id, notes)
                     VALUES (%s, %s, %s, %s)
                     RETURNING process_id"""
            TRN.add(sql, [pt_id, process_date, user.id, notes])
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
                     FROM labcontrol.process
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
    def notes(self):
        return self._get_process_attr('notes')

    @property
    def process_id(self):
        return self._get_process_attr('process_id')

    @property
    def plates(self):
        """The plates being extracted by this process

        Returns
        -------
        plate : list of labcontrol.db.Plate
            The extracted plates
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.container
                        LEFT JOIN labcontrol.well USING (container_id)
                     WHERE latest_upstream_process_id = %s
                     ORDER BY plate_id"""
            TRN.add(sql, [self.process_id])
            plate_ids = TRN.execute_fetchflatten()
        return [plate_module.Plate(plate_id) for plate_id in plate_ids]


class _Process(Process):
    """Process object

    Not all processes have a specific subtable, so we need to override the
    date, personnel, and notes attributes

    Attributes
    ----------
    id
    date
    personnel
    notes
    """
    _table = 'labcontrol.process'
    _id_column = 'process_id'

    @property
    def date(self):
        return self._get_attr('run_date')

    @property
    def personnel(self):
        return user_module.User(self._get_attr('run_personnel_id'))

    @property
    def notes(self):
        return self._get_attr('notes')

    @notes.setter
    def notes(self, value):
        """Updates the notes of the process"""
        self._set_attr('notes', value)

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
        user : labcontrol.db.user.User
            User performing the plating
        plate_config : labcontrol.db.PlateConfiguration
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
        plate : labcontrol.db.Plate
            The plate being plated
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.container
                        LEFT JOIN labcontrol.well USING (container_id)
                        LEFT JOIN labcontrol.plate USING (plate_id)
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

        Returns
        -------
        str
            The new contents of the well
        """
        return self.plate.get_well(row, col).composition.update(content)

    def comment_well(self, row, col, comment):
        """Updates the comment of a well

        Parameters
        ----------
        row: int
            The well row
        col: int
            The well column
        content: str
            The new contents of the well
        """
        self.plate.get_well(row, col).composition.notes = comment


class ReagentCreationProcess(_Process):
    """Reagent creation process"""

    _process_type = 'reagent creation'

    @classmethod
    def create(cls, user, external_id, volume, reagent_type):
        """Creates a new reagent creation process

        Parameters
        ----------
        user : labcontrol.db.user.User
            User adding the reagent to the system
        external_id: str
            The external id of the reagent
        volume: float
            Initial reagent volume
        reagent_type : str
            The type of the reagent

        Returns
        -------
        ReagentCreationProcess
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
                     FROM labcontrol.tube
                        LEFT JOIN labcontrol.container USING (container_id)
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
    _table = 'labcontrol.primer_working_plate_creation_process'
    _id_column = 'primer_working_plate_creation_process_id'
    _process_type = 'primer working plate creation'

    @classmethod
    def create(cls, user, primer_set, master_set_order, creation_date=None):
        """Creates a new set of working primer plates

        Parameters
        ----------
        user : labcontrol.db.user.User
            User creating the new set of primer plates
        primer_set : labcontrol.composition.PrimerSet
            The primer set
        master_set_order : str
            The master set order
        creation_date: datetime.date, optional
            The creation date. Default: today

        Returns
        -------
        PrimerWorkingPlateCreationProcess
        """

        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(
                user, process_date=creation_date)

            sql = """INSERT INTO labcontrol.primer_working_plate_creation_process
                        (process_id, primer_set_id, master_set_order_number)
                     VALUES (%s, %s, %s)
                     RETURNING primer_working_plate_creation_process_id"""
            TRN.add(sql, [process_id, primer_set.id, master_set_order])
            instance = cls(TRN.execute_fetchlast())

            creation_date = instance.date
            plate_name_suffix = creation_date.strftime(
                Process.get_date_format())
            primer_set_plates = primer_set.plates
            check_name = '%s %s' % (primer_set_plates[0].external_id,
                                    plate_name_suffix)
            if plate_module.Plate.external_id_exists(check_name):
                # The likelihood of this happening in the real system is really
                # low, but better be safe than sorry
                plate_name_suffix = "{0} {1}".format(plate_name_suffix,
                                                     randrange(1000, 9999))

            for ps_plate in primer_set_plates:
                # Create a new working primer plate
                plate_name = '%s %s' % (ps_plate.external_id,
                                        plate_name_suffix)
                plate_config = ps_plate.plate_configuration
                work_plate = plate_module.Plate.create(
                    plate_name, plate_config)
                # Add the wells to the new plate
                for row in ps_plate.layout:
                    for ps_well in row:
                        w_well = container_module.Well.create(
                            work_plate, instance, 10, ps_well.row,
                            ps_well.column)
                        composition_module.PrimerComposition.create(
                            instance, w_well, 10, ps_well.composition)

        return instance

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
    kingfisher
    epmotion
    epmotion_tool
    extraction_kit
    sample_plate
    externally_extracted
    volume
    notes

    See Also
    --------
    Process
    """
    _table = 'labcontrol.gdna_extraction_process'
    _id_column = 'gdna_extraction_process_id'
    _process_type = 'gDNA extraction'

    @property
    def kingfisher(self):
        """The King Fisher robot used during extraction

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(
            self._get_attr('kingfisher_robot_id'))

    @property
    def epmotion(self):
        """The EpMotion robot used during extraction

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(self._get_attr('epmotion_robot_id'))

    @property
    def epmotion_tool(self):
        """The EpMotion tool used during extraction

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(self._get_attr('epmotion_tool_id'))

    @property
    def extraction_kit(self):
        """The extraction kit used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('extraction_kit_id'))

    @property
    def sample_plate(self):
        """The source sample plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition gc
                        JOIN labcontrol.gdna_composition gdc
                            ON gc.composition_id = gdc.composition_id
                        JOIN labcontrol.sample_composition ssc
                            USING (sample_composition_id)
                        JOIN labcontrol.composition sc
                            ON ssc.composition_id = sc.composition_id
                        JOIN labcontrol.well w
                            ON sc.container_id = w.container_id
                     WHERE gc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])

            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def volume(self):
        """The elution volume

        Returns
        -------
        float
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT total_volume
                     FROM labcontrol.composition
                     WHERE upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return TRN.execute_fetchlast()

    @property
    def externally_extracted(self):
        """Whether extraction was done externally

        Returns
        -------
        bool
        """
        return self._get_attr('externally_extracted')

    @classmethod
    def create(cls, user, plate, kingfisher, epmotion, epmotion_tool,
               extraction_kit, volume, gdna_plate_name,
               externally_extracted=False, extraction_date=None, notes=None):
        """Creates a new gDNA extraction process

        Parameters
        ----------
        user : labcontrol.db.user.User
            User performing the gDNA extraction
        plate: labcontrol.db.plate.Plate
            The plate being extracted
        kingfisher: labcontrol.db.equipment.Equipment
            The KingFisher used
        epmotion: labcontrol.db.equipment.Equipment
            The EpMotion used
        epmotion_tool: labcontrol.db.equipment.Equipment
            The EpMotion tool used
        extraciton_kit: labcontrol.db.composition.ReagentComposition
            The extraction kit used
        volume : float
            The elution extracted
        gdna_plate_name : str
            The name for the gdna plate
        externally_extracted : bool
            Whether the extraction was done externally
        extraction_date : datetime.date, optional
            The extraction date. Default: today
        notes : str
            Description of the extraction process

        Returns
        -------
        GDNAExtractionProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(
                user, process_date=extraction_date, notes=notes)

            # Add the row to the gdna_extraction_process table
            sql = """INSERT INTO labcontrol.gdna_extraction_process
                        (process_id, epmotion_robot_id, epmotion_tool_id,
                         kingfisher_robot_id, extraction_kit_id,
                         externally_extracted)
                     VALUES (%s, %s, %s, %s, %s, %s)
                     RETURNING gdna_extraction_process_id"""
            TRN.add(sql, [process_id, epmotion.id, epmotion_tool.id,
                          kingfisher.id, extraction_kit.id,
                          externally_extracted])
            instance = cls(TRN.execute_fetchlast())

            # Create the extracted plate
            plate_config = plate.plate_configuration
            gdna_plate = plate_module.Plate.create(
                gdna_plate_name, plate_config)
            plate_layout = plate.layout
            # Add the wells to the new plate
            for i in range(plate_config.num_rows):
                for j in range(plate_config.num_columns):
                    plated_sample = plate_layout[i][j].composition
                    if plated_sample.sample_composition_type != 'empty':
                        well = container_module.Well.create(
                            gdna_plate, instance, volume, i + 1, j + 1)
                        composition_module.GDNAComposition.create(
                            instance, well, volume, plated_sample)

        return instance


class GDNAPlateCompressionProcess(Process):
    """Gets 1 to 4 96-well gDNA plates and remaps them in a 384-well plate

    The remapping schema follows this structure:
    A B A B A B A B ...
    C D C D C D C D ...
    A B A B A B A B ...
    C D C D C D C D ...
    ...
    """
    _table = 'labcontrol.compression_process'
    _id_column = 'compression_process_id'
    _process_type = "compressed gDNA plates"

    # basically a struct: see https://stackoverflow.com/a/36033 .
    # all properties are 0-based.
    # for input_plate_order_index, 0 = top-left, 1 = top-right,
    # 2 = bottom-left, 3 = bottom-right
    InterleavedPosition = namedtuple("InterleavedPosition",
                                     "output_row_index output_col_index "
                                     "input_plate_order_index input_row_index "
                                     "input_col_index")

    @staticmethod
    def get_interleaved_quarters_position_generator(
            num_quarters, total_num_rows, total_num_cols):
        """Make generator of positions interleaving small plates onto large.

        When smaller plates are compressed onto a larger plate (such as 1 to 4
        96-well plates compressed onto a 384-well plate, or 1 to 4
        384-well plates compressed onto a 1536-well plate), one strategy is to
        interleave the input plates' wells, as shown below (for input plates
        W, X, Y, and Z):

        W X W X W X W X ...
        Y Z Y Z Y Z Y Z ...
        W X W X W X W X ...
        Y Z Y Z Y Z Y Z ...

        This function creates a generator that yields interleaved positions for
        the specified number of input plates on the output plate, in the order
        given by reading down each column of each input plate (ordered
        from W-Z)--for example, assuming W-Z are 96-well input plates and V is
        a 384-well output plate, this generates position mappings in the
        following order:
        W:A1->V:A1
        W:B1->V:C1
        W:C1->V:E1
        ...
        W:H1->V:O1
        W:A2->V:A3
        W:B2->V:C3
        ...
        W:H12->V:O23
        X:A1->V:A2
        X:B2->V:C2
        ... etc.

        Parameters
        ----------
        num_quarters : int
            Number of quarters of interleaved positions to generate; equivalent
            to number of smaller plates to interleave.  Must be 1-4, inclusive.
        total_num_rows : int
            Number of rows on large plate (e.g., 16 for a 384-well plate); must
            be even.
        total_num_cols : int
            Number of columns on large plate (e.g., 24 for a 384-well plate);
            must be even.

        Yields
        -------
        InterleavedPosition namedtuple

        Raises
        ------
        ValueError
            if num_quarters is not an integer in the range 1-4, inclusive or
            if total_num_rows is not positive and even or
            if total_num_cols is not positive and even
        """

        if num_quarters < 1 or num_quarters > 4 or \
                int(num_quarters) != num_quarters:
            raise ValueError("Expected number of quarters to be an integer"
                             " between 1 and 4 but received {0}".format(
                                    num_quarters))

        if total_num_rows <= 0 or total_num_rows % 2 > 0 or \
                total_num_cols <= 0 or total_num_cols % 2 > 0:

            raise ValueError("Expected number of rows and columns to be"
                             " positive integers evenly divisible by two"
                             " but received {0} rows and {1}"
                             " columns".format(total_num_rows,
                                               total_num_cols))

        input_max_rows = int(total_num_rows / 2)
        input_max_cols = int(total_num_cols / 2)

        for input_plate_order in range(0, num_quarters):
            row_pad = int(input_plate_order / 2)  # rounds down for positive #s
            col_pad = input_plate_order % 2

            for input_col_index in range(0, input_max_cols):
                output_col_index = (input_col_index * 2) + col_pad
                for input_row_index in range(0, input_max_rows):
                    output_row_index = (input_row_index * 2) + row_pad
                    result = GDNAPlateCompressionProcess.InterleavedPosition(
                        output_row_index, output_col_index, input_plate_order,
                        input_row_index, input_col_index)
                    yield result

    @classmethod
    def create(cls, user, plates, plate_ext_id, robot):
        """Creates a new gDNA compression process

        Parameters
        ----------
        user : labcontrol.db.user.User
            User performing the plating
        plates: list of labcontrol.db.plate.Plate
            The plates to compress
        plate_ext_id : str
            The external plate id
        robot: Equipment
            The robot performing the compression

        Raises
        ------
        ValueError

        Returns
        -------
        GDNAPlateCompressionProcess
        """
        if not (1 <= len(plates) <= 4):
            raise ValueError(
                'Cannot compress %s gDNA plates. Please provide 1 to 4 '
                'gDNA plates' % len(plates))

        volume = 1  # TODO: where did this magic # come from and can it change?

        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the compression_process table
            sql = """INSERT INTO labcontrol.compression_process
                        (process_id, robot_id)
                     VALUES (%s, %s)
                     RETURNING compression_process_id"""
            TRN.add(sql, [process_id, robot.id])
            instance = cls(TRN.execute_fetchlast())

        # get the input plates' layouts (to avoid repeated sql calls)
        plate_layouts = [x.layout for x in plates]

        # Create the output plate
        # Magic number 3 -> 384-well plate
        plate_config_384 = plate_module.PlateConfiguration(3)
        plate = plate_module.Plate.create(plate_ext_id, plate_config_384)

        # Compress the plates
        position_generator = GDNAPlateCompressionProcess.\
            get_interleaved_quarters_position_generator(
                len(plates), plate_config_384.num_rows,
                plate_config_384.num_columns)

        for p in position_generator:  # each position on interleaved plate
            input_layout = plate_layouts[p.input_plate_order_index]
            input_well = input_layout[p.input_row_index][p.input_col_index]
            # completely empty wells (represented as Nones) are ignored
            if input_well is not None:
                # note adding 1 to the row/col from p, as those are
                # 0-based while the positions in Well are 1-based
                out_well = container_module.Well.create(
                    plate, instance, volume, p.output_row_index + 1,
                    p.output_col_index + 1)
                composition_module.CompressedGDNAComposition.create(
                    instance, out_well, volume, input_well.composition)

        return instance

    @property
    def robot(self):
        """The robot performing the compression"""
        return equipment_module.Equipment(self._get_attr('robot_id'))

    @property
    def gdna_plates(self):
        """The input gdna plates"""
        with sql_connection.TRN as TRN:
            # Rationale: giving the compression algorithm, we only need to look
            # at the 4 wells on the top left corner (1, 1), (1, 2), (2, 1) and
            # (2, 2), and in that order, to know which plates have been
            # compressed
            sql = """SELECT gw.plate_id
                     FROM labcontrol.composition cc
                        JOIN labcontrol.well cw ON
                            cc.container_id = cw.container_id
                        JOIN labcontrol.compressed_gdna_composition cgc ON
                            cc.composition_id = cgc.composition_id
                        JOIN labcontrol.gdna_composition gdnac ON
                            cgc.gdna_composition_id = gdnac.gdna_composition_id
                        JOIN labcontrol.composition gc ON
                            gdnac.composition_id = gc.composition_id
                        JOIN labcontrol.well gw ON
                            gc.container_id = gw.container_id
                     WHERE cc.upstream_process_id = %s AND
                        cw.row_num IN (1, 2) AND cw.col_num IN (1, 2)
                     ORDER BY cw.row_num, cw.col_num"""
            TRN.add(sql, [self.process_id])
            return [plate_module.Plate(pid)
                    for pid in TRN.execute_fetchflatten()]


class LibraryPrep16SProcess(Process):
    """16S Library Prep process object

    Attributes
    ----------
    mastermix_lots
    water_lots
    epmotions

    See Also
    --------
    Process
    """
    _table = 'labcontrol.library_prep_16s_process'
    _id_column = 'library_prep_16s_process_id'
    _process_type = '16S library prep'

    @classmethod
    def create(cls, user, plate, primer_plate, lib_plate_name, epmotion,
               epmotion_tool_tm300, epmotion_tool_tm50, master_mix, water_lot,
               volume, preparation_date=None):
        """Creates a new 16S library prep process

        Parameters
        ----------
        user : labcontrol.db.user.User
            User performing the library prep
        plate: labcontrol.db.plate.Plate
            The plate being prepared for amplicon sequencing
        primer_plate: labcontrol.db.plate.Plate
            The primer plate
        lib_plate_name: str
            The name of the prepared plate
        epmotion: labcontrol.db.equipment.Equipment
            The EpMotion
        epmotion_tool_tm300: labcontrol.db.equipment.Equipment
            The EpMotion TM300 8 tool
        epmotion_tool_tm50: labcontrol.db.equipment.Equipment
            The EpMotion TM300 8 tool
        master_mix: labcontrol.db.composition.ReagentComposition
            The mastermix used
        water_lot: labcontrol.db.composition.ReagentComposition
            The water lot used
        volume : float
            The PCR total volume in the wells
        preparation_date : datetime.date, optional
            The preparation date. Default: today

        Returns
        -------
        LibraryPrep16SProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(
                user, process_date=preparation_date)

            # Add the row to the library_prep_16s_process
            sql = """INSERT INTO labcontrol.library_prep_16s_process
                        (process_id, epmotion_robot_id,
                         epmotion_tm300_8_tool_id, epmotion_tm50_8_tool_id,
                         master_mix_id, water_lot_id)
                     VALUES (%s, %s, %s, %s, %s, %s)
                     RETURNING library_prep_16s_process_id"""
            TRN.add(sql, [process_id, epmotion.id, epmotion_tool_tm300.id,
                          epmotion_tool_tm50.id, master_mix.id, water_lot.id])
            instance = cls(TRN.execute_fetchlast())

            # Create the library plate
            plate_config = plate.plate_configuration
            library_plate = plate_module.Plate.create(lib_plate_name,
                                                      plate_config)
            gdna_layout = plate.layout
            primer_layout = primer_plate.layout
            for i in range(plate_config.num_rows):
                for j in range(plate_config.num_columns):
                    if gdna_layout[i][j] is not None:
                        well = container_module.Well.create(
                            library_plate, instance, volume, i + 1, j + 1)
                        composition_module.LibraryPrep16SComposition.create(
                            instance, well, volume,
                            gdna_layout[i][j].composition,
                            primer_layout[i][j].composition)

        return instance

    @property
    def mastermix(self):
        """The master mix lot used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('master_mix_id'))

    @property
    def water_lot(self):
        """The water lot used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('water_lot_id'))

    @property
    def epmotion(self):
        """The EpMotion robot used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(self._get_attr('epmotion_robot_id'))

    @property
    def epmotion_tm300_tool(self):
        """The EpMotion tm300 tool used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(
            self._get_attr('epmotion_tm300_8_tool_id'))

    @property
    def epmotion_tm50_tool(self):
        """The EpMotion tm50 tool used

        Returns
        -------
        Equipment
        """
        return equipment_module.Equipment(
            self._get_attr('epmotion_tm50_8_tool_id'))

    @property
    def gdna_plate(self):
        """The input gdna plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition lc
                        JOIN labcontrol.library_prep_16s_composition l16sc
                            ON lc.composition_id = l16sc.composition_id
                        JOIN labcontrol.gdna_composition gdc
                            USING (gdna_composition_id)
                        JOIN labcontrol.composition gc
                            ON gc.composition_id = gdc.composition_id
                        JOIN labcontrol.well w ON gc.container_id = w.container_id
                     WHERE lc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])

            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def primer_plate(self):
        """The primer plate

        Returns
        -------
        plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition lc
                        JOIN labcontrol.library_prep_16s_composition l16sc
                            ON lc.composition_id = l16sc.composition_id
                        JOIN labcontrol.primer_composition prc
                            USING (primer_composition_id)
                        JOIN labcontrol.composition pc
                            ON pc.composition_id = prc.composition_id
                        JOIN labcontrol.well w ON pc.container_id = w.container_id
                     WHERE lc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def volume(self):
        """The PCR Total volume

        Returns
        -------
        float
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT total_volume
                     FROM labcontrol.composition
                     WHERE upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return TRN.execute_fetchlast()


class NormalizationProcess(Process):
    """Normalization process object for normalization of one 384-well plate

    Attributes
    ----------
    quantification_process
    water_lot

    See Also
    --------
    Process
    """
    _table = 'labcontrol.normalization_process'
    _id_column = 'normalization_process_id'
    _process_type = 'gDNA normalization'

    @staticmethod
    def _calculate_norm_vol(dna_concs, ng=5, min_vol=25, max_vol=3500,
                            resolution=2.5):
        """Calculates nanoliters of each sample to add to get a normalized pool

        Parameters
        ----------
        dna_concs : numpy array of float
            The concentrations calculated via PicoGreen (ng/uL)
        ng : float, optional
            The amount of DNA to pool (ng). Default: 5
        min_vol : float, optional
            The minimum volume to pool (nL). Default: 25
        max_vol : float, optional
            The max volume to pool (nL). Default: 3500
            Note that in the wet lab's Jupyter notebook, this parameter is
            referred to as "total_vol".
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
        user : labcontrol.db.user.User
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
            func_data = {
                'function': 'default',
                'parameters': {'total_volume': total_vol, 'target_dna': ng,
                               'min_vol': min_vol, 'max_volume': max_vol,
                               'resolution': resolution, 'reformat': reformat}}
            sql = """INSERT INTO labcontrol.normalization_process
                        (process_id, quantitation_process_id, water_lot_id,
                         normalization_function_data)
                     VALUES (%s, %s, %s, %s)
                     RETURNING normalization_process_id"""
            TRN.add(sql, [process_id, quant_process.id, water.id,
                          dumps(func_data)])
            instance = cls(TRN.execute_fetchlast())

            # Retrieve all the concentration values
            concs = quant_process.concentrations
            # Transform the concentrations to a numpy array
            np_conc = np.asarray([raw_con for _, raw_con, _ in concs])
            dna_v = NormalizationProcess._calculate_norm_vol(
                np_conc, ng, min_vol, max_vol, resolution)
            water_v = total_vol - dna_v

            # Create the plate. 3 -> 384-well plate
            plate_config = plate_module.PlateConfiguration(3)
            plate = plate_module.Plate.create(plate_name, plate_config)
            for (comp, _, _), dna_vol, water_vol in zip(concs, dna_v, water_v):
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

    @property
    def compressed_plate(self):
        """The input compressed plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition nc
                        JOIN labcontrol.normalized_gdna_composition ngc
                            ON nc.composition_id = ngc.composition_id
                        JOIN labcontrol.compressed_gdna_composition cgdnac
                            USING (compressed_gdna_composition_id)
                        JOIN labcontrol.composition cc
                            ON cc.composition_id = cgdnac.composition_id
                        JOIN labcontrol.well w ON cc.container_id = w.container_id
                     WHERE nc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def normalization_function_data(self):
        """The information about the normalization function

        Returns
        -------
        str
        """
        return self._get_attr('normalization_function_data')

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
            'Sample ID\tSource Plate Name\tSource Plate Type\tSource Well'
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
            for comp, conc, _ in self.quantification_process.concentrations}

        dna_vol = "dna_vol"
        water_vol = "water_vol"
        sample_plate = "sample_plate"
        sample_row = "sample_row"
        sample_column = "sample_column"
        compressed_well = "compressed_well"
        dest_well = "dest_well"
        sample_name = "sample_name"
        dna_conc = "dna_conc"

        well_index = 0
        df = pd.DataFrame(columns=[dna_vol, water_vol,
                                   sample_plate, sample_row, sample_column,
                                   compressed_well, dest_well,
                                   sample_name, dna_conc])
        layout = self.plates[0].layout
        for row in layout:
            for well in row:
                if well:
                    composition = well.composition
                    # For the source well we need to take a look at the
                    # gdna comp
                    c_gdna_comp = composition.compressed_gdna_composition
                    # For the sample name we need to check the sample
                    # composition and its container
                    sample_comp = c_gdna_comp.gdna_composition.\
                        sample_composition
                    sample_container = sample_comp.container
                    name = _format_name_for_picklist(sample_comp)
                    # For the DNA concentrations we need to look at
                    # the quantification process
                    df.loc[well_index] = [composition.dna_volume,
                                          composition.water_volume,
                                          sample_container.plate.id,
                                          sample_container.row,
                                          sample_container.column,
                                          c_gdna_comp.container.well_id,
                                          well.well_id,
                                          name,
                                          concentrations[c_gdna_comp]]
                    well_index = well_index + 1

        # get order of plates on compression plate
        # Per pandas docs, "Uniques are returned in order of appearance"
        plate_series = df[sample_plate].unique()
        replacement_dict = {plate_id: plate_order for plate_order, plate_id in
                            enumerate(plate_series)}
        df[sample_plate] = df[sample_plate].replace(replacement_dict)

        # sort the df by sample plate order on compression plate, then by
        # sample plate column, then by sample plate row.  Note that these
        # rows do not make it through into the actual picklist; they are
        # used ONLY to determine the order of the sorting
        df = df.sort_values([sample_plate, sample_column, sample_row])

        # _format_picklist expects numpy arrays
        dna_vols = df[dna_vol].values
        water_vols = df[water_vol].values
        wells = df[compressed_well].values
        dest_wells = df[dest_well].values
        sample_names = df[sample_name].values
        dna_concs = df[dna_conc].values

        return NormalizationProcess._format_picklist(
            dna_vols, water_vols, wells, dest_wells=dest_wells,
            sample_names=sample_names, dna_concs=dna_concs)


class LibraryPrepShotgunProcess(Process):
    """Shotgun Library Prep process object

    Attributes
    ----------
    kapa_hyper_plus_kit
    stub_lot
    normalization_process

    See Also
    --------
    Process
    """
    _table = 'labcontrol.library_prep_shotgun_process'
    _id_column = 'library_prep_shotgun_process_id'
    _process_type = 'shotgun library prep'

    @classmethod
    def create(cls, user, plate, plate_name, kapa_hyper_plus_kit, stub_lot,
               volume, i5_plate, i7_plate):
        """Creats a new LibraryPrepShotgunProcess

        Parameters
        ----------
        user : labcontrol.db.user.User
            User performing the library prep
        plate: labcontrol.db.plate.Plate
            The normalized gDNA plate of origin
        plate_name: str
            The library
        kapa_hyper_plus_kit: labcontrol.db.composition.ReagentComposition
            The Kapa Hyper Plus kit used
        stub_lot: labcontrol.db.composition.ReagentComposition
            The stub lot used
        volume : float
            The initial volume in the wells
        i5_plate: labcontrol.db.plate.Plate
            The i5 primer working plate
        i7_plate: labcontrol.db.plate.Plate
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
            sql = """INSERT INTO labcontrol.library_prep_shotgun_process
                        (process_id, kapa_hyper_plus_kit_id, stub_lot_id,
                         normalization_process_id)
                     VALUES (%s, %s, %s, (
                        SELECT DISTINCT normalization_process_id
                            FROM labcontrol.normalization_process np
                                JOIN labcontrol.container c
                                    ON np.process_id =
                                        c.latest_upstream_process_id
                                JOIN labcontrol.well USING (container_id)
                                WHERE plate_id = %s))
                     RETURNING library_prep_shotgun_process_id"""
            TRN.add(sql, [process_id, kapa_hyper_plus_kit.id, stub_lot.id,
                          plate.id])
            instance = cls(TRN.execute_fetchlast())

            # Get the primer set for the plates
            sql = """SELECT DISTINCT shotgun_primer_set_id
                     FROM labcontrol.shotgun_combo_primer_set cps
                        JOIN labcontrol.primer_set_composition psc
                            ON cps.i5_primer_set_composition_id =
                                psc.primer_set_composition_id
                        JOIN labcontrol.primer_composition pc USING
                            (primer_set_composition_id)
                        JOIN labcontrol.composition c
                            ON pc.composition_id = c.composition_id
                        JOIN labcontrol.well USING (container_id)
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

            # walk across all the positions on the plate in interleaved order;
            # magic number 4 = get all positions (all 4 quarters)
            position_generator = GDNAPlateCompressionProcess. \
                get_interleaved_quarters_position_generator(
                    4, plate.plate_configuration.num_rows,
                    plate.plate_configuration.num_columns)

            combo_index = 0
            plate_layout = plate.layout  # time-consuming so do only once
            for p in position_generator:  # each position on interleaved plate
                # note OUTPUT indices rather than input indices because the
                # normalized gdna plate we are working from is the SAME SIZE
                # as the library prep plate, not 1/4 its size.
                input_well = \
                    plate_layout[p.output_row_index][p.output_col_index]
                # completely empty wells (represented as Nones) are ignored
                if input_well is not None:
                    curr_combo = idx_combos[combo_index]
                    # As database entities, these "wells" represent the
                    # positions of the current i5 and i7 primers on the primer
                    # set plate maps (NOT on the chosen actual, physical primer
                    # working plates for these primer sets).  That is why we
                    # aren't just getting the compositions that go with these
                    # "wells"--these aren't real, physical wells and their
                    # compositions aren't real, physical compositions.
                    i5_well = curr_combo[0].container
                    i7_well = curr_combo[1].container

                    # While the positions of the relevant i5 and i7 primers
                    # in the i5 and i7 plate maps have separate database
                    # entities from the positions of those primers on the
                    # actual physical primer working plates being used, the
                    # primers are at the same positions (of course!) in the
                    # working plates made from a given primer set plate map
                    # as they are in the plate map itself--duh :)
                    # Thus, we use the position of the relevant i5 and i7
                    # primers in the plate map (gotten above) to find the
                    # real, physical compositions for the primers at those
                    # positions on the real, physical primer working plates.
                    # Note subtracting 1 from positions in Well, as those
                    # are 1-based while the positions in layout are 0-based.
                    i5_comp = i5_layout[i5_well.row - 1][i5_well.column - 1]\
                        .composition
                    i7_comp = i7_layout[i7_well.row - 1][i7_well.column - 1]\
                        .composition

                    # Note adding 1 to the row/col from p, as those are
                    # 0-based while the positions in Well are 1-based
                    lib_well = container_module.Well.create(
                        lib_plate, instance, volume, p.output_row_index + 1,
                        p.output_col_index + 1)
                    composition_module.LibraryPrepShotgunComposition.create(
                        instance, lib_well, volume, input_well.composition,
                        i5_comp, i7_comp)
                    combo_index = combo_index + 1

        return instance

    @property
    def kapa_hyper_plus_kit(self):
        """The Kapa Hyper Plus kit used

        Returns
        -------
        ReagentComposition
        """
        return composition_module.ReagentComposition(
            self._get_attr('kapa_hyper_plus_kit_id'))

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

    @property
    def normalized_plate(self):
        """The input normalized plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition lc
                        JOIN labcontrol.library_prep_shotgun_composition lpsc
                            ON lc.composition_id = lpsc.composition_id
                        JOIN labcontrol.normalized_gdna_composition ngdnac
                            USING (normalized_gdna_composition_id)
                        JOIN labcontrol.composition nc
                            ON ngdnac.composition_id = nc.composition_id
                        JOIN labcontrol.well w ON nc.container_id = w.container_id
                     WHERE lc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def i5_primer_plate(self):
        """The i5 primer plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition lc
                        JOIN labcontrol.library_prep_shotgun_composition lsc
                            ON lc.composition_id = lsc.composition_id
                        JOIN labcontrol.primer_composition prc
                            ON lsc.i5_primer_composition_id =
                                prc.primer_composition_id
                        JOIN labcontrol.composition pc
                            ON prc.composition_id = pc.composition_id
                        JOIN labcontrol.well w ON pc.container_id = w.container_id
                     WHERE lc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def i7_primer_plate(self):
        """The i7 primer plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labcontrol.composition lc
                        JOIN labcontrol.library_prep_shotgun_composition lsc
                            ON lc.composition_id = lsc.composition_id
                        JOIN labcontrol.primer_composition prc
                            ON lsc.i7_primer_composition_id =
                                prc.primer_composition_id
                        JOIN labcontrol.composition pc
                            ON prc.composition_id = pc.composition_id
                        JOIN labcontrol.well w ON pc.container_id = w.container_id
                     WHERE lc.upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return plate_module.Plate(TRN.execute_fetchlast())

    @property
    def volume(self):
        """The volume

        Returns
        -------
        float
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT total_volume
                     FROM labcontrol.composition
                     WHERE upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return TRN.execute_fetchlast()

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
            'Sample ID\tSource Plate Name\tSource Plate Type\tSource Well\t'
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

    def generate_echo_picklist(self):
        """Generates Echo pick list for preparing the shotgun library

        Returns
        -------
        str
            The echo-formatted pick list
        """

        def whitespace_to_underscore(a_str):
            return re.sub('\s+', '_', a_str)

        sample_names = []
        sample_wells = []
        indices = {'i5 name': {}, 'i5 plate': {}, 'i5 sequence': {},
                   'i5 well': {}, 'i7 name': {}, 'i7 plate': {},
                   'i7 sequence': {}, 'i7 well': {}, 'index combo': {},
                   'index combo seq': {}}

        for idx, well in enumerate(chain.from_iterable(self.plates[0].layout)):
            if well is None:
                continue
            # Add the sample well
            sample_wells.append(well.well_id)
            # Get the sample name - we need to go back to the SampleComposition
            lib_comp = well.composition
            sample_comp = lib_comp.normalized_gdna_composition\
                .compressed_gdna_composition.gdna_composition\
                .sample_composition
            sample_names.append(_format_name_for_picklist(sample_comp))
            # Retrieve all the information about the indices
            i5_comp = lib_comp.i5_composition.primer_set_composition
            i5_well = i5_comp.container
            indices['i5 name'][idx] = i5_comp.external_id
            indices['i5 plate'][idx] = whitespace_to_underscore(
                i5_well.plate.external_id)
            indices['i5 sequence'][idx] = i5_comp.barcode
            indices['i5 well'][idx] = i5_well.well_id

            i7_comp = lib_comp.i7_composition.primer_set_composition
            i7_well = i7_comp.container
            indices['i7 name'][idx] = i7_comp.external_id
            indices['i7 plate'][idx] = whitespace_to_underscore(
                i7_well.plate.external_id)
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
    _table = 'labcontrol.quantification_process'
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
        lib_concentration = (dna_vals / (660 * float(size))) * 10 ** 6

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
        contents : str
            The contents of the pico green plate reader output
        sep: str
            sep char used in quant file
        conc_col_name: str
            name to use for concentration column output

        Returns
        -------
        pico_df: pandas DataFrame object
            DataFrame relating well location and DNA concentration
        """

        cleaned_contents = QuantificationProcess._rationalize_pico_csv_string(
            contents)
        contents_io = StringIO(cleaned_contents)

        # when reading in concentrations, force them to come in as strings
        # so can check for overflow entries using regex
        raw_df = pd.read_csv(contents_io, sep=sep, skiprows=2, skipfooter=5,
                             engine='python',
                             converters={'[Concentration]': lambda x: str(x)})

        pico_df = raw_df[['Well', '[Concentration]']]
        pico_df = pico_df.rename(columns={'[Concentration]': conc_col_name})

        # any concentrations containing strings of question marks
        # (generated when you overflow the sensor; usually due to sample being
        # too concentrated) should be replaced with the highest concentration
        # found in this file, per wet lab practice. Start by
        # getting mask of the concentration rows that hold only question marks;
        # regex matches start of string followed by one or more literal
        # question marks, followed by end of string
        overflow_mask = pico_df[conc_col_name].str.contains(
            r'^\?+$', regex=True)

        # coerce oddball concentrations to np.nan
        pico_df[conc_col_name] = pd.to_numeric(pico_df[conc_col_name],
                                               errors='coerce')

        # find the highest concentration in the file and replace all overflow
        # concentrations with that value
        max_concentration = pico_df[conc_col_name].max()
        pico_df.loc[overflow_mask, conc_col_name] = max_concentration

        # if there are any NaN concentrations left, there's a problem with the
        # parsing, so throw an error
        if pico_df[conc_col_name].isnull().any():
            raise ValueError("Some concentrations in pico green quantitation "
                             "file are NaN: {0}".format(pico_df))

        return pico_df

    @staticmethod
    def _rationalize_pico_csv_string(contents):
        # Some plate reader files end with CRLF; convert to LF
        contents = contents.replace('\r\n', '\n')

        # Some plate reader files end with JUST CR;
        # convert any of those remaining to LF
        contents = contents.replace('\r', '\n')

        # anything valued as "<X" is converted to just "X"
        # e.g., <0.000 becomes 0.000
        contents = contents.replace('<', '')

        # anything valued as ">X" is converted to just "X"
        contents = contents.replace('>', '')
        return contents

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

        if file_format not in parsers:
            raise ValueError(
                'File format %s not recognized. Supported file formats: %s'
                % (file_format, ', '.join(parsers)))
        df = parsers[file_format](contents)
        array = QuantificationProcess._make_2D_array(df, rows=rows, cols=cols)
        return array.astype(float)

    @classmethod
    def create_manual(cls, user, quantifications, notes=None):
        """Creates a new quantification process for a pool

        Parameters
        ----------
        user: labcontrol.db.user.User
            User performing the quantification process
        quantifications: list of dict
            The quantifications in the form of {'composition': Composition,
            'concentration': float}
        notes: str
            Description of the quantification process
                (e.g., 'Requantification of failed plate', etc).
                Default: None

        Returns
        -------
        QuantificationProcess
        """
        return cls._create(user, notes, quantifications)

    @classmethod
    def create(cls, user, plate, concentrations, notes=None):
        """Creates a new quantification process for a plate

        Parameters
        ----------
        user: labcontrol.db.user.User
            User performing the quantification process
        plate: labcontrol.db.plate.Plate
            The plate being quantified
        concentrations: 2D np.array
            The plate concentrations
        notes: str
            Description of the quantification process
                (e.g., 'Requantification of failed plate', etc).
                Default: None

        Returns
        -------
        QuantificationProcess
        """
        return cls._create(user, notes, concentrations, plate)

    @classmethod
    def _create(cls, user, notes, concentrations, plate=None):
        """Creates a new quantification process for a plate or a pool.

        Parameters
        ----------
        user: labcontrol.db.user.User
            User performing the quantification process
        notes: str
            Description of the quantification process
                (e.g., 'Requantification of failed plate', etc).  May be None.
        concentrations: 2D np.array OR list of dict
            If plate is not None, the plate concentrations as a 2D np.array.
            If plate IS None, the pool component concentrations as a list of
                dicts where each dict is in the form of
                {'composition': Composition,  'concentration': float}
        plate: labcontrol.db.plate.Plate
            The plate being quantified, if relevant. Default: None

        Returns
        -------
        QuantificationProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user, notes=notes)

            # Add the row to the quantification process table
            sql = """INSERT INTO labcontrol.quantification_process (process_id)
                     VALUES (%s) RETURNING quantification_process_id"""
            TRN.add(sql, [process_id])
            instance = cls(TRN.execute_fetchlast())

            sql = """INSERT INTO labcontrol.concentration_calculation
                        (quantitated_composition_id, upstream_process_id,
                         raw_concentration)
                     VALUES (%s, %s, %s)"""

            if plate is not None:
                sql_args = cls._generate_concentration_inputs_for_plate(
                    plate, concentrations, instance)
            else:
                sql_args = cls._generate_concentration_inputs_for_pool(
                    concentrations, instance)

            if len(sql_args) == 0:
                raise ValueError('No concentration values have been provided')

            TRN.add(sql, sql_args, many=True)
            TRN.execute()

        return instance

    @classmethod
    def _generate_concentration_inputs_for_plate(cls, plate, concentrations,
                                                 quant_process_instance):
        sql_args = []
        layout = plate.layout

        for p_row, c_row in zip(layout, concentrations):
            for well, conc in zip(p_row, c_row):
                if well is not None:
                    sql_args.append([well.composition.composition_id,
                                     quant_process_instance.id, conc])
        return sql_args

    @classmethod
    def _generate_concentration_inputs_for_pool(cls, concentrations,
                                                quant_process_instance):
        sql_args = []
        for quant in concentrations:
            sql_args.append([quant['composition'].composition_id,
                             quant_process_instance.id,
                             quant['concentration']])
        return sql_args

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
                     FROM labcontrol.concentration_calculation
                     WHERE upstream_process_id = %s
                     ORDER BY concentration_calculation_id"""
            TRN.add(sql, [self._id])
            return [
                (composition_module.Composition.factory(comp_id), r_con, c_con)
                for comp_id, r_con, c_con in TRN.execute_fetchindex()]

    def compute_concentrations(self, size=500):
        """Compute the normalized library molarity based on pico green dna
        concentrations estimates.

        Parameters
        ----------
        size: int, optional
            The average library molecule size, in bp.
        """
        concentrations = self.concentrations
        layout = concentrations[0][0].container.plate.layout

        res = None

        sample_concs = np.zeros_like(layout, dtype=float)
        for comp, r_conc, _ in concentrations:
            well = comp.container
            row = well.row - 1
            col = well.column - 1
            sample_concs[row][col] = r_conc

        res = QuantificationProcess._compute_pico_concentration(
            sample_concs, size)

        if res is not None:
            sql_args = []
            for p_row, c_row in zip(layout, res):
                for well, conc in zip(p_row, c_row):
                    if well is not None:
                        sql_args.append([conc, self.id,
                                         well.composition.composition_id])
            sql = """UPDATE labcontrol.concentration_calculation
                        SET computed_concentration = %s
                        WHERE upstream_process_id = %s AND
                              quantitated_composition_id = %s"""

            with sql_connection.TRN as TRN:
                TRN.add(sql, sql_args, many=True)
                TRN.execute()


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
    _table = 'labcontrol.pooling_process'
    _id_column = 'pooling_process_id'
    _process_type = 'pooling'

    @staticmethod
    def estimate_pool_conc_vol(sample_vols, sample_concs):
        """Estimates the molarity and volume of a pool.

        Parameters
        ----------
        sample_concs : numpy array of float
            The concentrations calculated via PicoGreen (nM)
        sample_vols : numpy array of float
            The calculated pooling volumes (nL)

        Returns
        -------
        pool_conc : float
            The estimated actual concentration of the pool, in nM
        total_vol : float
            The total volume of the pool, in nL
        """
        # scalar to adjust nL to L for molarity calculations
        nl_scalar = 1e-9
        # calc total pool pmols
        total_pmols = np.multiply(sample_concs, sample_vols) * nl_scalar
        # calc total pool vol in nanoliters
        total_vol = sample_vols.sum()
        # pool pM is total pmols divided by total liters
        # (total vol in nL * 1 L / 10^9 nL)
        pool_conc = total_pmols.sum() / (total_vol * nl_scalar)
        return (pool_conc, total_vol)

    @staticmethod
    def compute_pooling_values_eqvol(sample_concs, total_vol=60.0, **kwargs):
        """Computes molar concentration of libraries from concentration values,
        using an even volume per sample

        Parameters
        ----------
        sample_concs : numpy array of float
            The concentrations calculated via PicoGreen (nM)
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
    def compute_pooling_values_minvol(
            sample_concs, sample_fracs=None, floor_vol=2, floor_conc=16,
            total=240, total_each=True, vol_constant=1, **kwargs):
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
        quantity (`total`, default .01). For a perfect 384 sample library,
        in which you had all samples at a concentration of exactly 400 nM and
        wanted a total volume of 60 uL, this would be 0.024 nmol.

        For a Novaseq, we expect to need 150 uL at 4 nM, or about 0.0006 nmol.
        Taking into account sample loss on the pippin prep (1/2) and molar loss
        due to exclusion of primer dimers (1/2), figure we need 4 times that or
        0.0024.

        Parameters
        ----------
        sample_concs: 2D array of float
            sample concentrations, with numerator same units as `total`.
        sample_fracs: 2D of float, optional
            fractional value for each sample (default 1/N)
        floor_vol: float, optional
            volume at which samples below floor_conc will be pooled.
            Default: 100
        floor_conc: float, optional
            minimum value for pooling at real estimated value. Default: 40
        total : float, optional
            total quantity (numerator) for pool. Unitless, but could represent
            for example ng or nmol. Default: 240
        total_each : bool, optional
            whether `total` refers to the quantity pooled *per sample*
            (default; True) or to the total quantity of the pool.
        vol_constant : float, optional
            conversion factor between `sample_concs` demoninator and output
            pooling volume units. E.g. if pooling ng/µL concentrations and
            producing µL pool volumes, `vol_constant` = 1. If pooling nM
            concentrations and producing nL pool volumes, `vol_constant` =
            10**-9. Default: 1

        Returns
        -------
        sample_vols: np.array of floats
            the volumes in nL per each sample pooled
        """

        if sample_fracs is None:
            sample_fracs = np.ones(sample_concs.shape)

        if not total_each:
            sample_fracs = sample_fracs / sample_concs.size

        with np.errstate(divide='ignore'):
            # calculate volumetric fractions including floor val
            sample_vols = (total * sample_fracs) / sample_concs

        # convert volume from concentration units to pooling units
        sample_vols *= vol_constant
        # drop volumes for samples below floor concentration to floor_vol
        sample_vols[sample_concs < floor_conc] = floor_vol

        return sample_vols

    @staticmethod
    def adjust_blank_vols(pool_vols, comp_blanks, blank_vol):
        """Specifically adjust blanks to a value specified volume

        Parameters
        ----------
        pool_vols: np.array
            The per-well pool volumes
        comp_blanks: np.array of bool
            Boolean array indicating which wells are blanks
        blank_vol: float
            Volume at which to pool blanks

        Returns
        -------
        np.array
            The adjusted per-well pool volumes
        """

        pool_vols[comp_blanks] = blank_vol

        return (pool_vols)

    @staticmethod
    def select_blanks(pool_vols, raw_concs, comp_blanks, blank_num):
        """Specifically retain only the N most concentrated blanks

        Parameters
        ----------
        pool_vols: np.array
            The per-well pool volumes
        raw_concs: np.array of float
            The per-well concentrations
        comp_blanks: np.array of bool
            Boolean array indicating which wells are blanks
        blank_num: int
            The number of blanks N to pool (in order of highest concentration)

        Returns
        -------
        np.array
            The adjusted per-well pool volumes
        """

        if blank_num < 0:
            raise ValueError("blank_num cannot be negative (passed: %s)" %
                             blank_num)

        if comp_blanks.shape != pool_vols.shape != raw_concs.shape:
            raise ValueError("all input arrays must be same shape")

        blanks = []

        adjusted_vols = pool_vols.copy()

        for index, x in np.ndenumerate(comp_blanks):
            if x:
                blanks.append((raw_concs[index], index))

        sorted_blanks = sorted(blanks, key=lambda tup: tup[0], reverse=True)

        reject_blanks = sorted_blanks[blank_num:]

        for _, idx in reject_blanks:
            adjusted_vols[idx] = 0

        return (adjusted_vols)

    @classmethod
    def create(cls, user, quantification_process, pool_name, volume,
               input_compositions, func_data, robot=None, destination=None):
        """Creates a new pooling process

        Parameters
        ----------
        user: labcontrol.db.user.User
            User performing the pooling process
        quantification_process: labcontrol.db.process.QuantificationProcess
            The quantification process this pooling is based on
        pool_name: str
            The name of the new pool
        volume: float
            The initial volume
        input_compositions: list of dicts
            The input compositions for the pool {'composition': Composition,
            'input_volume': float, 'percentage_of_output': float}
        func_data : dict
            Dictionary with the pooling function information
        robot: labcontrol.equipment.Equipment, optional
            The robot performing the pooling, if not manual
        destination: str
            The EpMotion destination tube

        Returns
        -------
        PoolingProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the pooling process table
            sql = """INSERT INTO labcontrol.pooling_process
                        (process_id, quantification_process_id, robot_id,
                         destination, pooling_function_data)
                     VALUES (%s, %s, %s, %s, %s)
                     RETURNING pooling_process_id"""
            r_id = robot.id if robot is not None else None
            if r_id is None:
                destination = None
            TRN.add(sql, [process_id, quantification_process.id, r_id,
                          destination, dumps(func_data)])
            instance = cls(TRN.execute_fetchlast())

            # Create the new pool
            tube = container_module.Tube.create(instance, pool_name, volume)
            pool = composition_module.PoolComposition.create(
                instance, tube, volume)

            # Link the pool with its contents
            sql = """INSERT INTO labcontrol.pool_composition_components
                        (output_pool_composition_id, input_composition_id,
                         input_volume, percentage_of_output)
                     VALUES (%s, %s, %s, %s)"""
            sql_args = []
            for in_comp in input_compositions:
                # The wet lab pointed out that we don't need to pool the ones
                # that have a value below 0.001
                if in_comp['input_volume'] < 0.001:
                    continue
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
    def destination(self):
        """The EpMotion destination tube

        Returns
        -------
        str
        """
        return self._get_attr('destination')

    @property
    # TODO: Someday: Seems suboptimal that this and the code in
    # PoolComposition.components are very similar
    def components(self):
        """The components of the pool

        Returns
        -------
        list of (Composition, float)
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT input_composition_id, input_volume
                     FROM labcontrol.pool_composition_components
                        JOIN labcontrol.pool_composition
                            ON output_pool_composition_id = pool_composition_id
                        JOIN labcontrol.composition USING (composition_id)
                     WHERE upstream_process_id = %s
                     ORDER BY pool_composition_components_id"""
            TRN.add(sql, [self.process_id])
            return [(composition_module.Composition.factory(comp_id), vol)
                    for comp_id, vol in TRN.execute_fetchindex()]

    @property
    def pool(self):
        """The generated pool composition

        Returns
        -------
        PoolComposition
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT composition_id
                     FROM labcontrol.composition
                     WHERE upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return composition_module.Composition.factory(
                TRN.execute_fetchlast())

    @property
    def pooling_function_data(self):
        """The information about the pooling process

        Returns
        -------
        dict
        """
        return self._get_attr('pooling_function_data')

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

        Raises
        ------
        ValueError
            If input and/or output plate has >26 rows
            If volume of any individual input well exceeds the max vol per well
            If more output wells are needed than there are on the output plate
        """

        def get_well_name(offset_from_ascii_ucase_a, col_num):
            if offset_from_ascii_ucase_a > 25:
                raise ValueError("Row letter generation for >26 wells is not "
                                 "supported")  # Recall max # rows = offset + 1
            row_ascii_code = ord('A') + offset_from_ascii_ucase_a
            row_letter = chr(row_ascii_code)
            return "%s%d" % (row_letter, col_num)

        if dest_plate_shape is None:
            dest_plate_shape = [16, 24]

        contents = ['Source Plate Name,Source Plate Type,Source Well,'
                    'Concentration,Transfer Volume,Destination Plate Name,'
                    'Destination Well']
        num_input_rows, num_input_cols = vol_sample.shape
        running_tot = 0
        num_dest_rows = dest_plate_shape[0]
        num_dest_cols = dest_plate_shape[1]
        dest_well_index = 0

        # replace NaN values with 0s to leave a trail of unpooled wells
        pool_vols = np.nan_to_num(vol_sample)

        for curr_input_row_index in range(num_input_rows):
            for curr_input_col_index in range(num_input_cols):
                curr_input_well_name = get_well_name(curr_input_row_index,
                                                     curr_input_col_index + 1)
                curr_input_well_vol = (pool_vols[curr_input_row_index]
                                       [curr_input_col_index])

                # Test to see if the current well volume exceeds the allowed
                # maximum volume per well and if so, error
                if curr_input_well_vol > max_vol_per_well:
                    raise ValueError("Volume {0} in input well {1} exceeds "
                                     "maximum volume per well of "
                                     "{2}".format(curr_input_well_vol,
                                                  curr_input_well_name,
                                                  max_vol_per_well))

                # If adding the current well volume to the current dest well
                # volume would exceed the maximum volume per well, start the
                # next destination well. Otherwise, add the volume of this
                # input well into the current destination well.
                putative_vol = running_tot + curr_input_well_vol
                if putative_vol > max_vol_per_well:
                    dest_well_index += 1
                    running_tot = curr_input_well_vol
                else:
                    running_tot = putative_vol

                # Echo will round the volume anyway, so just give it enough
                # digits to do the correct rounding.
                curr_input_transfer_vol = "%.2f" % curr_input_well_vol

                curr_output_row_offset = int(np.floor(
                    dest_well_index / num_dest_cols))

                # NB: offset should never be as large as number of rows because
                # first row has an offset of 0
                if curr_output_row_offset >= num_dest_rows:
                    raise ValueError("Destination well should be in row {0} "
                                     "but destination plate has only {1} "
                                     "rows".format((curr_output_row_offset+1),
                                                   num_dest_rows))

                curr_output_col_num = (dest_well_index % num_dest_cols) + 1
                curr_dest_well_name = get_well_name(curr_output_row_offset,
                                                    curr_output_col_num)

                curr_output_line = ",".join(
                    ['1', '384LDV_AQ_B2_HT', curr_input_well_name,
                     "", curr_input_transfer_vol,
                     'NormalizedDNA', curr_dest_well_name]
                )
                contents.append(curr_output_line)

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
        return PoolingProcess._format_picklist(vol_sample, max_vol_per_well)

    def generate_epmotion_file(self):
        """Generates an EpMotion file to perform the pooling

        Returns
        -------
        str
            The EpMotion-formatted pool file contents
        """
        contents = ['Rack,Source,Rack,Destination,Volume,Tool']
        destination = self.destination
        for comp, vol in self.components:
            source = comp.container.well_id
            val = "%.3f" % vol
            # Hard-coded values - never changes according to the wet lab
            contents.append(
                ",".join(['1', source, '1', destination, val, '1']))
        # EpMotion-formatted pool files will always be read on a Windows-based
        # PC, in KL. Hence, newlines should be written out as '\r\n'.
        return "\r\n".join(contents)

    def generate_pool_file(self):
        """Generates the correct pool file based on the pool contents

        Returns
        -------
        str
            The contents of the pool file
        """
        component_compositions = [x[0] for x in self.components]
        comp_class = composition_module.PoolComposition\
            .get_components_type(component_compositions)
        if comp_class == composition_module.LibraryPrep16SComposition:
            return self.generate_epmotion_file()
        elif comp_class == composition_module.LibraryPrepShotgunComposition:
            return self.generate_echo_picklist()
        else:
            # This error should only be shown to programmers
            raise ValueError(
                "Can't generate a pooling file for a pool containing "
                "compositions of type: %s" % comp_class)


class SequencingProcess(Process):
    """Sequencing process object

    Attributes
    ----------

    See Also
    --------
    Process
    """
    _table = 'labcontrol.sequencing_process'
    _id_column = 'sequencing_process_id'
    _process_type = 'sequencing'

    _amplicon_assay_type = "Amplicon"
    _metagenomics_assay_type = "Metagenomics"

    sequencer_lanes = {
        'HiSeq4000': 8, 'HiSeq3000': 8, 'HiSeq2500': 2, 'HiSeq1500': 2,
        'MiSeq': 1, 'MiniSeq': 1, 'NextSeq': 1, 'NovaSeq': 1}

    @staticmethod
    def get_controls_prep_sheet_id():
        return "controls"

    @staticmethod
    def list_sequencing_runs():
        """Generates a list of sequencing runs

        Returns
        -------
        list of dicts
            The list of sequence run information with the structure:
            [{'process_id': int, 'run_name': string, ...}]
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT *
                        FROM labcontrol.sequencing_process
                     ORDER BY process_id"""
            TRN.add(sql)
            return [dict(r) for r in TRN.execute_fetchindex()]

    @classmethod
    def create(cls, user, pools, run_name, experiment, sequencer,
               fwd_cycles, rev_cycles, principal_investigator,
               contacts=None):
        """Creates a new sequencing process

        Parameters
        ----------
        user : labcontrol.db.user.User
            User preparing the sequencing
        pools: list of labcontrol.db.composition.PoolComposition
            The pools being sequenced, in lane order
        run_name: str
            The run name
        experiment: str
            The run experiment
        sequencer: labcontrol.db.equipment.Equipment
            The sequencer used
        fwd_cycles : int
            The number of forward cycles
        rev_cycles : int
            The number of reverse cycles
        principal_investigator : labcontrol.db.user.User
            The principal investigator to list in the run
        contacts: list of labcontrol.db.user.User, optinal
            Any additional contacts to add to the Sample Sheet

        Returns
        -------
        SequencingProcess

        Raises
        ------
        ValueError
            If the number of cycles are <= 0
        """
        if fwd_cycles <= 0 or not isinstance(fwd_cycles, int):
            raise ValueError("fwd_cycles must be > 0")
        if rev_cycles <= 0 or not isinstance(rev_cycles, int):
            raise ValueError("rev_cycles must be > 0")

        if len(pools) > cls.sequencer_lanes[sequencer.equipment_type]:
            raise ValueError(
                'Number of pools cannot be bigger than the number of lanes '
                'in the sequencer. Pools: %s. Lanes in a %s sequencer: %s'
                % (len(pools), sequencer.equipment_type,
                   cls.sequencer_lanes[sequencer.equipment_type]))

        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)
            assay = None
            pool = pools[0]
            CM = composition_module
            while assay is None:
                comp = pool.components[0]['composition']
                if isinstance(comp, CM.LibraryPrep16SComposition):
                    assay = SequencingProcess._amplicon_assay_type
                elif isinstance(comp, CM.LibraryPrepShotgunComposition):
                    assay = SequencingProcess._metagenomics_assay_type
                elif isinstance(comp, CM.PoolComposition):
                    pool = comp
                else:
                    # This should never happen - i.e. there is no way
                    # of creating a pool like that
                    raise ValueError(
                        'Pool with unexpected composition type: %s'
                        % comp.__class__.__name__)

            # Add the row to the sequencing table
            sql = """INSERT INTO labcontrol.sequencing_process
                        (process_id, run_name, experiment, sequencer_id,
                         fwd_cycles, rev_cycles, assay, principal_investigator)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                     RETURNING sequencing_process_id"""
            TRN.add(sql, [process_id, run_name, experiment, sequencer.id,
                          fwd_cycles, rev_cycles, assay,
                          principal_investigator.id])
            instance = cls(TRN.execute_fetchlast())

            sql = """INSERT INTO labcontrol.sequencing_process_lanes
                        (sequencing_process_id, pool_composition_id,
                         lane_number)
                     VALUES (%s, %s, %s)"""
            sql_args = [[instance.id, p.id, i + 1]
                        for i, p in enumerate(pools)]
            TRN.add(sql, sql_args, many=True)

            if contacts:
                sql = """INSERT INTO labcontrol.sequencing_process_contacts
                            (sequencing_process_id, contact_id)
                         VALUES (%s, %s)"""
                sql_args = [[instance.id, c.id] for c in contacts]
                TRN.add(sql, sql_args, many=True)
                TRN.execute()

        return instance

    @property
    def pools(self):
        with sql_connection.TRN as TRN:
            sql = """SELECT pool_composition_id, lane_number
                     FROM labcontrol.sequencing_process_lanes
                     WHERE sequencing_process_id = %s
                     ORDER BY lane_number"""
            TRN.add(sql, [self.id])
            res = [[composition_module.PoolComposition(p), l]
                   for p, l in TRN.execute_fetchindex()]
        return res

    @property
    def run_name(self):
        return self._get_attr('run_name')

    @property
    def experiment(self):
        return self._get_attr('experiment')

    @property
    def sequencer(self):
        return equipment_module.Equipment(self._get_attr('sequencer_id'))

    @property
    def include_lane(self):
        # For multi-lane sequencers, include a "Lane" column in sample sheet.
        return self.sequencer_lanes[self.sequencer.equipment_type] > 1

    @property
    def fwd_cycles(self):
        return self._get_attr('fwd_cycles')

    @property
    def rev_cycles(self):
        return self._get_attr('rev_cycles')

    @property
    def is_amplicon_assay(self):
        return self.assay == self._amplicon_assay_type

    @property
    def is_metagenomics_assay(self):
        return self.assay == self._metagenomics_assay_type

    @property
    def assay(self):
        return self._get_attr('assay')

    @property
    def principal_investigator(self):
        return user_module.User(self._get_attr('principal_investigator'))

    @property
    def contacts(self):
        with sql_connection.TRN as TRN:
            sql = """SELECT contact_id
                     FROM labcontrol.sequencing_process_contacts
                     WHERE sequencing_process_id = %s
                     ORDER BY contact_id"""
            TRN.add(sql, [self.id])
            return [user_module.User(r[0]) for r in TRN.execute_fetchindex()]

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
            return [SequencingProcess._reverse_complement(x) for x in indices]
        elif sequencer in other_sequencers:
            return indices
        else:
            raise ValueError(
                'Your indicated sequencer [%s] is not recognized.\nRecognized '
                'sequencers are: \n' %
                ' '.join(revcomp_sequencers + other_sequencers))

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
            'comments': SequencingProcess._format_sample_sheet_comments(
                principal_investigator=principal_investigator,
                contacts=contacts),
            'IEMFileVersion': '4',
            'Investigator Name': self.principal_investigator.name,
            'Experiment Name': self.experiment,
            'Date': datetime.strftime(self.date, Process.get_date_format()),
            'Workflow': 'GenerateFASTQ',
            'Application': 'FASTQ Only',
            'Assay': 'TruSeq HT' if self.is_amplicon_assay else self.assay,
            'Description': '',
            'Chemistry': 'Amplicon' if self.is_amplicon_assay else 'Default',
            'read1': self.fwd_cycles,
            'read2': self.rev_cycles,
            'ReverseComplement': '0',
            'data': data}
        if self.is_amplicon_assay:
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
        ) if self.is_amplicon_assay else (
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

    def _generate_shotgun_sample_sheet(self):
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
                compressed_gdna_composition = libprepshotgun_composition.\
                    normalized_gdna_composition.compressed_gdna_composition
                # Get the well of this component ON THE COMPRESSED GDNA PLATE
                well = compressed_gdna_composition.container
                wells.append(well.well_id)
                # Get the human-readable name of the SAMPLE plate from which
                # this component came
                sample_composition = compressed_gdna_composition.\
                    gdna_composition.sample_composition
                sample_well = sample_composition.container
                sample_plates.append(sample_well.plate.external_id)
                # Get the i7 index information
                i7_comp = libprepshotgun_composition.\
                    i7_composition.primer_set_composition
                i7_names.append(i7_comp.external_id)
                i7_sequences.append(i7_comp.barcode)
                # Get the i5 index information
                i5_comp = libprepshotgun_composition.\
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
                SequencingProcess._bcl_scrub_name(sid) for sid in
                samples_contents]
            bcl2fastq_sample_plates = [
                SequencingProcess._bcl_scrub_name(sid) for sid in
                sample_plates]
            # Reverse the i5 sequences if needed based on the sequencer
            i5_sequences = SequencingProcess._sequencer_i5_index(
                sequencer_type, i5_sequences)

            # Note: laundering arrays into a dataframe and back is not optimal.
            # However, the "parallel arrays" data structure used here would
            # itself make more sense as a dataframe, so it seems undesirable
            # to change _set_control_values_to_plate_value to use arrays.
            plate = "plate"
            proj = "proj"
            plate_proj_df = pd.DataFrame({plate: bcl2fastq_sample_plates,
                                          proj: sample_proj_values})
            adj_plate_proj_df = self._set_control_values_to_plate_value(
                plate_proj_df, plate, proj)
            sample_proj_values = adj_plate_proj_df[proj].tolist()

            # add the data of the current pool
            data.append(SequencingProcess._format_sample_sheet_data(
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
                result = SequencingProcess._folder_scrub_name(result)

        return result

    def _generate_amplicon_sample_sheet(self):
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

    def generate_sample_sheet(self):
        """Generates Illumina compatible sample sheets

        Returns
        -------
        str
            The illumina-formatted sample sheet
        """
        assay = self.assay
        if self.is_amplicon_assay:
            return self._generate_amplicon_sample_sheet()
        elif assay == self._metagenomics_assay_type:
            return self._generate_shotgun_sample_sheet()
        else:
            raise ValueError("Unrecognized assay type: {0}".format(assay))

    def generate_prep_information(self):
        """Generates prep information

        Generates the content for two or more prep information files (at least
        one samples file, as well as one controls file), and returns them all
        within a single dictionary.

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
        if self.is_amplicon_assay:
            return self._generate_amplicon_prep_information()
        elif self.is_metagenomics_assay:
            return self._generate_metagenomics_prep_information()

        raise ValueError("Prep file generation is not implemented for this "
                         "assay type.")

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
                        WHERE sequencing_process_id = %s""", [self.id])

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

    def _generate_amplicon_prep_information(self):
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

            TRN.add(sql, [self.id])
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
                    # not equaling None. This also prevents interference w/the
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

            # the following lines apply for assay == self._amplicon_assay_type
            # when we add shotgun (ToDo: #327), we'll need to modify
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
                    libpreppr.kapa_hyper_plus_kit_id,
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
            TRN.add(sql, [self.id])

            results = [dict(r) for r in TRN.execute_fetchindex()]

            for d in results:
                d['primer_date_i5'] =\
                    d['primer_date_i5'].strftime(Process.get_date_format())
                d['primer_date_i7'] =\
                    d['primer_date_i7'].strftime(Process.get_date_format())

                # instrument_model remains the same across all rows in this
                # query.
                d['instrument_model'] = inst_mdl

                id = d['kapa_hyper_plus_kit_id']
                d['kapa_hyper_plus_kit_lot'] = reagent[id]['external_lot_id']

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

    def _generate_metagenomics_prep_information(self):
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
            prep_sheet =\
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
                  "kapa_hyper_plus_kit_lot": "KapaHyperPlusKit_lot",
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
                SequencingProcess._bcl_scrub_name(id) for id in
                prep_sheet.content]

            prep_sheet['Well_description'] =\
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
                'KapaHyperPlusKit_lot',
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
