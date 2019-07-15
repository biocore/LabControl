-- July 15, 2019
-- Rename any existing instances of 'kappa' to 'kapa'

-- Functions taken from Stack Overflow:
-- https://stackoverflow.com/questions/48102295/postgresql-rename-column-only-if-exists

CREATE OR REPLACE FUNCTION column_exists(ptable TEXT, pcolumn TEXT)
  RETURNS BOOLEAN AS $BODY$
DECLARE result bool;
BEGIN
    -- Does the requested column exist?
    SELECT COUNT(*) INTO result
    FROM information_schema.columns
    WHERE
      table_name = ptable and
      column_name = pcolumn;
    RETURN result;
END$BODY$
  LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION rename_column_if_exists(ptable TEXT, pcolumn TEXT, new_name TEXT)
  RETURNS VOID AS $BODY$
BEGIN
    -- Rename the column if it exists.
    IF column_exists(ptable, pcolumn) THEN
        EXECUTE FORMAT('ALTER TABLE %I RENAME COLUMN %I TO %I;',
            ptable, pcolumn, new_name);
    END IF;
END$BODY$
  LANGUAGE plpgsql VOLATILE;

rename_column_if_exists(library_prep_shotgun_process, kappa_hyper_plus_kit_id, kapa_hyper_plus_kit_id);
-- ALTER TABLE labcontrol.library_prep_shotgun_process RENAME COLUMN kappa_hyper_plus_kit_id to kapa_hyper_plus_kit_id;
-- ALTER INDEX idx_shotgun_library_prep_process_kappa RENAME TO idx_shotgun_library_prep_process_kapa;
-- ALTER TABLE labcontrol.library_prep_shotgun_process RENAME CONSTRAINT fk_shotgun_library_prep_process_kappa TO fk_shotgun_library_prep_process_kapa;
-- UPDATE labcontrol.reagent_composition_type SET description = 'kappa hyper plus kit' where description = 'kapa hyper plus kit';


