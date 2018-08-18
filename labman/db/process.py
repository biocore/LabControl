# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

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
from .study import Study


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
                     FROM labman.process_type
                        JOIN labman.process USING (process_type_id)
                     WHERE process_id = %s"""
            TRN.add(sql, [process_id])
            p_type = TRN.execute_fetchlast()
            constructor = factory_classes[p_type]

            if constructor._table == 'labman.process':
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
        return '%Y-%m-%d %H:%M:%S'

    @classmethod
    def _common_creation_steps(cls, user, process_date=None, notes=None):
        if process_date is None:
            process_date = datetime.now().strftime(cls.get_date_format())

        with sql_connection.TRN as TRN:
            sql = """SELECT process_type_id
                     FROM labman.process_type
                     WHERE description = %s"""
            TRN.add(sql, [cls._process_type])
            pt_id = TRN.execute_fetchlast()

            sql = """INSERT INTO labman.process
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
                     FROM labman.process
                        JOIN {} USING (process_id)
                     WHERE {} = %s""".format(attr, self._table,
                                             self._id_column)
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def date(self):
        # Be very, very careful!  Per the postgresql documentation (see
        # https://www.postgresql.org/docs/9.3/static/datatype-datetime.html
        # section 8.5.1.3. Time Stamps, time stamps with timezone values are
        # "** always converted from UTC to the current timezone
        # zone, and displayed as local time in that zone** [emphasis mine].
        # That is to say, when times are written into a postgres db, they
        # are coerced to the representation that shows what that time would
        # be in the current local time zone setting for the system on which the
        # postgres db is running (yes, really!)
        #
        # That means that if you try to set a timestamp as
        # '2018-01-18 00:00:00-0700', in the database, but you run the code on
        # a computer whose system knows you are in, say, San Diego--where the
        # correct UTC offset in January is actually -8--then the value that
        # will actually be stored in postgres, and the value you get back,
        # will be '2018-01-17 23:00:00-8000'.
        #
        # When comparing actual datetime objects (as long as they are timezone-
        # aware), this isn't a problem--python is smart enough to know that
        # 2018-01-18 00:00:00-0700 and 2018-01-17 23:00:00-0800 both represent
        # the same moment in time.
        #
        # However, when (say) writing the datetime as a string, no such smart
        # reasoning applies.  As long as you are running the system in a single
        # physical location, this shouldn't be a problem--all your times will
        # be as you expect.  But if you import times from ANOTHER location, or
        # if heaven forbid you MOVE from one location to another that is in a
        # different time zone, you could get string representations of dates
        # that are very different than you expected.
        #
        # So, be very, very careful.
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
        plate : list of labman.db.Plate
            The extracted plates
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labman.container
                        LEFT JOIN labman.well USING (container_id)
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
    _table = 'labman.process'
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
                     FROM labman.container
                        LEFT JOIN labman.well USING (container_id)
                        LEFT JOIN labman.plate USING (plate_id)
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
                     FROM labman.tube
                        LEFT JOIN labman.container USING (container_id)
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
    _table = 'labman.primer_working_plate_creation_process'
    _id_column = 'primer_working_plate_creation_process_id'
    _process_type = 'primer working plate creation'

    @classmethod
    def create(cls, user, primer_set, master_set_order, creation_date=None):
        """Creates a new set of working primer plates

        Parameters
        ----------
        user : labman.db.user.User
            User creating the new set of primer plates
        primer_set : labman.composition.PrimerSet
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

            sql = """INSERT INTO labman.primer_working_plate_creation_process
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
    _table = 'labman.gdna_extraction_process'
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
                     FROM labman.composition gc
                        JOIN labman.gdna_composition gdc
                            ON gc.composition_id = gdc.composition_id
                        JOIN labman.sample_composition ssc
                            USING (sample_composition_id)
                        JOIN labman.composition sc
                            ON ssc.composition_id = sc.composition_id
                        JOIN labman.well w
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
                     FROM labman.composition
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
        user : labman.db.user.User
            User performing the gDNA extraction
        plate: labman.db.plate.Plate
            The plate being extracted
        kingfisher: labman.db.equipment.Equipment
            The KingFisher used
        epmotion: labman.db.equipment.Equipment
            The EpMotion used
        epmotion_tool: labman.db.equipment.Equipment
            The EpMotion tool used
        extraciton_kit: labman.db.composition.ReagentComposition
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
            sql = """INSERT INTO labman.gdna_extraction_process
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

    The remapping schema follows this strucutre:
    A B A B A B A B ...
    C D C D C D C D ...
    A B A B A B A B ...
    C D C D C D C D ...
    ...
    """
    _table = 'labman.compression_process'
    _id_column = 'compression_process_id'
    _process_type = "compressed gDNA plates"

    def _compress_plate(self, out_plate, in_plate, row_pad, col_pad, volume=1):
        """Compresses the 96-well in_plate into the 384-well out_plate"""
        with sql_connection.TRN:
            layout = in_plate.layout
            for row in layout:
                for well in row:
                    if well is not None:
                        # The row/col pair is stored in the DB starting at 1
                        # subtract 1 to make it start at 0 so the math works
                        # and re-add 1 at the end
                        out_well_row = (((well.row - 1) * 2) + row_pad) + 1
                        out_well_col = (((well.column - 1) * 2) + col_pad) + 1
                        out_well = container_module.Well.create(
                            out_plate, self, volume, out_well_row,
                            out_well_col)
                        composition_module.CompressedGDNAComposition.create(
                            self, out_well, volume, well.composition)

    @classmethod
    def create(cls, user, plates, plate_ext_id, robot):
        """Creates a new gDNA compression process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the plating
        plates: list of labman.db.plate.Plate
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
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user)

            # Add the row to the compression_process table
            sql = """INSERT INTO labman.compression_process
                        (process_id, robot_id)
                     VALUES (%s, %s)
                     RETURNING compression_process_id"""
            TRN.add(sql, [process_id, robot.id])
            instance = cls(TRN.execute_fetchlast())

            # Create the output plate
            # Magic number 3 -> 384-well plate
            plate = plate_module.Plate.create(
                plate_ext_id, plate_module.PlateConfiguration(3))

            # Compress the plates
            for i, in_plate in enumerate(plates):
                row_pad = int(np.floor(i / 2))
                col_pad = i % 2

                instance._compress_plate(plate, in_plate, row_pad, col_pad)

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
                     FROM labman.composition cc
                        JOIN labman.well cw ON
                            cc.container_id = cw.container_id
                        JOIN labman.compressed_gdna_composition cgc ON
                            cc.composition_id = cgc.composition_id
                        JOIN labman.gdna_composition gdnac ON
                            cgc.gdna_composition_id = gdnac.gdna_composition_id
                        JOIN labman.composition gc ON
                            gdnac.composition_id = gc.composition_id
                        JOIN labman.well gw ON
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
    _table = 'labman.library_prep_16s_process'
    _id_column = 'library_prep_16s_process_id'
    _process_type = '16S library prep'

    @classmethod
    def create(cls, user, plate, primer_plate, lib_plate_name, epmotion,
               epmotion_tool_tm300, epmotion_tool_tm50, master_mix, water_lot,
               volume, preparation_date=None):
        """Creates a new 16S library prep process

        Parameters
        ----------
        user : labman.db.user.User
            User performing the library prep
        plate: labman.db.plate.Plate
            The plate being prepared for amplicon sequencing
        primer_plate: labman.db.plate.Plate
            The primer plate
        lib_plate_name: str
            The name of the prepared plate
        epmotion: labman.db.equipment.Equipment
            The EpMotion
        epmotion_tool_tm300: labman.db.equipment.Equipment
            The EpMotion TM300 8 tool
        epmotion_tool_tm50: labman.db.equipment.Equipment
            The EpMotion TM300 8 tool
        master_mix: labman.db.composition.ReagentComposition
            The mastermix used
        water_lot: labman.db.composition.ReagentComposition
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
            sql = """INSERT INTO labman.library_prep_16s_process
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
                     FROM labman.composition lc
                        JOIN labman.library_prep_16s_composition l16sc
                            ON lc.composition_id = l16sc.composition_id
                        JOIN labman.gdna_composition gdc
                            USING (gdna_composition_id)
                        JOIN labman.composition gc
                            ON gc.composition_id = gdc.composition_id
                        JOIN labman.well w ON gc.container_id = w.container_id
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
                     FROM labman.composition lc
                        JOIN labman.library_prep_16s_composition l16sc
                            ON lc.composition_id = l16sc.composition_id
                        JOIN labman.primer_composition prc
                            USING (primer_composition_id)
                        JOIN labman.composition pc
                            ON pc.composition_id = prc.composition_id
                        JOIN labman.well w ON pc.container_id = w.container_id
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
                     FROM labman.composition
                     WHERE upstream_process_id = %s"""
            TRN.add(sql, [self.process_id])
            return TRN.execute_fetchlast()


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
    _table = 'labman.normalization_process'
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
            func_data = {
                'function': 'default',
                'parameters': {'total_volume': total_vol, 'target_dna': ng,
                               'min_vol': min_vol, 'max_volume': max_vol,
                               'resolution': resolution, 'reformat': reformat}}
            sql = """INSERT INTO labman.normalization_process
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
                     FROM labman.composition nc
                        JOIN labman.normalized_gdna_composition ngc
                            ON nc.composition_id = ngc.composition_id
                        JOIN labman.compressed_gdna_composition cgdnac
                            USING (compressed_gdna_composition_id)
                        JOIN labman.composition cc
                            ON cc.composition_id = cgdnac.composition_id
                        JOIN labman.well w ON cc.container_id = w.container_id
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
            for comp, conc, _ in self.quantification_process.concentrations}
        dna_vols = []
        water_vols = []
        wells = []
        dest_wells = []
        sample_names = []
        dna_concs = []
        layout = self.plates[0].layout
        for row in layout:
            for well in row:
                if well:
                    composition = well.composition
                    dna_vols.append(composition.dna_volume)
                    water_vols.append(composition.water_volume)
                    # For the source well we need to take a look at the
                    # gdna comp
                    c_gdna_comp = composition.compressed_gdna_composition
                    wells.append(c_gdna_comp.container.well_id)
                    dest_wells.append(well.well_id)
                    # For the sample name we need to check the sample
                    # composition
                    sample_comp = c_gdna_comp.gdna_composition.\
                        sample_composition
                    sample_names.append(sample_comp.content)
                    # For the DNA concentrations we need to look at
                    # the quantification process
                    dna_concs.append(concentrations[c_gdna_comp])

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
    _table = 'labman.library_prep_shotgun_process'
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
            sql = """INSERT INTO labman.library_prep_shotgun_process
                        (process_id, kappa_hyper_plus_kit_id, stub_lot_id,
                         normalization_process_id)
                     VALUES (%s, %s, %s, (
                        SELECT DISTINCT normalization_process_id
                            FROM labman.normalization_process np
                                JOIN labman.container c
                                    ON np.process_id =
                                        c.latest_upstream_process_id
                                JOIN labman.well USING (container_id)
                                WHERE plate_id = %s))
                     RETURNING library_prep_shotgun_process_id"""
            TRN.add(sql, [process_id, kappa_hyper_plus_kit.id, stub_lot.id,
                          plate.id])
            instance = cls(TRN.execute_fetchlast())

            # Get the primer set for the plates
            sql = """SELECT DISTINCT shotgun_primer_set_id
                     FROM labman.shotgun_combo_primer_set cps
                        JOIN labman.primer_set_composition psc
                            ON cps.i5_primer_set_composition_id =
                                psc.primer_set_composition_id
                        JOIN labman.primer_composition pc USING
                            (primer_set_composition_id)
                        JOIN labman.composition c
                            ON pc.composition_id = c.composition_id
                        JOIN labman.well USING (container_id)
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

    @property
    def normalized_plate(self):
        """The input normalized plate

        Returns
        -------
        Plate
        """
        with sql_connection.TRN as TRN:
            sql = """SELECT DISTINCT plate_id
                     FROM labman.composition lc
                        JOIN labman.library_prep_shotgun_composition lpsc
                            ON lc.composition_id = lpsc.composition_id
                        JOIN labman.normalized_gdna_composition ngdnac
                            USING (normalized_gdna_composition_id)
                        JOIN labman.composition nc
                            ON ngdnac.composition_id = nc.composition_id
                        JOIN labman.well w ON nc.container_id = w.container_id
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
                     FROM labman.composition lc
                        JOIN labman.library_prep_shotgun_composition lsc
                            ON lc.composition_id = lsc.composition_id
                        JOIN labman.primer_composition prc
                            ON lsc.i5_primer_composition_id =
                                prc.primer_composition_id
                        JOIN labman.composition pc
                            ON prc.composition_id = pc.composition_id
                        JOIN labman.well w ON pc.container_id = w.container_id
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
                     FROM labman.composition lc
                        JOIN labman.library_prep_shotgun_composition lsc
                            ON lc.composition_id = lsc.composition_id
                        JOIN labman.primer_composition prc
                            ON lsc.i7_primer_composition_id =
                                prc.primer_composition_id
                        JOIN labman.composition pc
                            ON prc.composition_id = pc.composition_id
                        JOIN labman.well w ON pc.container_id = w.container_id
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
                     FROM labman.composition
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

    def generate_echo_picklist(self):
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
            if well is None:
                continue
            # Add the sample well
            sample_wells.append(well.well_id)
            # Get the sample name - we need to go back to the SampleComposition
            lib_comp = well.composition
            sample_comp = lib_comp.normalized_gdna_composition\
                .compressed_gdna_composition.gdna_composition\
                .sample_composition
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
    _table = 'labman.quantification_process'
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
        # Plate reader files end with CR; convert to LF
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
        user: labman.db.user.User
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
        user: labman.db.user.User
            User performing the quantification process
        plate: labman.db.plate.Plate
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
        user: labman.db.user.User
            User performing the quantification process
        notes: str
            Description of the quantification process
                (e.g., 'Requantification of failed plate', etc).  May be None.
        concentrations: 2D np.array OR list of dict
            If plate is not None, the plate concentrations as a 2D np.array.
            If plate IS None, the pool component concentrations as a list of
                dicts where each dict is in the form of
                {'composition': Composition,  'concentration': float}
        plate: labman.db.plate.Plate
            The plate being quantified, if relevant. Default: None

        Returns
        -------
        QuantificationProcess
        """
        with sql_connection.TRN as TRN:
            # Add the row to the process table
            process_id = cls._common_creation_steps(user, notes=notes)

            # Add the row to the quantification process table
            sql = """INSERT INTO labman.quantification_process (process_id)
                     VALUES (%s) RETURNING quantification_process_id"""
            TRN.add(sql, [process_id])
            instance = cls(TRN.execute_fetchlast())

            sql = """INSERT INTO labman.concentration_calculation
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
                     FROM labman.concentration_calculation
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
            sql = """UPDATE labman.concentration_calculation
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
    _table = 'labman.pooling_process'
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

        return(pool_vols)

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

        return(adjusted_vols)

    @classmethod
    def create(cls, user, quantification_process, pool_name, volume,
               input_compositions, func_data, robot=None, destination=None):
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
        func_data : dict
            Dictionary with the pooling function information
        robot: labman.equipment.Equipment, optional
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
            sql = """INSERT INTO labman.pooling_process
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
            sql = """INSERT INTO labman.pool_composition_components
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
                     FROM labman.pool_composition_components
                        JOIN labman.pool_composition
                            ON output_pool_composition_id = pool_composition_id
                        JOIN labman.composition USING (composition_id)
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
                     FROM labman.composition
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
        return "\n".join(contents)

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
    _table = 'labman.sequencing_process'
    _id_column = 'sequencing_process_id'
    _process_type = 'sequencing'

    _amplicon_assay_type = "Amplicon"
    _metagenomics_assay_type = "Metagenomics"

    sequencer_lanes = {
        'HiSeq4000': 8, 'HiSeq3000': 8, 'HiSeq2500': 2, 'HiSeq1500': 2,
        'MiSeq': 1, 'MiniSeq': 1, 'NextSeq': 1, 'NovaSeq': 1}

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
                        FROM labman.sequencing_process
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
        user : labman.db.user.User
            User preparing the sequencing
        pools: list of labman.db.composition.PoolComposition
            The pools being sequenced, in lane order
        run_name: str
            The run name
        experiment: str
            The run experiment
        sequencer: labman.db.equipment.Equipment
            The sequencer used
        fwd_cycles : int
            The number of forward cycles
        rev_cycles : int
            The number of reverse cycles
        principal_investigator : labman.db.user.User
            The principal investigator to list in the run
        contacts: list of labman.db.user.User, optinal
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
            sql = """INSERT INTO labman.sequencing_process
                        (process_id, run_name, experiment, sequencer_id,
                         fwd_cycles, rev_cycles, assay, principal_investigator)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                     RETURNING sequencing_process_id"""
            TRN.add(sql, [process_id, run_name, experiment, sequencer.id,
                          fwd_cycles, rev_cycles, assay,
                          principal_investigator.id])
            instance = cls(TRN.execute_fetchlast())

            sql = """INSERT INTO labman.sequencing_process_lanes
                        (sequencing_process_id, pool_composition_id,
                         lane_number)
                     VALUES (%s, %s, %s)"""
            sql_args = [[instance.id, p.id, i + 1]
                        for i, p in enumerate(pools)]
            TRN.add(sql, sql_args, many=True)

            if contacts:
                sql = """INSERT INTO labman.sequencing_process_contacts
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
                     FROM labman.sequencing_process_lanes
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
    def assay(self):
        return self._get_attr('assay')

    @property
    def principal_investigator(self):
        return user_module.User(self._get_attr('principal_investigator'))

    @property
    def contacts(self):
        with sql_connection.TRN as TRN:
            sql = """SELECT contact_id
                     FROM labman.sequencing_process_contacts
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
        return re.sub('[^0-9a-zA-Z\-\_]+', '_', name)

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
            return([SequencingProcess._reverse_complement(x) for x in indices])
        elif sequencer in other_sequencers:
            return(indices)
        else:
            raise ValueError(
                'Your indicated sequencer [%s] is not recognized.\nRecognized '
                'sequencers are: \n' %
                ' '.join(revcomp_sequencers + other_sequencers))

    @staticmethod
    def _format_sample_sheet_data(sample_ids, i7_name, i7_seq, i5_name, i5_seq,
                                  sample_projs, wells=None, sample_plates=None,
                                  description=None, lanes=[1], sep=',',
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
            The source sample wells, in sample_ids order. Default: None
        sample_plate: str, optional
            The plate name. Default: ''
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
        is_amplicon = self.assay == self._amplicon_assay_type
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
            'Assay': 'TruSeq HT' if is_amplicon else self.assay,
            'Description': '',
            'Chemistry': 'Amplicon' if is_amplicon else 'Default',
            'read1': self.fwd_cycles,
            'read2': self.rev_cycles,
            'ReverseComplement': '0',
            'data': data}
        if is_amplicon:
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
        ) if is_amplicon else (
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
                lp_composition = component['composition']
                # Get the well information
                well = lp_composition.container
                wells.append(well.well_id)
                # Get the plate information
                sample_plates.append(well.plate.external_id)
                # Get the i7 index information
                i7_comp = lp_composition.i7_composition.primer_set_composition
                i7_names.append(i7_comp.external_id)
                i7_sequences.append(i7_comp.barcode)
                # Get the i5 index information
                i5_comp = lp_composition.i5_composition.primer_set_composition
                i5_names.append(i5_comp.external_id)
                i5_sequences.append(i5_comp.barcode)

                # Get the sample content (used as description)
                sample_content = lp_composition.normalized_gdna_composition.\
                    compressed_gdna_composition.gdna_composition.\
                    sample_composition.content
                # sample_content is the labman.sample_composition.content
                # value, which is the "true" sample_id plus a "." plus the
                # plate id of the plate on which the sample was plated, plus
                # another "." and the well (e.g., "A1") into which the sample
                # was plated on that plate.
                samples_contents.append(sample_content)

                true_sample_id = lp_composition.normalized_gdna_composition.\
                    compressed_gdna_composition.gdna_composition.\
                    sample_composition.sample_id
                sample_proj_values.append(self._generate_sample_proj_value(
                    true_sample_id))
            # Transform the sample ids to be bcl2fastq-compatible
            bcl2fastq_sample_ids = [
                SequencingProcess._bcl_scrub_name(sid) for sid in
                samples_contents]
            # Reverse the i5 sequences if needed based on the sequencer
            i5_sequences = SequencingProcess._sequencer_i5_index(
                sequencer_type, i5_sequences)
            # add the data of the current pool
            data.append(SequencingProcess._format_sample_sheet_data(
                bcl2fastq_sample_ids, i7_names, i7_sequences, i5_names,
                i5_sequences, sample_proj_values, wells=wells,
                sample_plates=sample_plates, description=samples_contents,
                lanes=[lane], sep=',', include_header=include_header,
                include_lane=self.include_lane))
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
        sample_id : str
            The value of the sample_id column from qiita.study_sample for the
            sample of interest. For samples with no sample_id (e.g., controls,
            blanks, empties), the value is "Controls".

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

        if result is None:
            # usually this is because the sample_id was not found in
            # study_sample because it is not an experimental sample but rather
            # a blank or an empty or a control.
            # TODO: Probably worth checking if the sample IS experimental
            # because if it IS and we got None, something is profoundly wrong.
            result = "Controls"

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
        if assay == self._amplicon_assay_type:
            return self._generate_amplicon_sample_sheet()
        elif assay == self._metagenomics_assay_type:
            return self._generate_shotgun_sample_sheet()
        else:
            raise ValueError("Unrecognized assay type: {0}".format(assay))

    def generate_prep_information(self):
        """Generates prep information

        Returns
        -------
        dict labman.db.study.Study: str
            a dict of the Study and the prep
        """
        assay = self.assay
        data = {}
        blanks = {}
        if assay == self._amplicon_assay_type:
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
                SELECT study_id, sample_id, content, run_name, experiment,
                       fwd_cycles, rev_cycles, principal_investigator,
                       et.description as sequencer_description,
                       lpp.epmotion_robot_id as lepmotion_robot_id,
                       epmotion_tm300_8_tool_id, epmotion_tm50_8_tool_id,
                       master_mix_id, water_lot_id,
                       gep.epmotion_robot_id as gepmotion_robot_id,
                       epmotion_tool_id, kingfisher_robot_id,
                       extraction_kit_id,
                       p1.external_id as plate, w1.row_num as row_num,
                       w1.col_num as col_num,
                       p2.external_id as primer_composition,
                       psc.barcode_seq as primer_set_composition,
                       run_name as run_prefix, sp.sequencer_id as platform_id,
                       sp.experiment as center_project_name
                -- Retrieve sequencing information
                FROM labman.sequencing_process sp
                LEFT JOIN labman.equipment e ON (
                    sequencer_id = equipment_id)
                LEFT JOIN labman.equipment_type et ON (
                    et.equipment_type_id = e.equipment_type_id)
                LEFT JOIN labman.sequencing_process_lanes spl USING (
                    sequencing_process_id)
                -- Retrieve pooling information
                LEFT JOIN labman.pool_composition_components pcc1 ON (
                    pcc1.output_pool_composition_id = spl.pool_composition_id)
                LEFT JOIN labman.pool_composition pccon ON (
                    pcc1.input_composition_id = pccon.composition_id)
                 LEFT JOIN labman.pool_composition_components pcc2 ON (
                    pccon.pool_composition_id =
                    pcc2.output_pool_composition_id)
                -- Retrieve amplicon library prep information
                LEFT JOIN labman.library_prep_16s_composition lp ON (
                    pcc2.input_composition_id = lp.composition_id)
                LEFT JOIN labman.composition c1 ON (
                    lp.composition_id = c1.composition_id)
                LEFT JOIN labman.library_prep_16s_process lpp ON (
                    lpp.process_id = c1.upstream_process_id)
                -- Retrieve the extracted gdna information
                LEFT JOIN labman.gdna_composition gc
                    USING (gdna_composition_id)
                LEFT JOIN labman.composition c2 ON (
                    gc.composition_id = c2.composition_id)
                LEFT JOIN labman.gdna_extraction_process gep ON (
                    gep.process_id = c2.upstream_process_id)
                -- Retrieve the sample information
                LEFT JOIN labman.sample_composition sc USING (
                    sample_composition_id)
                LEFT JOIN labman.composition c3 ON (
                    c3.composition_id = sc.composition_id)
                LEFT JOIN labman.well w1 ON (
                    w1.container_id = c3.container_id)
                LEFT JOIN labman.plate p1 ON (
                    w1.plate_id = p1.plate_id)
                LEFT JOIN labman.composition c4 ON (
                    lp.primer_composition_id = c4.composition_id
                )
                LEFT JOIN labman.well w2 ON (
                    w2.container_id = c4.container_id)
                LEFT JOIN labman.plate p2 ON (
                    w2.plate_id = p2.plate_id)
                LEFT JOIN labman.primer_composition pc ON (
                    lp.primer_composition_id = pc.primer_composition_id)
                LEFT JOIN labman.primer_set_composition psc ON (
                    pc.primer_set_composition_id =
                    psc.primer_set_composition_id)
                FULL JOIN qiita.study_sample USING (sample_id)
                WHERE sequencing_process_id = %s
                ORDER BY study_id, sample_id, row_num, col_num"""
        elif assay == self._metagenomics_assay_type:
            extra_fields = [
                ('e', 'gepmotion_robot_id', 'gdata_robot'),
                ('e', 'epmotion_tool_id', 'epmotion_tool'),
                ('e', 'kingfisher_robot_id', 'kingfisher_robot'),
                ('r', 'kappa_hyper_plus_kit_id', 'kappa_hyper_plus_kit'),
                ('r', 'stub_lot_id', 'stub_lot'),
                ('r', 'extraction_kit_id', 'extraction_kit'),
                ('r', 'nwater_lot_id', 'normalization_water_lot'),
            ]
            sql = """
                SELECT study_id, sample_id, content, run_name, experiment,
                       fwd_cycles, rev_cycles, principal_investigator,
                       i5.barcode_seq as i5_sequence,
                       i7.barcode_seq as i5_sequence,
                       et.description as sequencer_description,
                       gep.epmotion_robot_id as gepmotion_robot_id,
                       epmotion_tool_id, kingfisher_robot_id,
                       extraction_kit_id, np.water_lot_id as nwater_lot_id,
                       kappa_hyper_plus_kit_id, stub_lot_id,
                       p1.external_id as plate, row_num, col_num,
                       sp.sequencer_id as platform_id,
                       sp.experiment as center_project_name
                -- Retrieve sequencing information
                FROM labman.sequencing_process sp
                LEFT JOIN labman.equipment e ON (
                    sequencer_id = equipment_id)
                LEFT JOIN labman.equipment_type et ON (
                    et.equipment_type_id = e.equipment_type_id)
                LEFT JOIN labman.sequencing_process_lanes USING (
                    sequencing_process_id)
                -- Retrieving pool information
                LEFT JOIN labman.pool_composition_components ON (
                    output_pool_composition_id = pool_composition_id)
                -- Retrieving library prep information
                LEFT JOIN labman.library_prep_shotgun_composition ON (
                    input_composition_id = composition_id)
                LEFT JOIN labman.primer_composition i5pc ON (
                    i5_primer_composition_id = i5pc.primer_composition_id)
                LEFT JOIN labman.primer_set_composition i5 ON (
                    i5pc.primer_set_composition_id =
                    i5.primer_set_composition_id
                )
                LEFT JOIN labman.primer_composition i7pc ON (
                    i7_primer_composition_id = i7pc.primer_composition_id)
                LEFT JOIN labman.primer_set_composition i7 ON (
                    i7pc.primer_set_composition_id =
                    i7.primer_set_composition_id
                )
                -- Retrieving normalized gdna information
                LEFT JOIN labman.normalized_gdna_composition ngc USING (
                    normalized_gdna_composition_id)
                LEFT JOIN labman.composition c1 ON (
                    ngc.composition_id = c1.composition_id)
                LEFT JOIN labman.library_prep_shotgun_process lps ON (
                    lps.process_id = c1.upstream_process_id)
                LEFT JOIN labman.normalization_process np USING (
                    normalization_process_id)
                -- Retrieving compressed gdna information
                LEFT JOIN labman.compressed_gdna_composition cgc USING (
                    compressed_gdna_composition_id)
                -- Retrieving gdna information
                LEFT JOIN labman.gdna_composition gc
                    USING (gdna_composition_id)
                LEFT JOIN labman.composition c2 ON (
                    gc.composition_id = c2.composition_id)
                LEFT JOIN labman.gdna_extraction_process gep ON (
                    gep.process_id = c2.upstream_process_id)
                LEFT JOIN labman.sample_composition sc USING (
                    sample_composition_id)
                LEFT JOIN labman.composition c3 ON (
                    c3.composition_id = sc.composition_id)
                LEFT JOIN labman.well w1 ON (
                    w1.container_id = c3.container_id)
                LEFT JOIN labman.plate p1 ON (
                    w1.plate_id = p1.plate_id)
                FULL JOIN qiita.study_sample USING (sample_id)
                WHERE sequencing_process_id = %s
                ORDER BY study_id, sample_id, row_num, col_num, i5.barcode_seq
                """

        with sql_connection.TRN as TRN:
            # to simplify the main queries, let's get all the equipment info
            TRN.add("""SELECT equipment_id, external_id, notes, description
                       FROM labman.equipment
                       LEFT JOIN labman.equipment_type
                       USING (equipment_type_id)""")
            equipment = {}
            for row in TRN.execute_fetchindex():
                row = dict(row)
                eid = row.pop('equipment_id')
                equipment[eid] = row

            # and the reagents
            TRN.add("""SELECT reagent_composition_id, composition_id,
                           external_lot_id, description
                       FROM labman.reagent_composition
                       LEFT JOIN labman.reagent_composition_type
                       USING (reagent_composition_type_id)""")
            reagent = {}
            for row in TRN.execute_fetchindex():
                row = dict(row)
                rid = row.pop('reagent_composition_id')
                reagent[rid] = row

            TRN.add(sql, [self.id])
            for result in TRN.execute_fetchindex():
                result = dict(result)
                study_id = result.pop('study_id')
                sid = result.pop('sample_id')
                content = result.pop('content')

                # format well
                col = result.pop('col_num')
                row = result.pop('row_num')
                well = []
                while row:
                    row, rem = divmod(row-1, 26)
                    well[:0] = container_module.LETTERS[rem]
                result['well'] = ''.join(well) + str(col)

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
                result['platform'] = equipment[
                    result.pop('platform_id')]['description']

                if sid is not None and study_id is not None:
                    study = Study(study_id)
                    if study not in data:
                        data[study] = {}
                    data[study][content] = result

                    if assay == self._metagenomics_assay_type:
                        result['run_prefix'] = \
                            SequencingProcess._bcl_scrub_name(content)
                else:
                    if assay == self._metagenomics_assay_type:
                        result['run_prefix'] = \
                            SequencingProcess._bcl_scrub_name(content)
                    blanks[content] = result

        # converting from dict to pandas and then to tsv
        for study, vals in data.items():
            merged = {**vals, **blanks}
            df = pd.DataFrame.from_dict(merged, orient='index')
            df.sort_index(inplace=True)
            cols = sorted(list(df.columns))
            sio = StringIO()
            df[cols].to_csv(sio, sep='\t', index_label='sample_name')
            data[study] = sio.getvalue()

        return data
