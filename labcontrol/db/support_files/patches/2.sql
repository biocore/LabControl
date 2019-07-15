-- July 15, 2019
-- Rename any existing instances of 'kappa' to 'kapa'
ALTER TABLE labcontrol.library_prep_shotgun_process RENAME COLUMN kappa_hyper_plus_kit_id to kapa_hyper_plus_kit_id;
ALTER INDEX idx_shotgun_library_prep_process_kappa RENAME TO idx_shotgun_library_prep_process_kapa;
ALTER TABLE labcontrol.library_prep_shotgun_process RENAME CONSTRAINT fk_shotgun_library_prep_process_kappa TO fk_shotgun_library_prep_process_kapa;
UPDATE labcontrol.reagent_composition_type SET description = 'kappa hyper plus kit' where description = 'kapa hyper plus kit';


