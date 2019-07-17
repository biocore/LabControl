from labcontrol.db.sql_connection import TRN
import logging


with TRN:
    # although TRN has its own queue, use a local list to queue statements
    # until prerequisite queries are completed.
    statements = []

    #
    # rename kappa_hyper_plus_kit_id in library_prep_shotgun_process
    #
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
               'column name kappa_hyper_plus_kit_id. Will rename to '
               'kapa_hyper_plus_kit_id...')
        logging.debug(msg)

        sql = """ALTER TABLE labcontrol.library_prep_shotgun_process RENAME
        COLUMN kappa_hyper_plus_kit_id to kapa_hyper_plus_kit_id;"""
        statements.append(sql)
    else:
        msg = ('labcontrol.library_prep_shotgun_process contains the '
               'column name kapa_hyper_plus_kit_id. Skipping...')
        logging.debug(msg)

    #
    # rename fk_shotgun_library_prep_process_kappa in
    # library_prep_shotgun_process
    #
    sql = """SELECT COUNT(*) FROM information_schema.constraint_column_usage
                 WHERE table_name = 'library_prep_shotgun_process' AND
                 constraint_name = 'fk_shotgun_library_prep_process_kappa';"""

    logging.debug(sql)
    TRN.add(sql)
    result = TRN.execute_fetchflatten()[0]

    if result == 1:
        msg = ('labcontrol.library_prep_shotgun_process contains the '
               'constraint name fk_shotgun_library_prep_process_kappa. Will '
               'rename to fk_shotgun_library_prep_process_kapa...')
        logging.debug(msg)

        sql = """ALTER TABLE labcontrol.library_prep_shotgun_process RENAME
                     CONSTRAINT fk_shotgun_library_prep_process_kappa TO
                     fk_shotgun_library_prep_process_kapa;"""
        statements.append(sql)
    else:
        msg = ('labcontrol.library_prep_shotgun_process contains the '
               'constraint name fk_shotgun_library_prep_process_kapa. '
               'Skipping...')
        logging.debug(msg)

    #
    # rename index idx_shotgun_library_prep_process_kappa
    #
    sql = """ALTER INDEX IF EXISTS idx_shotgun_library_prep_process_kappa
             RENAME TO idx_shotgun_library_prep_process_kapa;"""

    logging.debug(sql)
    statements.append(sql)

    #
    # update description string
    #
    sql = """UPDATE labcontrol.reagent_composition_type SET description =
             'kapa hyper plus kit' where description =
             'kappa hyper plus kit';"""

    statements.append(sql)

    # slightly inefficient, but TRN.add() does perform checking in addition to
    # appending each SQL statement to its queue.
    for statement in statements:
        TRN.add(statement)

    TRN.execute()
    TRN.commit()
