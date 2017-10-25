# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from labman.db.base import LabmanObject
from labman.db.sql_connection import TRN


class _Composition(LabmanObject):
    """Composition object

    Attributes
    ----------
    id
    upstream_process
    container
    total_volume
    notes
    """
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
        with TRN:
            sql = """SELECT {}
                     FROM qiita.composition
                        JOIN {} USING composition_id
                     WHERE {} = %s""".format(attr, self._table,
                                             self._id_column)
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()

    @property
    def upstream_process(self):
        """The last process applied to the composition"""
        # TODO return the correct process, not the id
        return self._get_composition_attr('upstream_process_id')

    @property
    def container(self):
        """The container where the composition is stored"""
        # TODO return the correct container, not the id
        return self._get_composition_attr('container_id')

    @property
    def total_volume(self):
        """The composition total volume"""
        return self._get_composition_attr('total_volume')

    @property
    def notes(self):
        """The composition notes"""
        return self._get_composition_attr('notes')


class ReagentComposition(_Composition):
    """Reagent composition class

    Attributes
    ----------
    external_lot_id
    reagent_type

    See Also
    --------
    _Composition
    """
    _table = 'qiita.reagent_composition'
    _id_column = 'reagent_composition_id'

    @property
    def external_lot_id(self):
        """The external lot id of the reagent"""
        return self._get_attr('external_lot_id')

    @property
    def reagent_type(self):
        """The reagent type"""
        with TRN:
            sql = """SELECT description
                     FROM qiita.reagent_composition_type
                        JOIN qiita.reagent_composition
                            USING (composition_type_id)
                     WHERE reagent_composition_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()


class PrimerComposition(_Composition):
    """Primer composition class

    See Also
    --------
    _Composition
    """
    # TODO: I'm still a bit confused on how the Primer Compositions work around
    # So I'm not sure how this class should look like
    pass


class PrimerSetComposition(_Composition):
    """Primer set composition class

    See Also
    --------
    _Composition
    """


class SampleComposition(_Composition):
    """Sample composition class

    Attributes
    ----------
    content_id
    content_type

    See Also
    --------
    _Composition
    """
    _table = 'qiita.sample_composition'
    _id_column = 'sample_composition_id'

    @property
    def content_id(self):
        """The content id"""
        return self._get_attr('content_id')

    @property
    def content_type(self):
        """The content type"""
        with TRN:
            sql = """SELECT description
                     FROM qiita.sample_composition_type
                        JOIN qiita.sample_composition
                            USING (sample_composition_type_id)
                     WHERE sample_composition_id = %s"""
            TRN.add(sql, [self.id])
            return TRN.execute_fetchlast()


class GDNAComposition(_Composition):
    """gDNA composition class

    Attributes
    ----------
    sample_composition

    See Also
    --------
    _Composition
    """
    _table = 'qiita.gdna_composition'
    _id_column = 'gdna_composition_id'

    @property
    def sample_composition(self):
        return SampleComposition(self._get_attr('sample_composition_id'))


class LibraryPrep16SComposition(_Composition):
    """16S Library Preparation composition class

    Attributes
    ----------
    gdna_composition
    primer_composition

    See Also
    --------
    _Composition
    """
    _table = 'qiita."16S_library_prep_composition"'
    _id_column = '16S_library_prep_composition_id'

    @property
    def gdna_composition(self):
        return GDNAComposition(self._get_attr('gdna_composition_id'))

    @property
    def primer_composition(self):
        return PrimerComposition(self._get_attr('primer_composition_id'))


class NormalizedGDNAComposition(_Composition):
    """Normalized gDNA composition class

    Attributes
    ----------
    gdna_composition

    See Also
    --------
    _Composition
    """
    _table = 'qiita.normalized_gdna_composition'
    _id_column = 'normalized_gdna_composition_id'

    @property
    def gdna_composition(self):
        return GDNAComposition(self._get_attr('gdna_composition_id'))


class LibraryPrepShotgunComposition(_Composition):
    """Shotgun Library Preparation composition class

    Attributes
    ----------
    normalized_gdna_composition
    i5_composition
    i7_composition

    See Also
    --------
    _Composition
    """
    _table = 'qiita.shotgun_library_prep_composition'
    _id_column = 'shotgun_library_prep_composition_id'

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


class PoolComposition(_Composition):
    """Pool composition class

    Attributes
    ----------
    components

    See Also
    --------
    _Composition
    """
    _table = 'qiita.pool_composition'
    _id_column = 'pool_composition_id'

    @property
    def components(self):
        with TRN:
            sql = """SELECT input_compostion_id, input_volume as volume,
                            percentage_of_output as percentage
                     FROM qiita.pool_composition_components
                     WHERE output_pool_composition_id = %s"""
            TRN.add(sql, [self.id])
            # TODO: return the correct composition type instead of the ID
            return TRN.execute_fetchindex()


class PrimerSet(LabmanObject):
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
