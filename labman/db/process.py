# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.base import LabmanObject
from labman.db.sql_connection import TRN
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition, PrimerSet


class _Process(LabmanObject):
    """Base process object

    Attributes
    ----------
    id
    date
    personnel
    """

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
        with TRN:
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


class Process(_Process):
    """Process object

    Not all processes have a specific subclass, so we need to override the
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
        return self._get_attr('run_personnel_id')


class PrimerWorkingPlateCreationProcess(_Process):
    """Primer working plate creation process object

    Attributes
    ----------
    primer_set
    master_set_order_number
    """
    @property
    def primer_set(self):
        """The primer set template from which the working plates are created

        Returns
        -------
        PrimerSet
        """
        return PrimerSet(self._get_attr('primer_set_id'))

    @property
    def master_set_order(self):
        """The master set order

        Returns
        -------
        str
        """
        return self._get_attr('master_set_order_number')


class GDNAExtractionProcess(_Process):
    """gDNA extraction process object

    Attributes
    ----------
    robot
    kit
    tool

    See Also
    --------
    _Process
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
        return Equipment(self._get_attr('extraction_robot_id'))

    @property
    def kit(self):
        """The kit used during extraction

        Returns
        -------
        ReagentComposition
        """
        return ReagentComposition(self._get_attr('extraction_kit_id'))

    @property
    def tool(self):
        """The tool used during extraction

        Returns
        -------
        Equipment
        """
        return Equipment(self._get_attr('extraction_tool_id'))


class LibraryPrep16SProcess(_Process):
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
    _Process
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
        return ReagentComposition(self._get_attr('master_mix_id'))

    @property
    def tm300_8_tool(self):
        """The tm300_8 tool used

        Returns
        -------
        Equipment
        """
        return Equipment(self._get_attr('tm300_8_tool_id'))

    @property
    def tm50_8_tool(self):
        """The tm50_8 tool used

        Returns
        -------
        Equipment
        """
        return Equipment(self._get_attr('tm50_8_tool_id'))

    @property
    def water_lot(self):
        """The water lot used

        Returns
        -------
        ReagentComposition
        """
        return ReagentComposition(self._get_attr('water_id'))

    @property
    def processing_robot(self):
        """The processing robot used

        Returns
        -------
        Equipment
        """
        return Equipment(self._get_attr('processing_robot_id'))


class NormalizationProcess(_Process):
    """Normalization process object

    Attributes
    ----------
    quantification_process
    water_lot

    See Also
    --------
    _Process
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
        return ReagentComposition(self._get_attr('water_lot_id'))


class LibraryPrepShotgunProcess(_Process):
    """Shotgun Library Prep process object

    Attributes
    ----------
    kappa_hyper_plus_kit
    stub_lot
    normalization_process

    See Also
    --------
    _Process
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
        return ReagentComposition(self._get_attr('kappa_hyper_plus_kit_id'))

    @property
    def stub_lot(self):
        """The stub lot used

        Returns
        -------
        ReagentComposition
        """
        return ReagentComposition(self._get_attr('stub_lot_id'))

    @property
    def normalization_process(self):
        """The normalization process used

        Returns
        -------
        NormalizationProcess
        """
        return NormalizationProcess(self._get_attr('normalization_process_id'))


class QuantificationProcess(_Process):
    """Quantification process object

    Attributes
    ----------
    concentrations

    See Also
    --------
    _Process
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
        with TRN:
            sql = """SELECT quantitated_composition_id, raw_concentration
                     FROM qiita.concentration_calculation
                     WHERE upstream_process_id = %s
                     ORDER BY concentration_calculation_id"""
            TRN.add(sql, [self._id])
            # TODO: return the Composition object rather than the ID
            return [(comp_id, raw_con)
                    for comp_id, raw_con in TRN.execute_fetchindex()]


class PoolingProcess(_Process):
    """Pooling process object

    Attributes
    ----------
    quantification_process
    robot

    See Also
    --------
    _Process
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
        return Equipment(self._get_attr('robot_id'))
