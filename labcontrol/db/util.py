# ----------------------------------------------------------------------------
# Copyright (c) 2017-, labman development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from . import sql_connection
from . import process


def get_pools_listing():
    """Generates pool listing for GUI with direct DB access for speed

    Returns
    -------
    list of list

    Notes
    -----
    Reproduces the functionality of:
    [p.id, p.container.external_id, p.is_plate_pool, p.upstream_process.id]
     for p in PoolComposition.get_pools()]
    but with direct calls to the database
    """
    with sql_connection.TRN as TRN:
        sql = """SELECT pool_composition_id, external_id,
                    (SELECT DISTINCT description != 'pool'
                     FROM labman.pool_composition_components
                     LEFT JOIN labman.composition ON (
                         input_composition_id = composition_iD)
                     LEFT JOIN labman.composition_type USING (
                         composition_type_id)
                     WHERE output_pool_composition_id = pool_composition_id)
                     as is_plate_pool, upstream_process_id
                 FROM labman.pool_composition
                 LEFT JOIN labman.composition USING (composition_id)
                 LEFT JOIN labman.tube USING (container_id)
                 LEFT JOIN labman.composition_type USING (composition_type_id)
                 ORDER BY pool_composition_id"""
        TRN.add(sql)

        # if you are looking for a way to improve performance, you would
        # need to:
        # 1. Create a database table with all the process.Process.factory
        # factory_classes
        # 2. retrieve the table names that corresponde to each object
        # 3. reproduce what process.Process.factory does but in the database
        return [[pid, eid, ipp, process.Process.factory(upi).id]
                for pid, eid, ipp, upi in TRN.execute_fetchindex()]
