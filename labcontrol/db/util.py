# ----------------------------------------------------------------------------
# Copyright (c) 2017-, LabControl development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import sql_connection
from . import process
from . import composition


def get_pools_listing(is_plate_pool_limits, is_amplicon_plate_pool_limits):
    """Generates pool listing for GUI with direct DB access for speed

    Returns
    -------
    list of list

    Notes
    -----
    Reproduces the functionality of getting various information from a pool
    object and its components (e.g., p.id, p.container.external_id,
    p.upstream_process.id, etc) but with direct calls to the database
    """
    pool_composition_desc = composition.PoolComposition.\
        get_composition_type_description()
    amplicon_composition_desc = composition.LibraryPrep16SComposition.\
        get_composition_type_description()

    with sql_connection.TRN as TRN:
        sql = """SELECT pool_composition_id, external_id,
                    (SELECT DISTINCT description != '{0}'
                     FROM labman.pool_composition_components
                     LEFT JOIN labman.composition ON (
                         input_composition_id = composition_iD)
                     LEFT JOIN labman.composition_type USING (
                         composition_type_id)
                     WHERE output_pool_composition_id = pool_composition_id)
                     as is_plate_pool,
                    (SELECT DISTINCT description = '{1}'
                     FROM labman.pool_composition_components
                     LEFT JOIN labman.composition ON (
                         input_composition_id = composition_iD)
                     LEFT JOIN labman.composition_type USING (
                         composition_type_id)
                     WHERE output_pool_composition_id = pool_composition_id)
                     as is_amplicon_plate_pool, upstream_process_id
                 FROM labman.pool_composition
                 LEFT JOIN labman.composition USING (composition_id)
                 LEFT JOIN labman.tube USING (container_id)
                 LEFT JOIN labman.composition_type USING (composition_type_id)
                 ORDER BY pool_composition_id""".format(
            pool_composition_desc, amplicon_composition_desc)
        TRN.add(sql)

        # if you are looking for a way to improve performance, you would
        # need to:
        # 1. Create a database table with all the process.Process.factory
        # factory_classes
        # 2. retrieve the table names that correspond to each object
        # 3. reproduce what process.Process.factory does but in the database
        return [[pid, eid, ipp, iap, process.Process.factory(upi).id]
                for pid, eid, ipp, iap, upi in TRN.execute_fetchindex()
                if ipp in is_plate_pool_limits and
                iap in is_amplicon_plate_pool_limits]
