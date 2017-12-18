# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import base
from . import sql_connection
from . import process
from . import container as container_mod


class Composition(base.LabmanObject):
    """Composition object

    Attributes
    ----------
    id
    upstream_process
    container
    total_volume
    notes
    """
    @staticmethod
    def factory(composition_id):
        """Initializes the correct composition subclass

        Parameters
        ----------
        composition_id : int
            The composition id

        Returns
        -------
        An instance of a subclass of Composition
        """
        factory_classes = {
            'reagent': ReagentComposition,
            'primer set': PrimerSetComposition,
            'primer': PrimerComposition,
            'sample': SampleComposition,
            'gDNA': GDNAComposition,
            '16S library prep': LibraryPrep16SComposition,
            'normalized gDNA': NormalizedGDNAComposition,
            'shotgun library prep': LibraryPrepShotgunComposition,
            'pool': PoolComposition}

        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM qiita.composition_type
                        JOIN qiita.composition USING (composition_type_id)
                     WHERE composition_id = %s"""
            TRN.add(sql, [composition_id])
            c_type = TRN.execute_fetchlast()
            constructor = factory_classes[c_type]

            sql = """SELECT {}
                     FROM {}
                     WHERE composition_id = %s""".format(
                        constructor._id_column, constructor._table)
            TRN.add(sql, [composition_id])
            subclass_id = TRN.execute_fetchlast()
            instance = constructor(subclass_id)

        return instance

    @classmethod
    def _common_creation_steps(cls, process, container, volume):
        """"""
        with sql_connection.TRN as TRN:
            sql = """SELECT composition_type_id
                     FROM qiita.composition_type
                     WHERE description = %s"""
            TRN.add(sql, [cls._composition_type])
            ct_id = TRN.execute_fetchlast()

            sql = """INSERT INTO qiita.composition
                        (composition_type_id, upstream_process_id,
                         container_id, total_volume)
                     VALUES (%s, %s, %s, %s)
                     RETURNING composition_id"""
            TRN.add(sql, [ct_id, process.process_id, container.container_id,
                          volume])
            composition_id = TRN.execute_fetchlast()
        return composition_id

    def _get_composition_attr(self, attr):
        """Returns the value of the given composition attribute

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
                     FROM qiita.composition
                        JOIN {} USING (composition_id)
                     WHERE {} = %s""".format(attr, self._table,
                                             self._id_column)
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def upstream_process(self):
        """The last process applied to the composition"""
        return process.Process.factory(
            self._get_composition_attr('upstream_process_id'))

    @property
    def container(self):
        """The container where the composition is stored"""
        return container_mod.Container.factory(
            self._get_composition_attr('container_id'))

    @property
    def total_volume(self):
        """The composition total volume"""
        return self._get_composition_attr('total_volume')

    @property
    def notes(self):
        """The composition notes"""
        return self._get_composition_attr('notes')


class ReagentComposition(Composition):
    """Reagent composition class

    Attributes
    ----------
    external_lot_id
    reagent_type

    See Also
    --------
    Composition
    """
    _table = 'qiita.reagent_composition'
    _id_column = 'reagent_composition_id'
    _composition_type = 'reagent'

    @classmethod
    def create(cls, process, container, volume, reagent_type, external_lot_id):
        """Creates a new reagent composition

        Parameters
        ----------
        process : labman.db.process.Process
            The process that created the reagents
        container: labman.db.container.Container
            The container where the composition is stored
        volume: float
            The composition volume
        reagent_type: string
            The reagent type
        external_lot_id : str
            The external lot id

        Returns
        -------
        labman.db.composition.ReagentComposition
        """
        with sql_connection.TRN as TRN:
            # Add the row into the composition table
            composition_id = cls._common_creation_steps(
                process, container, volume)
            # Get the reagent composition type
            sql = """SELECT reagent_composition_type_id
                     FROM qiita.reagent_composition_type
                     WHERE description = %s"""
            TRN.add(sql, [reagent_type])
            rct_id = TRN.execute_fetchlast()

            # Add the row into the reagent composition table
            sql = """INSERT INTO qiita.reagent_composition
                        (composition_id, reagent_composition_type_id,
                         external_lot_id)
                     VALUES (%s, %s, %s)
                     RETURNING reagent_composition_id"""
            TRN.add(sql, [composition_id, rct_id, external_lot_id])
            rc_id = TRN.execute_fetchlast()
        return cls(rc_id)

    @property
    def external_lot_id(self):
        """The external lot id of the reagent"""
        return self._get_attr('external_lot_id')

    @property
    def reagent_type(self):
        """The reagent type"""
        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM qiita.reagent_composition_type
                        JOIN qiita.reagent_composition
                            USING (reagent_composition_type_id)
                     WHERE reagent_composition_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()


class PrimerComposition(Composition):
    """Primer composition class

    See Also
    --------
    Composition
    """
    # TODO: I'm still a bit confused on how the Primer Compositions work around
    # So I'm not sure how this class should look like
    pass


class PrimerSetComposition(Composition):
    """Primer set composition class

    See Also
    --------
    Composition
    """


class SampleComposition(Composition):
    """Sample composition class

    Attributes
    ----------
    content_id
    content_type

    See Also
    --------
    Composition
    """
    _table = 'qiita.sample_composition'
    _id_column = 'sample_composition_id'
    _composition_type = 'sample'

    @classmethod
    def create(cls, process, container, volume, sample_id=None, control=None):
        """"""
        if sample_id is None and control is None:
            # Raise an error if neither sample ID or control are provided
            raise ValueError("")
        elif sample_id is not None and control is not None:
            # Raise an error if both sample ID and control are provided
            raise ValueError("")
        elif sample_id is not None:
            # If sample_id is provided, then the sample_composition_type
            # is 'experimental sample'
            sct_string = 'experimental sample'
        else:
            # The only remaining case is sample id is not provided and control
            # is provided. In this case, the sample_composition_type is the
            # control itself
            sct_string = control

        with sql_connection.TRN as TRN:
            # Add the row into the composition table
            composition_id = cls._common_creation_steps(process, container,
                                                        volume)

            # Get the sample composition type id
            sql = """SELECT sample_composition_type_id
                     FROM qiita.sample_composition_type
                     WHERE description = %s"""
            TRN.add(sql, [sct_string])
            sct_id = TRN.execute_fetchlast()

            # Add the row into the sample composition table
            sql = """INSERT INTO qiita.sample_composition
                        (composition_id, sample_composition_type_id, sample_id)
                     VALUES (%s, %s, %s)
                     RETURNING sample_composition_id"""
            TRN.add(sql, [composition_id, sct_id, sample_id])
            sc_id = TRN.execute_fetchlast()
        return cls(sc_id)

    @property
    def sample_id(self):
        """The sample id"""
        return self._get_attr('sample_id')

    @property
    def sample_composition_type(self):
        """The content type"""
        with sql_connection.TRN as TRN:
            sql = """SELECT description
                     FROM qiita.sample_composition_type
                        JOIN qiita.sample_composition
                            USING (sample_composition_type_id)
                     WHERE sample_composition_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()


class GDNAComposition(Composition):
    """gDNA composition class

    Attributes
    ----------
    sample_composition

    See Also
    --------
    Composition
    """
    _table = 'qiita.gdna_composition'
    _id_column = 'gdna_composition_id'

    @classmethod
    def create(cls, process, container, volume, sample_composition):
        """Creates a new gDNA composition

        Parameters
        ----------
        process: labman.db.process.Process
            The process creating the gDNA composition
        container: labman.db.container.Container
            The container with the composition
        volume: float
            The initial volume
        sample_composition: labman.db.composition.SampleComposition
            The origin sample composition the new gDNA composition has been
            derived from
        """
        with sql_connection.TRN as TRN:
            # Add the row into the composition table
            composition_id = cls._common_creation_steps(process, container,
                                                        volume)
            # Add the row into the gdna composition table
            sql = """INSERT INTO qiita.gdna_composition
                        (composition_id, sample_composition_id)
                     VALUES (%s, %s)
                     RETURNING gdna_composition_id"""
            TRN.add(sql, [composition_id, sample_composition.id])
            gdnac_id = TRN.execute_fetchlast()
        return cls(gdnac_id)

    @property
    def sample_composition(self):
        return SampleComposition(self._get_attr('sample_composition_id'))


class LibraryPrep16SComposition(Composition):
    """16S Library Preparation composition class

    Attributes
    ----------
    gdna_composition
    primer_composition

    See Also
    --------
    Composition
    """
    _table = 'qiita.library_prep_16s_composition'
    _id_column = 'library_prep_16s_composition_id'

    @property
    def gdna_composition(self):
        return GDNAComposition(self._get_attr('gdna_composition_id'))

    @property
    def primer_composition(self):
        return PrimerComposition(self._get_attr('primer_composition_id'))


class NormalizedGDNAComposition(Composition):
    """Normalized gDNA composition class

    Attributes
    ----------
    gdna_composition

    See Also
    --------
    Composition
    """
    _table = 'qiita.normalized_gdna_composition'
    _id_column = 'normalized_gdna_composition_id'

    @property
    def gdna_composition(self):
        return GDNAComposition(self._get_attr('gdna_composition_id'))


class LibraryPrepShotgunComposition(Composition):
    """Shotgun Library Preparation composition class

    Attributes
    ----------
    normalized_gdna_composition
    i5_composition
    i7_composition

    See Also
    --------
    Composition
    """
    _table = 'qiita.library_prep_shotgun_composition'
    _id_column = 'library_prep_shotgun_composition_id'

    @property
    def normalized_gdna_composition(self):
        return NormalizedGDNAComposition(
            self._get_attr('normalized_gdna_composition'))

    @property
    def i5_composition(self):
        return PrimerComposition(self._get_attr('i5_primer_composition_id'))

    @property
    def i7_composition(self):
        return PrimerComposition(self._get_attr('i7_primer_composition_id'))


class PoolComposition(Composition):
    """Pool composition class

    Attributes
    ----------
    components

    See Also
    --------
    Composition
    """
    _table = 'qiita.pool_composition'
    _id_column = 'pool_composition_id'

    @property
    def components(self):
        with sql_connection.TRN as TRN:
            sql = """SELECT input_compostion_id, input_volume as volume,
                            percentage_of_output as percentage
                     FROM qiita.pool_composition_components
                     WHERE output_pool_composition_id = %s"""
            TRN.add(sql, [self.id])
            # TODO: return the correct composition type instead of the ID
            return TRN.execute_fetchindex()


class PrimerSet(base.LabmanObject):
    """Primer set class

    Attributes
    ----------
    external_id
    target_name
    notes
    """
    _table = 'qiita.primer_set'
    _id_column = 'primer_set_id'

    @property
    def external_id(self):
        return self._get_attr('external_id')

    @property
    def target_name(self):
        return self._get_attr('target_name')

    @property
    def notes(self):
        return self._get_attr('notes')
