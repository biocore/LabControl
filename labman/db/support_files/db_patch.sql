CREATE SCHEMA labman;

CREATE TABLE labman.equipment_type ( 
	equipment_type_id    bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	CONSTRAINT pk_equipment_type PRIMARY KEY ( equipment_type_id ),
	CONSTRAINT idx_equipment_type UNIQUE ( description ) 
 );

COMMENT ON COLUMN labman.equipment_type.description IS 'Must be unique';

CREATE TABLE labman.gdna_content_type ( 
	gdna_content_type_id bigserial  NOT NULL,
	description          integer  NOT NULL,
	CONSTRAINT pk_gdna_content_type PRIMARY KEY ( gdna_content_type_id ),
	CONSTRAINT idx_gdna_content_type UNIQUE ( description ) 
 );

COMMENT ON TABLE labman.gdna_content_type IS 'Example types: sample, blank, vibrio positive control, alternate positive control, etc';

COMMENT ON COLUMN labman.gdna_content_type.description IS 'Must be unique';

CREATE TABLE labman.marker_gene_primer_set ( 
	marker_gene_primer_set_id bigserial  NOT NULL,
	external_identifier  integer  NOT NULL,
	marker_gene_name     varchar(100)  NOT NULL,
	target_subfragment   varchar(100)  NOT NULL,
	linker_primer_sequence varchar(250)  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_targeted_primer_plate PRIMARY KEY ( marker_gene_primer_set_id ),
	CONSTRAINT idx_marker_gene_primer_set UNIQUE ( external_identifier ) 
 );

COMMENT ON TABLE labman.marker_gene_primer_set IS 'This is sort of like the original targeted_primer_plate table but isn`t specific to a single plate template but rather to the set of 8 plates in the primer set for a given marker gene.';

COMMENT ON COLUMN labman.marker_gene_primer_set.external_identifier IS 'Must be unique';

COMMENT ON COLUMN labman.marker_gene_primer_set.marker_gene_name IS 'This could become an id to another type table holding 16S, 18S, ITS';

COMMENT ON COLUMN labman.marker_gene_primer_set.target_subfragment IS 'Greg isn`t sure what this is: clarification?

Again, if only limited choices available, could make a foreign key to a new type table';

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

CREATE TABLE labman.plate_type ( 
	plate_type_id        bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	CONSTRAINT pk_plate_type PRIMARY KEY ( plate_type_id ),
	CONSTRAINT idx_plate_type UNIQUE ( description ) 
 );

COMMENT ON COLUMN labman.plate_type.description IS 'Must be unique';

CREATE TABLE labman.pool_type ( 
	pool_type_id         bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	CONSTRAINT pk_pool_type PRIMARY KEY ( pool_type_id ),
	CONSTRAINT idx_pool_type UNIQUE ( description ) 
 );

COMMENT ON COLUMN labman.pool_type.description IS 'Must be unique';

CREATE TABLE labman.reagent_type ( 
	reagent_type_id      bigserial  NOT NULL,
	description          varchar(100)  NOT NULL,
	CONSTRAINT pk_reagent_type PRIMARY KEY ( reagent_type_id ),
	CONSTRAINT idx_reagent_type UNIQUE ( description ) 
 );

COMMENT ON COLUMN labman.reagent_type.description IS 'Must be unique';

CREATE TABLE labman.equipment ( 
	equipment_id         integer  NOT NULL,
	external_id          integer  NOT NULL,
	equipment_type_id    integer  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_equipment PRIMARY KEY ( equipment_id ),
	CONSTRAINT idx_equipment UNIQUE ( external_id ) 
 );

COMMENT ON COLUMN labman.equipment.external_id IS 'Must be unique';

CREATE TABLE labman.plate ( 
	plate_id             integer  NOT NULL,
	external_identifier  varchar(250)  NOT NULL,
	creator_id           integer  NOT NULL,
	create_date          date  NOT NULL,
	plate_type_id        integer  NOT NULL,
	plate_configuration_id integer  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_plate PRIMARY KEY ( plate_id ),
	CONSTRAINT idx_plate UNIQUE ( external_identifier ) 
 );

COMMENT ON COLUMN labman.plate.external_identifier IS 'Must be unique';

COMMENT ON COLUMN labman.plate.creator_id IS 'This should probably be a foreign key to a user_id somewhere else in the db';

CREATE TABLE labman.pool ( 
	pool_id              bigserial  NOT NULL,
	pool_type_id         integer  NOT NULL,
	total_volume         float8  NOT NULL,
	remaining_volume     float8  NOT NULL,
	discarded            bool  NOT NULL,
	CONSTRAINT pk_pool PRIMARY KEY ( pool_id )
 );

COMMENT ON COLUMN labman.pool.total_volume IS 'Should this be mandatory?  Orig schema shows targeted_pool and run_pool but NOT shotgun_pool as having volumes ... is that accurate?';

COMMENT ON COLUMN labman.pool.remaining_volume IS 'May not be null,so add trigger to set to same as total_volume when record is created?';

CREATE TABLE labman.primer_plate_template ( 
	primer_plate_template_id bigserial  NOT NULL,
	plate_id             integer  NOT NULL,
	marker_gene_primer_set_id integer  NOT NULL,
	CONSTRAINT pk_target_primer_plate PRIMARY KEY ( primer_plate_template_id )
 );

COMMENT ON TABLE labman.primer_plate_template IS 'I would prefer to call this a marker gene primer plate template, because it really isn`t referring to a specific physical plate, but rather to a specific plate layout that can be stamped onto infinite working plates';

CREATE TABLE labman.reagent ( 
	reagent_id           integer  NOT NULL,
	external_lot_id      integer  NOT NULL,
	reagent_type_id      integer  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_reagent PRIMARY KEY ( reagent_id ),
	CONSTRAINT idx_reagent UNIQUE ( external_lot_id ) 
 );

COMMENT ON COLUMN labman.reagent.external_lot_id IS 'Must be unique';

CREATE TABLE labman.sequencing_pool_components ( 
	sequencing_pool_components_id bigserial  NOT NULL,
	sequencing_pool_id   integer  NOT NULL,
	component_pool_id    integer  NOT NULL,
	volume               float8  NOT NULL,
	percentage           float8  NOT NULL,
	CONSTRAINT pk_pool_components PRIMARY KEY ( sequencing_pool_components_id )
 );

COMMENT ON COLUMN labman.sequencing_pool_components.volume IS 'Use trigger to ensure that this is calculated if percentage is set?';

CREATE TABLE labman.well ( 
	well_id              bigserial  NOT NULL,
	plate_id             integer  NOT NULL,
	row_num              integer  NOT NULL,
	col_num              integer  NOT NULL,
	notes                varchar(600)  ,
	CONSTRAINT pk_well PRIMARY KEY ( well_id )
 );

CREATE TABLE labman.combined_pcr_well ( 
	combined_pcr_well_id bigserial  NOT NULL,
	well_id              integer  NOT NULL,
	raw_concentration    integer  ,
	CONSTRAINT pk_combined_pcr_well PRIMARY KEY ( combined_pcr_well_id )
 );

COMMENT ON COLUMN labman.combined_pcr_well.raw_concentration IS 'Not null because combined_pcr_plate_well record will (probably?) be created *before* concentration calculation.';

CREATE TABLE labman.gdna_plate ( 
	gdna_plate_id        bigserial  NOT NULL,
	plate_id             integer  NOT NULL,
	extraction_robot_id  integer  ,
	extraction_kit_id    integer  ,
	extraction_tool_id   integer  ,
	CONSTRAINT pk_dna_plate PRIMARY KEY ( gdna_plate_id )
 );

COMMENT ON COLUMN labman.gdna_plate.extraction_robot_id IS 'Not null because gdna plate record will be created *before* extraction.
Enforce correct type of equipment id with trigger.';

COMMENT ON COLUMN labman.gdna_plate.extraction_kit_id IS 'Not null because gdna plate record will be created *before* extraction.
Enforce correct type of reagent id with trigger.';

COMMENT ON COLUMN labman.gdna_plate.extraction_tool_id IS 'Not null because gdna plate record will be created *before* extraction.
Enforce correct type of equipment id with trigger.';

CREATE TABLE labman.gdna_well ( 
	gdna_well_id         bigserial  NOT NULL,
	well_id              integer  NOT NULL,
	content_type_id      integer  NOT NULL,
	content_id           varchar  ,
	CONSTRAINT pk_dna_well PRIMARY KEY ( gdna_well_id )
 );

COMMENT ON COLUMN labman.gdna_well.content_id IS 'Trigger should enforce, per-record, whether this is allowed to be null based on the content_type entered';

CREATE TABLE labman.primer_plate_template_well ( 
	primer_plate_template_well_id bigserial  NOT NULL,
	well_id              integer  NOT NULL,
	barcode_seq          varchar(20)  NOT NULL,
	CONSTRAINT pk_targeted_primer_well PRIMARY KEY ( primer_plate_template_well_id )
 );

COMMENT ON COLUMN labman.primer_plate_template_well.barcode_seq IS 'Should barcode sequence be mandatory, or do the primer plate templates have wells with blanks/etc in them?';

CREATE TABLE labman.combined_pcr_plate ( 
	combined_pcr_plate_id bigserial  NOT NULL,
	plate_id             integer  NOT NULL,
	gdna_plate_id        integer  NOT NULL,
	primer_plate_template_id integer  NOT NULL,
	master_mix_id        integer  NOT NULL,
	tm300_8_tool_id      integer  NOT NULL,
	tm50_8_tool_id       integer  NOT NULL,
	water_id             integer  NOT NULL,
	processing_robot_id  integer  NOT NULL,
	discarded            bool  NOT NULL,
	CONSTRAINT pk_targeted_plate PRIMARY KEY ( combined_pcr_plate_id )
 );

COMMENT ON TABLE labman.combined_pcr_plate IS 'The wet lab calls this the 3x PCR plate';

COMMENT ON COLUMN labman.combined_pcr_plate.master_mix_id IS 'Enforce correct type of reagent id with trigger.';

COMMENT ON COLUMN labman.combined_pcr_plate.tm300_8_tool_id IS 'Enforce correct type of equipment id with trigger.';

COMMENT ON COLUMN labman.combined_pcr_plate.tm50_8_tool_id IS 'Enforce correct type of equipment id with trigger.';

COMMENT ON COLUMN labman.combined_pcr_plate.water_id IS 'Enforce correct type of reagent id with trigger.';

COMMENT ON COLUMN labman.combined_pcr_plate.processing_robot_id IS 'Enforce correct type of equipment id with trigger.';

CREATE TABLE labman.combined_pcr_plate_pool ( 
	combined_pcr_plate_pool_id bigserial  NOT NULL,
	pool_id              integer  NOT NULL,
	combined_pcr_plate_id integer  NOT NULL,
	CONSTRAINT pk_targeted_pool PRIMARY KEY ( combined_pcr_plate_pool_id )
 );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_plate FOREIGN KEY ( plate_id ) REFERENCES labman.plate( plate_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_dna_plate FOREIGN KEY ( gdna_plate_id ) REFERENCES labman.gdna_plate( gdna_plate_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_reagent_water FOREIGN KEY ( water_id ) REFERENCES labman.reagent( reagent_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_equipment_tm50 FOREIGN KEY ( tm50_8_tool_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_reagent_master_mix FOREIGN KEY ( master_mix_id ) REFERENCES labman.reagent( reagent_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_equipment_robot FOREIGN KEY ( processing_robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate_equipment_tm300 FOREIGN KEY ( tm300_8_tool_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.combined_pcr_plate ADD CONSTRAINT fk_targeted_plate FOREIGN KEY ( primer_plate_template_id ) REFERENCES labman.primer_plate_template( primer_plate_template_id );

ALTER TABLE labman.combined_pcr_plate_pool ADD CONSTRAINT fk_targeted_pool_pool FOREIGN KEY ( pool_id ) REFERENCES labman.pool( pool_id );

ALTER TABLE labman.combined_pcr_plate_pool ADD CONSTRAINT fk_targeted_pool FOREIGN KEY ( combined_pcr_plate_id ) REFERENCES labman.combined_pcr_plate( combined_pcr_plate_id );

ALTER TABLE labman.combined_pcr_well ADD CONSTRAINT fk_targeted_well_well FOREIGN KEY ( well_id ) REFERENCES labman.well( well_id );

ALTER TABLE labman.equipment ADD CONSTRAINT fk_equipment_equipment_type FOREIGN KEY ( equipment_type_id ) REFERENCES labman.equipment_type( equipment_type_id );

ALTER TABLE labman.gdna_plate ADD CONSTRAINT fk_dna_plate_plate FOREIGN KEY ( plate_id ) REFERENCES labman.plate( plate_id );

ALTER TABLE labman.gdna_plate ADD CONSTRAINT fk_dna_plate_equipment_robot FOREIGN KEY ( extraction_robot_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.gdna_plate ADD CONSTRAINT fk_dna_plate_equipment_extraction_tool FOREIGN KEY ( extraction_tool_id ) REFERENCES labman.equipment( equipment_id );

ALTER TABLE labman.gdna_plate ADD CONSTRAINT fk_dna_plate_reagent_extraction_kit FOREIGN KEY ( extraction_kit_id ) REFERENCES labman.reagent( reagent_id );

ALTER TABLE labman.gdna_well ADD CONSTRAINT fk_dna_well_well FOREIGN KEY ( well_id ) REFERENCES labman.well( well_id );

ALTER TABLE labman.gdna_well ADD CONSTRAINT fk_gdna_well_gdna_content_type FOREIGN KEY ( content_type_id ) REFERENCES labman.gdna_content_type( gdna_content_type_id );

ALTER TABLE labman.plate ADD CONSTRAINT fk_plate_plate_type FOREIGN KEY ( plate_type_id ) REFERENCES labman.plate_type( plate_type_id );

ALTER TABLE labman.plate ADD CONSTRAINT fk_plate_plate_configuration FOREIGN KEY ( plate_configuration_id ) REFERENCES labman.plate_configuration( plate_configuration_id );

ALTER TABLE labman.pool ADD CONSTRAINT fk_pool_pool_type FOREIGN KEY ( pool_type_id ) REFERENCES labman.pool_type( pool_type_id );

ALTER TABLE labman.primer_plate_template ADD CONSTRAINT fk_targeted_primer_plate_plate FOREIGN KEY ( plate_id ) REFERENCES labman.plate( plate_id );

ALTER TABLE labman.primer_plate_template ADD CONSTRAINT fk_targeted_primer_plate FOREIGN KEY ( marker_gene_primer_set_id ) REFERENCES labman.marker_gene_primer_set( marker_gene_primer_set_id );

ALTER TABLE labman.primer_plate_template_well ADD CONSTRAINT fk_targeted_primer_well_well FOREIGN KEY ( well_id ) REFERENCES labman.well( well_id );

ALTER TABLE labman.reagent ADD CONSTRAINT fk_reagent_reagent_type FOREIGN KEY ( reagent_type_id ) REFERENCES labman.reagent_type( reagent_type_id );

ALTER TABLE labman.sequencing_pool_components ADD CONSTRAINT fk_sequencing_pool_components_sequencing_pool FOREIGN KEY ( sequencing_pool_id ) REFERENCES labman.pool( pool_id );

ALTER TABLE labman.sequencing_pool_components ADD CONSTRAINT fk_sequencing_pool_components_component_pool FOREIGN KEY ( component_pool_id ) REFERENCES labman.pool( pool_id );

ALTER TABLE labman.well ADD CONSTRAINT fk_well_plate FOREIGN KEY ( plate_id ) REFERENCES labman.plate( plate_id );

