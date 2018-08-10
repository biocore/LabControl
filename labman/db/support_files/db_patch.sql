CREATE SCHEMA IF NOT EXISTS labman;

CREATE TABLE labman.composition_type (
	composition_type_id  bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	CONSTRAINT pk_pool_type PRIMARY KEY ( composition_type_id ),
	CONSTRAINT idx_pool_type UNIQUE ( description )
 );

COMMENT ON COLUMN labman.composition_type.description IS 'Must be unique';

CREATE TABLE labman.container_type (
	container_type_id    bigserial  NOT NULL,
	description          varchar(250)  NOT NULL,
	CONSTRAINT pk_container_type PRIMARY KEY ( container_type_id )
 );

CREATE TABLE labman.equipment_type (
	equipment_type_id    bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	CONSTRAINT pk_equipment_type PRIMARY KEY ( equipment_type_id ),
	CONSTRAINT idx_equipment_type UNIQUE ( description )
 );

COMMENT ON COLUMN labman.equipment_type.description IS 'Must be unique';

CREATE TABLE labman.labmanager_access (
	email                varchar  NOT NULL
 );

CREATE TABLE labman.plate_configuration (
	plate_configuration_id bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	num_rows             integer  NOT NULL,
	num_columns          integer  NOT NULL,
	CONSTRAINT pk_plate_size PRIMARY KEY ( plate_configuration_id ),
	CONSTRAINT idx_plate_configuration UNIQUE ( description )
 );

COMMENT ON TABLE labman.plate_configuration IS 'I have named this "plate configuration" instead of "plate size" in case at some point we want to expand it to hold more than just a description (for instance, row letter range, column number range, deep-well vs regular, etc, etc).';

COMMENT ON COLUMN labman.plate_configuration.description IS 'Must be unique';

CREATE TABLE labman.primer_set (
	primer_set_id        bigserial  NOT NULL,
	external_id          varchar(250)  NOT NULL,
	target_name          varchar(100)  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_primer_set PRIMARY KEY ( primer_set_id )
 );

COMMENT ON COLUMN labman.primer_set.external_id IS 'Must be unique';

CREATE TABLE labman.process_type (
	process_type_id      bigserial  NOT NULL,
	description          varchar(1000)  ,
	CONSTRAINT pk_protocol PRIMARY KEY ( process_type_id )
 );

COMMENT ON TABLE labman.process_type IS 'Realistically, I`d call this a "protocol"';

CREATE TABLE labman.reagent_composition_type (
	reagent_composition_type_id bigserial  NOT NULL,
	description          varchar(250)  NOT NULL,
	CONSTRAINT pk_reagent_composition_type PRIMARY KEY ( reagent_composition_type_id )
 );

CREATE TABLE labman.sample_composition_type (
	sample_composition_type_id bigserial  NOT NULL,
	external_id          varchar  NOT NULL,
	description          varchar  NOT NULL,
	include_in_libraries bool DEFAULT 'True' NOT NULL,
	CONSTRAINT pk_gdna_content_type PRIMARY KEY ( sample_composition_type_id ),
	CONSTRAINT idx_gdna_content_type UNIQUE ( description ) ,
	CONSTRAINT idx_sample_composition_type UNIQUE ( external_id )
 );

COMMENT ON TABLE labman.sample_composition_type IS 'Example types: sample, blank, vibrio positive control, alternate positive control, etc';

COMMENT ON COLUMN labman.sample_composition_type.description IS 'Must be unique';

CREATE TABLE labman.shotgun_primer_set (
	shotgun_primer_set_id bigserial  NOT NULL,
	external_id          varchar  NOT NULL,
	current_combo_index  integer DEFAULT 0 NOT NULL,
	CONSTRAINT pk_shotgun_primer_set PRIMARY KEY ( shotgun_primer_set_id )
 );

CREATE TABLE labman.equipment (
	equipment_id         bigserial  NOT NULL,
	external_id          varchar(100)  NOT NULL,
	equipment_type_id    integer  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_equipment PRIMARY KEY ( equipment_id ),
	CONSTRAINT idx_equipment UNIQUE ( external_id )
 );

COMMENT ON COLUMN labman.equipment.external_id IS 'Must be unique';

CREATE TABLE labman.marker_gene_primer_set (
	marker_gene_primer_set_id bigserial  NOT NULL,
	primer_set_id        integer  NOT NULL,
	target_gene   varchar(100)  NOT NULL,
	target_subfragment   varchar(100)  NOT NULL,
	linker_sequence varchar(100) NOT NULL,
	fwd_primer_sequence varchar(250)  NOT NULL,
	rev_primer_sequence varchar(250)  NOT NULL,
	region varchar(250) NOT NULL,
	CONSTRAINT pk_targeted_primer_plate PRIMARY KEY ( marker_gene_primer_set_id ),
	CONSTRAINT idx_marker_gene_primer_set UNIQUE ( primer_set_id )
 );

COMMENT ON TABLE labman.marker_gene_primer_set IS 'This is sort of like the original targeted_primer_plate table but isn`t specific to a single plate template but rather to the set of 8 plates in the primer set for a given marker gene.';

CREATE TABLE labman.plate (
	plate_id             bigserial  NOT NULL,
	external_id          varchar(250)  NOT NULL,
	plate_configuration_id integer  NOT NULL,
	discarded            bool DEFAULT 'False' NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_plate PRIMARY KEY ( plate_id ),
	CONSTRAINT idx_plate UNIQUE ( external_id )
 );

COMMENT ON COLUMN labman.plate.external_id IS 'Must be unique';

CREATE TABLE labman.process (
	process_id           bigserial  NOT NULL,
	process_type_id      integer  NOT NULL,
	run_date             timestamptz  NOT NULL,
	run_personnel_id     varchar  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_process PRIMARY KEY ( process_id )
 );

CREATE INDEX idx_process ON labman.process ( process_type_id );

CREATE TABLE labman.quantification_process (
	quantification_process_id bigserial  NOT NULL,
	process_id           integer  ,
	CONSTRAINT pk_pico_green_quantification_process PRIMARY KEY ( quantification_process_id )
 );

CREATE INDEX idx_pico_green_quantification_process ON labman.quantification_process ( process_id );

COMMENT ON TABLE labman.quantification_process IS 'At the moment, doesn`t appear we need to track different info for qpcr vs pico green.  Will nonetheless be able to tell which is which based on protocol id associated with parent process id';

CREATE TABLE labman.sequencing_process (
	sequencing_process_id bigserial  NOT NULL,
	process_id           bigint  NOT NULL,
	run_name             varchar  NOT NULL,
	experiment           varchar  ,
	sequencer_id         bigint  NOT NULL,
	fwd_cycles           integer  NOT NULL,
	rev_cycles           integer  NOT NULL,
	assay                text  NOT NULL,
	principal_investigator text  NOT NULL,
	CONSTRAINT pk_sequencing_process PRIMARY KEY ( sequencing_process_id )
 );

CREATE INDEX idx_sequencing_process ON labman.sequencing_process ( process_id );

CREATE INDEX idx_sequencing_process_1 ON labman.sequencing_process ( sequencer_id );

CREATE TABLE labman.sequencing_process_contacts (
	sequencing_process_id bigint  NOT NULL,
	contact_id           varchar  NOT NULL,
	CONSTRAINT idx_sequencing_process_contacts PRIMARY KEY ( sequencing_process_id, contact_id )
 );

CREATE INDEX idx_sequencing_process_contacts_0 ON labman.sequencing_process_contacts ( sequencing_process_id );

CREATE TABLE labman.compression_process (
	compression_process_id bigserial  NOT NULL,
	process_id           bigint  NOT NULL,
	robot_id             bigint  NOT NULL,
	CONSTRAINT pk_compression_process PRIMARY KEY ( compression_process_id )
 );

CREATE INDEX idx_compression_process_process_id ON labman.compression_process ( process_id );

CREATE INDEX idx_compression_process_robot_id ON labman.compression_process ( robot_id );

CREATE TABLE labman.container (
	container_id         bigserial  NOT NULL,
	container_type_id    integer  NOT NULL,
	latest_upstream_process_id integer  ,
	remaining_volume     float8  ,
	notes                varchar(600)  ,
	CONSTRAINT pk_container PRIMARY KEY ( container_id )
 );

CREATE INDEX idx_container ON labman.container ( container_type_id );

CREATE INDEX idx_container_0 ON labman.container ( latest_upstream_process_id );

CREATE TABLE labman.pooling_process (
	pooling_process_id   bigserial  NOT NULL,
	process_id           integer  ,
	quantification_process_id integer  ,
	robot_id             integer  ,
	destination          varchar  ,
	pooling_function_data JSON  NOT NULL,
	CONSTRAINT pk_pooling_process PRIMARY KEY ( pooling_process_id )
 );

CREATE INDEX idx_pooling_process ON labman.pooling_process ( process_id );

CREATE INDEX idx_pooling_process_robot ON labman.pooling_process ( robot_id );

CREATE INDEX idx_pooling_process_quant ON labman.pooling_process ( quantification_process_id );

COMMENT ON COLUMN labman.pooling_process.quantification_process_id IS 'It is my understanding that pooling is not always dependent upon immediate prior quantification (e.g., making the sequence pool) so this is nullable';

COMMENT ON COLUMN labman.pooling_process.robot_id IS 'Rename?  What robot does the plate-to-tube pooling?
Nullable for case where pooling is done manually; then the person who did it is assumed to be the person who ran the process';

CREATE TABLE labman.primer_working_plate_creation_process (
	primer_working_plate_creation_process_id bigserial  NOT NULL,
	process_id           integer  NOT NULL,
	primer_set_id        integer  NOT NULL,
	master_set_order_number varchar(250)  NOT NULL,
	CONSTRAINT pk_target_primer_plate PRIMARY KEY ( primer_working_plate_creation_process_id )
 );

CREATE INDEX idx_primer_working_plate_creation_process ON labman.primer_working_plate_creation_process ( primer_set_id );

CREATE INDEX idx_primer_working_plate_creation_process_0 ON labman.primer_working_plate_creation_process ( process_id );

CREATE TABLE labman.tube (
	tube_id              bigserial  NOT NULL,
	container_id         integer  NOT NULL,
	external_id          varchar(250)  NOT NULL,
	discarded            bool DEFAULT 'False' NOT NULL,
	CONSTRAINT pk_tube PRIMARY KEY ( tube_id )
 );

CREATE INDEX idx_tube_0 ON labman.tube ( container_id );

CREATE TABLE labman.well (
	well_id              bigserial  NOT NULL,
	container_id         integer  NOT NULL,
	plate_id             integer  NOT NULL,
	row_num              integer  NOT NULL,
	col_num              integer  NOT NULL,
	CONSTRAINT pk_well PRIMARY KEY ( well_id )
 );

CREATE INDEX idx_well ON labman.well ( container_id );

CREATE TABLE labman.composition (
	composition_id       bigserial  NOT NULL,
	composition_type_id  integer  NOT NULL,
	upstream_process_id  integer  NOT NULL,
	container_id         integer  NOT NULL,
	total_volume         float8  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_pool PRIMARY KEY ( composition_id )
 );

CREATE INDEX idx_composition ON labman.composition ( upstream_process_id );

CREATE INDEX idx_composition_0 ON labman.composition ( container_id );

COMMENT ON COLUMN labman.composition.total_volume IS 'Should this be mandatory?  Orig schema shows targeted_pool and run_pool but NOT shotgun_pool as having volumes ... is that accurate?';

CREATE TABLE labman.concentration_calculation (
	concentration_calculation_id bigserial  NOT NULL,
	quantitated_composition_id integer  NOT NULL,
	upstream_process_id  integer  NOT NULL,
	raw_concentration    real  NOT NULL,
	computed_concentration real  ,
	CONSTRAINT pk_concentration_calculation PRIMARY KEY ( concentration_calculation_id )
 );

CREATE INDEX idx_concentration_calculation ON labman.concentration_calculation ( upstream_process_id );

CREATE INDEX idx_concentration_calculation_0 ON labman.concentration_calculation ( quantitated_composition_id );

COMMENT ON COLUMN labman.concentration_calculation.quantitated_composition_id IS 'can`t be a specific kind because can be done on a gdna plate (in shotgun) or a library prep plate (in 16S)';

CREATE TABLE labman.pool_composition (
	pool_composition_id  bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	CONSTRAINT pk_pool_composition PRIMARY KEY ( pool_composition_id )
 );

CREATE INDEX idx_pool_composition ON labman.pool_composition ( composition_id );

CREATE TABLE labman.pool_composition_components (
	pool_composition_components_id bigserial  NOT NULL,
	output_pool_composition_id integer  NOT NULL,
	input_composition_id integer  NOT NULL,
	input_volume         float8  NOT NULL,
	percentage_of_output float8  NOT NULL,
	CONSTRAINT pk_pool_components PRIMARY KEY ( pool_composition_components_id )
 );

CREATE INDEX idx_pool_composition_components ON labman.pool_composition_components ( output_pool_composition_id );

COMMENT ON COLUMN labman.pool_composition_components.input_volume IS 'Use trigger to ensure that this is calculated if percentage is set?';

CREATE TABLE labman.primer_set_composition (
	primer_set_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	primer_set_id        integer  NOT NULL,
	barcode_seq          varchar(20)  NOT NULL,
	external_id          varchar  ,
	CONSTRAINT pk_targeted_primer_well PRIMARY KEY ( primer_set_composition_id )
 );

CREATE INDEX idx_primer_template_composition ON labman.primer_set_composition ( composition_id );

CREATE INDEX idx_primer_set_composition ON labman.primer_set_composition ( primer_set_id );

COMMENT ON COLUMN labman.primer_set_composition.barcode_seq IS 'Should barcode sequence be mandatory, or do the primer plate templates have wells with blanks/etc in them?';

CREATE TABLE labman.reagent_composition (
	reagent_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	reagent_composition_type_id integer  NOT NULL,
	external_lot_id      varchar(100)  NOT NULL,
	CONSTRAINT pk_reagent PRIMARY KEY ( reagent_composition_id ),
	CONSTRAINT idx_reagent_composition_1 UNIQUE ( reagent_composition_type_id, external_lot_id )
 );

CREATE INDEX idx_reagent_composition ON labman.reagent_composition ( composition_id );

CREATE INDEX idx_reagent_composition_0 ON labman.reagent_composition ( reagent_composition_type_id );

COMMENT ON COLUMN labman.reagent_composition.external_lot_id IS 'Must be unique';

CREATE TABLE labman.sample_composition (
	sample_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	sample_composition_type_id integer  NOT NULL,
	sample_id            varchar  ,
	content              varchar  NOT NULL,
	CONSTRAINT pk_dna_well PRIMARY KEY ( sample_composition_id )
 );

CREATE INDEX idx_sample_composition ON labman.sample_composition ( composition_id );

CREATE INDEX idx_sample_composition_0 ON labman.sample_composition ( sample_composition_type_id );

CREATE TABLE labman.sequencing_process_lanes (
	sequencing_process_id bigint  NOT NULL,
	pool_composition_id  bigint  NOT NULL,
	lane_number          integer  NOT NULL,
	CONSTRAINT idx_sequencing_process_lanes_0 UNIQUE ( sequencing_process_id, pool_composition_id, lane_number )
 );

CREATE INDEX idx_sequencing_process_lanes_1 ON labman.sequencing_process_lanes ( sequencing_process_id );

CREATE INDEX idx_sequencing_process_lanes_2 ON labman.sequencing_process_lanes ( pool_composition_id );

CREATE TABLE labman.shotgun_combo_primer_set (
	shotgun_combo_primer_set_id bigserial  NOT NULL,
	shotgun_primer_set_id bigint  NOT NULL,
	i5_primer_set_composition_id bigint  NOT NULL,
	i7_primer_set_composition_id bigint  NOT NULL,
	CONSTRAINT pk_shotgun_combo_primer_set PRIMARY KEY ( shotgun_combo_primer_set_id )
 );

CREATE INDEX idx_shotgun_combo_primer_set ON labman.shotgun_combo_primer_set ( i5_primer_set_composition_id );

CREATE INDEX idx_shotgun_combo_primer_set_0 ON labman.shotgun_combo_primer_set ( i7_primer_set_composition_id );

CREATE INDEX idx_shotgun_combo_primer_set_1 ON labman.shotgun_combo_primer_set ( shotgun_primer_set_id );

CREATE TABLE labman.gdna_composition (
	gdna_composition_id  bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	sample_composition_id integer  NOT NULL,
	CONSTRAINT pk_gdna_composition PRIMARY KEY ( gdna_composition_id )
 );

CREATE INDEX idx_gdna_composition ON labman.gdna_composition ( sample_composition_id );

CREATE INDEX idx_gdna_composition_0 ON labman.gdna_composition ( composition_id );

CREATE TABLE labman.gdna_extraction_process (
	gdna_extraction_process_id bigserial  NOT NULL,
	process_id           integer  NOT NULL,
	epmotion_robot_id    bigint  NOT NULL,
	epmotion_tool_id     bigint  NOT NULL,
	kingfisher_robot_id  bigint  NOT NULL,
	extraction_kit_id    bigint  NOT NULL,
	externally_extracted bool DEFAULT 'False' NOT NULL,
	CONSTRAINT pk_dna_plate PRIMARY KEY ( gdna_extraction_process_id )
 );

CREATE INDEX idx_extraction_process ON labman.gdna_extraction_process ( process_id );

CREATE INDEX idx_gdna_extraction_process ON labman.gdna_extraction_process ( epmotion_robot_id );

CREATE INDEX idx_gdna_extraction_process_0 ON labman.gdna_extraction_process ( epmotion_tool_id );

CREATE INDEX idx_gdna_extraction_process_1 ON labman.gdna_extraction_process ( extraction_kit_id );

CREATE TABLE labman.library_prep_16s_process (
	library_prep_16s_process_id bigserial  NOT NULL,
	process_id           bigint  NOT NULL,
	epmotion_robot_id    bigint  NOT NULL,
	epmotion_tm300_8_tool_id bigint  NOT NULL,
	epmotion_tm50_8_tool_id bigint  ,
	master_mix_id        bigint  NOT NULL,
	water_lot_id         bigint  NOT NULL,
	CONSTRAINT pk_targeted_plate PRIMARY KEY ( library_prep_16s_process_id )
 );

CREATE INDEX idx_library_prep_16s_process ON labman.library_prep_16s_process ( epmotion_robot_id );

CREATE INDEX idx_library_prep_16s_process_0 ON labman.library_prep_16s_process ( epmotion_tm300_8_tool_id );

CREATE INDEX idx_library_prep_16s_process_1 ON labman.library_prep_16s_process ( epmotion_tm50_8_tool_id );

CREATE INDEX idx_library_prep_16s_process_2 ON labman.library_prep_16s_process ( master_mix_id );

CREATE INDEX idx_library_prep_16s_process_3 ON labman.library_prep_16s_process ( water_lot_id );

COMMENT ON TABLE labman.library_prep_16s_process IS 'Process is PER PLATE. The wet lab calls this the 3x PCR plate';

CREATE TABLE labman.normalization_process (
	normalization_process_id bigserial  NOT NULL,
	process_id           integer  NOT NULL,
	quantitation_process_id integer  NOT NULL,
	water_lot_id         integer  NOT NULL,
	normalization_function_data JSON  NOT NULL,
	CONSTRAINT pk_normalization_process PRIMARY KEY ( normalization_process_id )
 );

CREATE INDEX idx_normalization_process ON labman.normalization_process ( process_id );

CREATE INDEX idx_normalization_process_0 ON labman.normalization_process ( quantitation_process_id );

CREATE INDEX idx_normalization_process_1 ON labman.normalization_process ( water_lot_id );

CREATE TABLE labman.primer_composition (
	primer_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	primer_set_composition_id integer  NOT NULL,
	CONSTRAINT pk_primer_composition PRIMARY KEY ( primer_composition_id )
 );

CREATE INDEX idx_primer_composition_comp ON labman.primer_composition ( composition_id );

CREATE INDEX idx_primer_composition_primer ON labman.primer_composition ( primer_set_composition_id );

CREATE TABLE labman.compressed_gdna_composition (
	compressed_gdna_composition_id bigserial  NOT NULL,
	composition_id       bigint  NOT NULL,
	gdna_composition_id  bigint  NOT NULL,
	CONSTRAINT pk_compressed_gdna_composition PRIMARY KEY ( compressed_gdna_composition_id )
 );

CREATE INDEX idx_compressed_gdna_composition_comp ON labman.compressed_gdna_composition ( composition_id );

CREATE INDEX idx_compressed_gdna_composition_gdna ON labman.compressed_gdna_composition ( gdna_composition_id );

CREATE TABLE labman.library_prep_16s_composition (
	library_prep_16s_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	gdna_composition_id  integer  NOT NULL,
	primer_composition_id integer  NOT NULL,
	CONSTRAINT pk_combined_pcr_well PRIMARY KEY ( library_prep_16s_composition_id )
 );

CREATE INDEX idx_16s_library_prep_composition ON labman.library_prep_16s_composition ( composition_id );

CREATE INDEX idx_16s_library_prep_composition_0 ON labman.library_prep_16s_composition ( gdna_composition_id );

CREATE INDEX idx_16s_library_prep_composition_1 ON labman.library_prep_16s_composition ( primer_composition_id );

CREATE TABLE labman.library_prep_shotgun_process (
	library_prep_shotgun_process_id bigserial  NOT NULL,
	process_id           integer  NOT NULL,
	kappa_hyper_plus_kit_id integer  NOT NULL,
	stub_lot_id          integer  NOT NULL,
	normalization_process_id integer  NOT NULL,
	CONSTRAINT pk_shotgun_library_prep_process PRIMARY KEY ( library_prep_shotgun_process_id )
 );

CREATE INDEX idx_shotgun_library_prep_process_process ON labman.library_prep_shotgun_process ( process_id );

CREATE INDEX idx_shotgun_library_prep_process_kappa ON labman.library_prep_shotgun_process ( kappa_hyper_plus_kit_id );

CREATE INDEX idx_shotgun_library_prep_process_stub ON labman.library_prep_shotgun_process ( stub_lot_id );

CREATE INDEX idx_shotgun_library_prep_process_norm ON labman.library_prep_shotgun_process ( normalization_process_id );

COMMENT ON COLUMN labman.library_prep_shotgun_process.stub_lot_id IS 'should there be more than one of these?';

CREATE TABLE labman.normalized_gdna_composition (
	normalized_gdna_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	compressed_gdna_composition_id bigint  NOT NULL,
	dna_volume           real  NOT NULL,
	water_volume         real  NOT NULL,
	CONSTRAINT pk_gdna_composition_0 PRIMARY KEY ( normalized_gdna_composition_id )
 );

CREATE INDEX idx_gdna_composition_1 ON labman.normalized_gdna_composition ( compressed_gdna_composition_id );

CREATE INDEX idx_gdna_composition_2 ON labman.normalized_gdna_composition ( composition_id );

CREATE TABLE labman.library_prep_shotgun_composition (
	library_prep_shotgun_composition_id bigserial  NOT NULL,
	composition_id       integer  NOT NULL,
	normalized_gdna_composition_id integer  NOT NULL,
	i5_primer_composition_id integer  NOT NULL,
	i7_primer_composition_id integer  NOT NULL,
	CONSTRAINT pk_combined_pcr_well_0 PRIMARY KEY ( library_prep_shotgun_composition_id )
 );

CREATE INDEX idx_16s_library_prep_composition_2 ON labman.library_prep_shotgun_composition ( composition_id );

CREATE INDEX idx_16s_library_prep_composition_3 ON labman.library_prep_shotgun_composition ( normalized_gdna_composition_id );

CREATE INDEX idx_16s_library_prep_composition_4 ON labman.library_prep_shotgun_composition ( i5_primer_composition_id );

CREATE INDEX idx_shotgun_library_prep_composition ON labman.library_prep_shotgun_composition ( i7_primer_composition_id );

ALTER TABLE labman.composition ADD CONSTRAINT fk_pool_pool_type FOREIGN KEY ( composition_type_id ) REFERENCES labman.composition_type( composition_type_id );

ALTER TABLE labman.composition ADD CONSTRAINT fk_composition_process FOREIGN KEY ( upstream_process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.composition ADD CONSTRAINT fk_composition_well FOREIGN KEY ( container_id ) REFERENCES labman.container( container_id );

ALTER TABLE labman.compressed_gdna_composition ADD CONSTRAINT fk_compressed_gdna_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.compressed_gdna_composition ADD CONSTRAINT fk_compressed_gdna_composition_gdna FOREIGN KEY ( gdna_composition_id ) REFERENCES labman.gdna_composition( gdna_composition_id );

ALTER TABLE labman.compression_process ADD CONSTRAINT fk_compression_process_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.compression_process ADD CONSTRAINT fk_compression_process FOREIGN KEY ( robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.concentration_calculation ADD CONSTRAINT fk_concentration_calculation_composition FOREIGN KEY ( quantitated_composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.concentration_calculation ADD CONSTRAINT fk_concentration_calculation FOREIGN KEY ( upstream_process_id ) REFERENCES labman.quantification_process( quantification_process_id );

ALTER TABLE labman.container ADD CONSTRAINT fk_container_container_type FOREIGN KEY ( container_type_id ) REFERENCES labman.container_type( container_type_id );

ALTER TABLE labman.container ADD CONSTRAINT fk_container_process FOREIGN KEY ( latest_upstream_process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.equipment ADD CONSTRAINT fk_equipment_equipment_type FOREIGN KEY ( equipment_type_id ) REFERENCES labman.equipment_type( equipment_type_id );

ALTER TABLE labman.gdna_composition ADD CONSTRAINT fk_gdna_composition_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.gdna_composition ADD CONSTRAINT fk_transfer_composition_source FOREIGN KEY ( sample_composition_id ) REFERENCES labman.sample_composition( sample_composition_id );

ALTER TABLE labman.gdna_extraction_process ADD CONSTRAINT fk_extraction_process_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.gdna_extraction_process ADD CONSTRAINT fk_gdna_extraction_process_eprobot FOREIGN KEY ( epmotion_robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.gdna_extraction_process ADD CONSTRAINT fk_gdna_extraction_process_tool FOREIGN KEY ( epmotion_tool_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.gdna_extraction_process ADD CONSTRAINT fk_gdna_extraction_process_kit FOREIGN KEY ( extraction_kit_id ) REFERENCES labman.reagent_composition( reagent_composition_id );

ALTER TABLE labman.gdna_extraction_process ADD CONSTRAINT fk_gdna_extraction_process_kf FOREIGN KEY ( kingfisher_robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.library_prep_16s_composition ADD CONSTRAINT fk_16s_library_prep_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.library_prep_16s_composition ADD CONSTRAINT fk_16s_library_prep_composition_gdna FOREIGN KEY ( gdna_composition_id ) REFERENCES labman.gdna_composition( gdna_composition_id );

ALTER TABLE labman.library_prep_16s_composition ADD CONSTRAINT fk_16s_library_prep_composition_primer FOREIGN KEY ( primer_composition_id ) REFERENCES labman.primer_composition( primer_composition_id );

ALTER TABLE labman.library_prep_16s_process ADD CONSTRAINT fk_targeted_plate_plate FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.library_prep_16s_process ADD CONSTRAINT fk_library_prep_16s_process_robot FOREIGN KEY ( epmotion_robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.library_prep_16s_process ADD CONSTRAINT fk_library_prep_16s_process_tm300 FOREIGN KEY ( epmotion_tm300_8_tool_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.library_prep_16s_process ADD CONSTRAINT fk_library_prep_16s_process_tm50 FOREIGN KEY ( epmotion_tm50_8_tool_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.library_prep_16s_process ADD CONSTRAINT fk_library_prep_16s_process_mm FOREIGN KEY ( master_mix_id ) REFERENCES labman.reagent_composition( reagent_composition_id );

ALTER TABLE labman.library_prep_16s_process ADD CONSTRAINT fk_library_prep_16s_process_water FOREIGN KEY ( water_lot_id ) REFERENCES labman.reagent_composition( reagent_composition_id );

ALTER TABLE labman.library_prep_shotgun_composition ADD CONSTRAINT fk_shotgun_library_prep_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.library_prep_shotgun_composition ADD CONSTRAINT fk_shotgun_library_prep_composition_normalized FOREIGN KEY ( normalized_gdna_composition_id ) REFERENCES labman.normalized_gdna_composition( normalized_gdna_composition_id );

ALTER TABLE labman.library_prep_shotgun_composition ADD CONSTRAINT fk_shotgun_library_prep_composition_i5 FOREIGN KEY ( i5_primer_composition_id ) REFERENCES labman.primer_composition( primer_composition_id );

ALTER TABLE labman.library_prep_shotgun_composition ADD CONSTRAINT fk_shotgun_library_prep_composition_i7 FOREIGN KEY ( i7_primer_composition_id ) REFERENCES labman.primer_composition( primer_composition_id );

ALTER TABLE labman.library_prep_shotgun_process ADD CONSTRAINT fk_shotgun_library_prep_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.library_prep_shotgun_process ADD CONSTRAINT fk_shotgun_library_prep_process_kappa FOREIGN KEY ( kappa_hyper_plus_kit_id ) REFERENCES labman.reagent_composition( reagent_composition_id );

ALTER TABLE labman.library_prep_shotgun_process ADD CONSTRAINT fk_shotgun_library_prep_process_stub FOREIGN KEY ( stub_lot_id ) REFERENCES labman.reagent_composition( reagent_composition_id );

ALTER TABLE labman.library_prep_shotgun_process ADD CONSTRAINT fk_shotgun_library_prep_process_norm FOREIGN KEY ( normalization_process_id ) REFERENCES labman.normalization_process( normalization_process_id );

ALTER TABLE labman.marker_gene_primer_set ADD CONSTRAINT fk_marker_gene_primer_set FOREIGN KEY ( primer_set_id ) REFERENCES labman.primer_set( primer_set_id );

ALTER TABLE labman.normalization_process ADD CONSTRAINT fk_normalization_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.normalization_process ADD CONSTRAINT fk_normalization_process_pico FOREIGN KEY ( quantitation_process_id ) REFERENCES labman.quantification_process( quantification_process_id );

ALTER TABLE labman.normalization_process ADD CONSTRAINT fk_normalization_process_water FOREIGN KEY ( water_lot_id ) REFERENCES labman.reagent_composition( reagent_composition_id );

ALTER TABLE labman.normalized_gdna_composition ADD CONSTRAINT fk_normalized_gdna_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.normalized_gdna_composition ADD CONSTRAINT fk_normalized_gdna_composition_gdna FOREIGN KEY ( compressed_gdna_composition_id ) REFERENCES labman.compressed_gdna_composition( compressed_gdna_composition_id );

ALTER TABLE labman.plate ADD CONSTRAINT fk_plate_plate_configuration FOREIGN KEY ( plate_configuration_id ) REFERENCES labman.plate_configuration( plate_configuration_id );

ALTER TABLE labman.pool_composition ADD CONSTRAINT fk_pool_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.pool_composition_components ADD CONSTRAINT fk_sequencing_pool_components_component_pool FOREIGN KEY ( input_composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.pool_composition_components ADD CONSTRAINT fk_pool_composition_components FOREIGN KEY ( output_pool_composition_id ) REFERENCES labman.pool_composition( pool_composition_id );

ALTER TABLE labman.pooling_process ADD CONSTRAINT fk_pooling_process_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.pooling_process ADD CONSTRAINT fk_pooling_process_equipment FOREIGN KEY ( robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.pooling_process ADD CONSTRAINT fk_pooling_process FOREIGN KEY ( quantification_process_id ) REFERENCES labman.quantification_process( quantification_process_id );

ALTER TABLE labman.primer_composition ADD CONSTRAINT fk_primer_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.primer_composition ADD CONSTRAINT fk_primer_composition_set FOREIGN KEY ( primer_set_composition_id ) REFERENCES labman.primer_set_composition( primer_set_composition_id );

ALTER TABLE labman.primer_set_composition ADD CONSTRAINT fk_primer_template_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.primer_set_composition ADD CONSTRAINT fk_primer_set_composition FOREIGN KEY ( primer_set_id ) REFERENCES labman.primer_set( primer_set_id );

ALTER TABLE labman.primer_working_plate_creation_process ADD CONSTRAINT fk_primer_working_plate_creation_process_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.primer_working_plate_creation_process ADD CONSTRAINT fk_primer_working_plate_creation_process FOREIGN KEY ( primer_set_id ) REFERENCES labman.primer_set( primer_set_id );

ALTER TABLE labman.process ADD CONSTRAINT fk_process_protocol FOREIGN KEY ( process_type_id ) REFERENCES labman.process_type( process_type_id );

ALTER TABLE labman.quantification_process ADD CONSTRAINT fk_pico_green_quantification_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.reagent_composition ADD CONSTRAINT fk_reagent_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.reagent_composition ADD CONSTRAINT fk_reagent_composition_reagent_type FOREIGN KEY ( reagent_composition_type_id ) REFERENCES labman.reagent_composition_type( reagent_composition_type_id );

ALTER TABLE labman.sample_composition ADD CONSTRAINT fk_sample_composition FOREIGN KEY ( composition_id ) REFERENCES labman.composition( composition_id );

ALTER TABLE labman.sample_composition ADD CONSTRAINT fk_sample_composition_type FOREIGN KEY ( sample_composition_type_id ) REFERENCES labman.sample_composition_type( sample_composition_type_id );

ALTER TABLE labman.sequencing_process ADD CONSTRAINT fk_sequencing_process_process FOREIGN KEY ( process_id ) REFERENCES labman.process( process_id );

ALTER TABLE labman.sequencing_process ADD CONSTRAINT fk_sequencing_process_eq FOREIGN KEY ( sequencer_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.sequencing_process_contacts ADD CONSTRAINT fk_sequencing_process_contacts FOREIGN KEY ( sequencing_process_id ) REFERENCES labman.sequencing_process( sequencing_process_id );

ALTER TABLE labman.sequencing_process_lanes ADD CONSTRAINT fk_sequencing_process_lanes FOREIGN KEY ( sequencing_process_id ) REFERENCES labman.sequencing_process( sequencing_process_id );

ALTER TABLE labman.sequencing_process_lanes ADD CONSTRAINT fk_sequencing_process_lanes_pool FOREIGN KEY ( pool_composition_id ) REFERENCES labman.pool_composition( pool_composition_id );

ALTER TABLE labman.shotgun_combo_primer_set ADD CONSTRAINT fk_shotgun_combo_primer_set_i5 FOREIGN KEY ( i5_primer_set_composition_id ) REFERENCES labman.primer_set_composition( primer_set_composition_id );

ALTER TABLE labman.shotgun_combo_primer_set ADD CONSTRAINT fk_shotgun_combo_primer_set_i7 FOREIGN KEY ( i7_primer_set_composition_id ) REFERENCES labman.primer_set_composition( primer_set_composition_id );

ALTER TABLE labman.shotgun_combo_primer_set ADD CONSTRAINT fk_shotgun_combo_primer_set FOREIGN KEY ( shotgun_primer_set_id ) REFERENCES labman.shotgun_primer_set( shotgun_primer_set_id );

ALTER TABLE labman.tube ADD CONSTRAINT fk_tube_container FOREIGN KEY ( container_id ) REFERENCES labman.container( container_id );

ALTER TABLE labman.well ADD CONSTRAINT fk_well_plate FOREIGN KEY ( plate_id ) REFERENCES labman.plate( plate_id );

ALTER TABLE labman.well ADD CONSTRAINT fk_well_container FOREIGN KEY ( container_id ) REFERENCES labman.container( container_id );
