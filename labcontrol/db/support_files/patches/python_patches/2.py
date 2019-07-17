from labcontrol.db.sql_connection import TRN

import logging

with TRN:
    sql = """SELECT COUNT(*) FROM information_schema.columns
             WHERE table_name = 'library_prep_shotgun_process'
             AND column_name = 'kappa_hyper_plus_kit_id';"""
    logging.debug(sql)
    TRN.add(sql)
    result = TRN.execute_fetchflatten()[0]

    # for now, assume result will be either 0 or 1.
    # if 1, then the column 'kappa_hyper_plus_kit_id' needs
    # to be renamed to 'kapa_hyper_plus_kit_id', otherwise
    # it has already been renamed.
    if result == 1:
        msg = ('labcontrol.library_prep_shotgun_process contains the '
               'column name kappa_hyper_plus_kit_id. Renaming to '
               'kapa_hyper_plus_kit_id...')
        logging.debug(msg)

        sql = """ALTER TABLE labcontrol.library_prep_shotgun_process RENAME
        COLUMN kappa_hyper_plus_kit_id to kapa_hyper_plus_kit_id;"""
        TRN.add(sql)
    else:
        msg = ('labcontrol.library_prep_shotgun_process contains the '
               'column name kapa_hyper_plus_kit_id. Skipping...')
        logging.debug(msg)

    sql = """ALTER INDEX IF EXISTS idx_shotgun_library_prep_process_kappa
             RENAME TO idx_shotgun_library_prep_process_kapa;"""

    logging.debug(sql)
    TRN.add(sql)

    sql = """ALTER TABLE labcontrol.library_prep_shotgun_process RENAME
             CONSTRAINT fk_shotgun_library_prep_process_kappa TO
             fk_shotgun_library_prep_process_kapa;"""

    logging.debug(sql)
    TRN.add(sql)

    sql = """UPDATE labcontrol.reagent_composition_type SET description =
             'kapa hyper plus kit' where description =
             'kappa hyper plus kit';"""
    TRN.add(sql)

    '''
    TODO: Need to commit (pun intended) to having all of these actions take
    place within a single transaction, or commit() each one in turn. The
    problem in this case is that debug messages for all statements are printed
    beforehand, implying that they were completed when perhaps none of them
    were committed because any one or all of them failed due to some error.
    Note that it will raise an exception on the first error, so the user can
    repair the first error and then still encounter more errors.
    '''
    TRN.execute()
    TRN.commit()
