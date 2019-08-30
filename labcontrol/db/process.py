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

from . import sheet as sheet_module


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
    kit_type
    kit_lot_id
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
    # TODO 503 add kit_type to creation (Charlie)
    def create(cls, user, plate, plate_name, kit_type, kit_lot_id, stub_lot,
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
        kit_type: str
            The type of the kit used
        kit_lot_id: labcontrol.db.composition.ReagentComposition
            The lot ID for the kit used
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
                        (process_id, kapa_hyperplus_kit_id, stub_lot_id,
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
            TRN.add(sql, [process_id, kit_lot_id.id, stub_lot.id,
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

    # TODO 503 make the actual getter for kit_type (Charlie)
    @property
    def kit_type(self):
        """The type of prep kit used

        Returns
        -------
         # TODO 503 or something like it. it looks like backend may
        already be supported via `reagent_composition_type`
        """
        return 'KAPA HyperPlus kit'

    @property
    def shotgun_library_prep_kit(self):
        """The shotgun library prep kit used

        Returns
        -------
        ReagentComposition
        """
        # TODO 503 I beleive this gets this attribute from the underlying
        #  table, this will need reflect whatever the attribute for
        #  kit_lot_id in the table is (if refactored in the future)
        return composition_module.ReagentComposition(
            self._get_attr('kapa_hyperplus_kit_id'))

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
            sql = """INSERT INTO labcontrol.sequencing_process
                        (process_id, run_name, experiment, sequencer_id,
                         fwd_cycles, rev_cycles, principal_investigator)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)
                     RETURNING sequencing_process_id"""

            TRN.add(sql, [process_id, run_name, experiment, sequencer.id,
                          fwd_cycles, rev_cycles, principal_investigator.id])
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

    def generate_sample_sheet(self):
        """Generates Illumina compatible sample sheets

        Returns
        -------
        str
            The illumina-formatted sample sheet
        """
        pool_comp = composition_module.PoolComposition
        assay_type = pool_comp.get_assay_type_for_sequencing_process(self.id)

        params = {'include_lane': self.include_lane,
                  'pools': self.pools,
                  'principal_investigator': self.principal_investigator,
                  'contacts': self.contacts,
                  'experiment': self.experiment,
                  'date': self.date,
                  'fwd_cycles': self.fwd_cycles,
                  'rev_cycles': self.rev_cycles,
                  'run_name': self.run_name,
                  'sequencer': self.sequencer,
                  'sequencing_process_id': self.id,
                  'assay_type': assay_type}

        sheet = sheet_module.SampleSheet.factory(**params)

        return sheet.generate()

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
        pool_comp = composition_module.PoolComposition
        assay_type = pool_comp.get_assay_type_for_sequencing_process(self.id)

        params = {'include_lane': self.include_lane,
                  'pools': self.pools,
                  'principal_investigator': self.principal_investigator,
                  'contacts': self.contacts,
                  'experiment': self.experiment,
                  'date': self.date,
                  'fwd_cycles': self.fwd_cycles,
                  'rev_cycles': self.rev_cycles,
                  'run_name': self.run_name,
                  'sequencer': self.sequencer,
                  'sequencing_process_id': self.id,
                  'assay_type': assay_type}

        # pass the vital data from SequencingProcess to the Sheet factory in
        # params, and let the factory pass it to the correct PrepInfoSheet
        # subclass, using self.assay_type as the determinator.
        # SequencingProcess no longer needs to know about mapping assay_types
        # or mapping them to Sheet types; that information is held w/in Sheets.
        # The params dictionary allows for passing of whatever parameters this
        # class can pass, and a given Sheet class can simply ignore the ones it
        # doesn't need. Assume for now that Sheets will not alter data.
        sheet = sheet_module.PrepInfoSheet.factory(**params)

        return sheet.generate()
