-- July 15, 2019
-- Rename any existing instances of 'kappa' to 'kapa'
create view labcontrol.vw_map_spid_to_cid as select a.input_composition_id as composition_id, b.sequencing_process_id from labcontrol.pool_composition_components a, labcontrol.sequencing_process_lanes b where a.output_pool_composition_id = b.pool_composition_id order by b.sequencing_process_id;

create view labcontrol.vw_sequence_process_pool_assay_type_map as select distinct a.composition_type_id, b.sequencing_process_id from labcontrol.composition a, labcontrol.vw_map_spid_to_cid b where a.composition_id = b.composition_id;

create view labcontrol.vw_sequence_process_pool_of_pools_assay_type_map as select distinct d.composition_type_id, b.sequencing_process_id from labcontrol.composition d, labcontrol.pool_composition_components c, labcontrol.pool_composition a, labcontrol.vw_map_spid_to_cid b where a.composition_id = b.composition_id and c.output_pool_composition_id = a.pool_composition_id and d.composition_id = c.input_composition_id;

alter table labcontrol.sequencing_process drop column assay;
