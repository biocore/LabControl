-- July 15, 2019
-- Rename any existing instances of 'kappa' to 'kapa'

CREATE VIEW view_composition_type AS SELECT a.composition_id, b.description AS composition_type FROM labcontrol.composition a, labcontrol.composition_type b WHERE a.composition_type_id = b.composition_type_id;
CREATE VIEW view_pool_composition_type AS SELECT DISTINCT a.output_pool_composition_id AS pool_composition_id, b.composition_type FROM labcontrol.pool_composition_components a, view_composition_type b WHERE a.input_composition_id = b.composition_id order by a.output_pool_composition_id;
CREATE VIEW view_map_composition_type_to_sequencing_process_id AS SELECT a.sequencing_process_id, a.pool_composition_id, b.composition_type FROM labcontrol.sequencing_process_lanes a, view_pool_composition_type b WHERE a.pool_composition_id = b.pool_composition_id;
