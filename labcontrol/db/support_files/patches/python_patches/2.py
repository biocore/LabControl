from labcontrol.db.sql_connection import TRN

with TRN:
    sql = """SELECT COUNT(*) FROM information_schema.columns
             WHERE table_name = 'library_prep_shotgun_process'
             AND column_name = 'kappa_hyper_plus_kit_id';"""
    TRN.add(sql)
    result = TRN.execute_fetchflatten()

    print("BEGIN TEST")
    print(str(result))
    print("END TEST")
    
    # for now, assume result will be either 0 or 1.
    # if 1, then the column 'kappa_hyper_plus_kit_id' needs
    # to be renamed to 'kapa_hyper_plus_kit_id', otherwise
    # it has already been renamed.
    if result == 1:
        sql = """ALTER TABLE labcontrol.library_prep_shotgun_process RENAME
        COLUMN kappa_hyper_plus_kit_id to kapa_hyper_plus_kit_id;"""
        TRN.add(sql)
        TRN.execute()
        TRN.commit()
