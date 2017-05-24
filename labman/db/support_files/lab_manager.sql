CREATE TABLE settings (
	test                 bool DEFAULT True NOT NULL,
	current_patch        varchar DEFAULT 'unpatched' NOT NULL
);

CREATE SCHEMA plate;

CREATE SCHEMA pm;

CREATE SCHEMA shotgun;

CREATE SCHEMA study;

CREATE SCHEMA tgene;

CREATE SCHEMA users;

-- NOTE: these type definitions need to be added manually cause DBSchema
-- doesn't support them
CREATE TYPE pm.target_region AS ENUM ('16S', '18S', 'ITS');
CREATE TYPE pm.target_subfragment AS ENUM ('V4');
CREATE TYPE pm.seq_platform AS ENUM ('Illumina');
CREATE TYPE pm.seq_instrument_model AS ENUM ('MiSeq', 'HiSeq 2500', 'HiSeq 4000');
CREATE TYPE pm.reagent_type AS ENUM ('MiSeq v3 150 cycle');
CREATE TYPE pm.assay_type AS ENUM ('Kapa Hyper Plus', 'TrueSeq HT');
-- END NOTE

CREATE SEQUENCE pm.dna_plate_dna_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.dna_plate_dna_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.echo_echo_id_seq START WITH 1;

CREATE SEQUENCE pm.echo_echo_id_seq1 START WITH 1;

CREATE SEQUENCE pm.extraction_kit_lot_extraction_kit_lot_id_seq START WITH 1;

CREATE SEQUENCE pm.extraction_kit_lot_extraction_kit_lot_id_seq1 START WITH 1;

CREATE SEQUENCE pm.extraction_robot_extraction_robot_id_seq START WITH 1;

CREATE SEQUENCE pm.extraction_robot_extraction_robot_id_seq1 START WITH 1;

CREATE SEQUENCE pm.extraction_tool_extraction_tool_id_seq START WITH 1;

CREATE SEQUENCE pm.extraction_tool_extraction_tool_id_seq1 START WITH 1;

CREATE SEQUENCE pm.master_mix_lot_master_mix_lot_id_seq START WITH 1;

CREATE SEQUENCE pm.master_mix_lot_master_mix_lot_id_seq1 START WITH 1;

CREATE SEQUENCE pm.mosquito_mosquito_id_seq START WITH 1;

CREATE SEQUENCE pm.mosquito_mosquito_id_seq1 START WITH 1;

CREATE SEQUENCE pm.plate_reader_plate_reader_id_seq START WITH 1;

CREATE SEQUENCE pm.plate_reader_plate_reader_id_seq1 START WITH 1;

CREATE SEQUENCE pm.plate_type_plate_type_id_seq START WITH 1;

CREATE SEQUENCE pm.plate_type_plate_type_id_seq1 START WITH 1;

CREATE SEQUENCE pm.processing_robot_processing_robot_id_seq START WITH 1;

CREATE SEQUENCE pm.processing_robot_processing_robot_id_seq1 START WITH 1;

CREATE SEQUENCE pm.qpcr_qpcr_id_seq START WITH 1;

CREATE SEQUENCE pm.qpcr_qpcr_id_seq1 START WITH 1;

CREATE SEQUENCE pm.run_pool_run_pool_id_seq START WITH 1;

CREATE SEQUENCE pm.run_pool_run_pool_id_seq1 START WITH 1;

CREATE SEQUENCE pm.sample_plate_sample_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.sample_plate_sample_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_adapter_aliquot_shotgun_adapter_aliquot_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_adapter_aliquot_shotgun_adapter_aliquot_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_index_aliquot_shotgun_index_aliquot_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_index_aliquot_shotgun_index_aliquot_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_index_shotgun_index_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_index_shotgun_index_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_index_tech_shotgun_index_tech_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_index_tech_shotgun_index_tech_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_library_prep_kit_shotgun_library_prep_kit_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_library_prep_kit_shotgun_library_prep_kit_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_normalized_plate_shotgun_normalized_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_normalized_plate_shotgun_normalized_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_plate_shotgun_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_plate_shotgun_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_pool_plate_shotgun_pool_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_pool_plate_shotgun_pool_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.shotgun_pool_shotgun_pool_id_seq START WITH 1;

CREATE SEQUENCE pm.shotgun_pool_shotgun_pool_id_seq1 START WITH 1;

CREATE SEQUENCE pm.targeted_plate_targeted_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.targeted_plate_targeted_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.targeted_pool_targeted_pool_id_seq START WITH 1;

CREATE SEQUENCE pm.targeted_pool_targeted_pool_id_seq1 START WITH 1;

CREATE SEQUENCE pm.targeted_primer_plate_targeted_primer_plate_id_seq START WITH 1;

CREATE SEQUENCE pm.targeted_primer_plate_targeted_primer_plate_id_seq1 START WITH 1;

CREATE SEQUENCE pm.tm300_8_tool_tm300_8_tool_id_seq START WITH 1;

CREATE SEQUENCE pm.tm300_8_tool_tm300_8_tool_id_seq1 START WITH 1;

CREATE SEQUENCE pm.tm50_8_tool_tm50_8_tool_id_seq START WITH 1;

CREATE SEQUENCE pm.tm50_8_tool_tm50_8_tool_id_seq1 START WITH 1;

CREATE SEQUENCE pm.water_lot_water_lot_id_seq START WITH 1;

CREATE SEQUENCE pm.water_lot_water_lot_id_seq1 START WITH 1;

CREATE SEQUENCE study.service_service_id_seq START WITH 1;

CREATE SEQUENCE study.study_communication_backlog_service_id_seq START WITH 1;

CREATE SEQUENCE study.study_communication_backlog_study_id_seq START WITH 1;

CREATE SEQUENCE study.study_sample_study_id_seq START WITH 1;

CREATE SEQUENCE study.study_study_id_seq START WITH 1;

CREATE SEQUENCE users.access_level_access_level_id_seq START WITH 1;

CREATE SEQUENCE users.user_user_id_seq START WITH 1;

CREATE TABLE pm.echo (
	echo_id              bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_echo PRIMARY KEY ( echo_id ),
	CONSTRAINT idx_echo UNIQUE ( name )
 );

CREATE TABLE pm.extraction_kit_lot (
	extraction_kit_lot_id bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_extraction_kit_lot PRIMARY KEY ( extraction_kit_lot_id ),
	CONSTRAINT uq_extraction_kit_lot_name UNIQUE ( name )
 );

CREATE TABLE pm.extraction_robot (
	extraction_robot_id  bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_extraction_robot PRIMARY KEY ( extraction_robot_id ),
	CONSTRAINT uq_extraction_robot_name UNIQUE ( name )
 );

CREATE TABLE pm.extraction_tool (
	extraction_tool_id   bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_extraction_tool PRIMARY KEY ( extraction_tool_id ),
	CONSTRAINT uq_extraction_tool_name UNIQUE ( name )
 );

COMMENT ON TABLE pm.extraction_tool IS 'TM1000-8 tools';

CREATE TABLE pm.master_mix_lot (
	master_mix_lot_id    bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_master_mix_lot PRIMARY KEY ( master_mix_lot_id ),
	CONSTRAINT uq_master_mix_lot_name UNIQUE ( name )
 );

CREATE TABLE pm.mosquito (
	mosquito_id          bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_mosquito PRIMARY KEY ( mosquito_id ),
	CONSTRAINT idx_mosquito UNIQUE ( name )
 );

CREATE TABLE pm.plate_reader (
	plate_reader_id      bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_plate_reader PRIMARY KEY ( plate_reader_id ),
	CONSTRAINT idx_plate_reader UNIQUE ( name )
 );

CREATE TABLE pm.plate_type (
	plate_type_id        bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	cols                 smallint  NOT NULL,
	"rows"               smallint  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_plate_type PRIMARY KEY ( plate_type_id ),
	CONSTRAINT uq_plate_type_name UNIQUE ( name )
 );

CREATE TABLE pm.processing_robot (
	processing_robot_id  bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_processing_robot PRIMARY KEY ( processing_robot_id ),
	CONSTRAINT uq_processing_robot_name UNIQUE ( name )
 );

CREATE TABLE pm.qpcr (
	qpcr_id              bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_qpcr PRIMARY KEY ( qpcr_id ),
	CONSTRAINT idx_qpcr UNIQUE ( name )
 );

CREATE TABLE pm.run_pool (
	run_pool_id          bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	volume               real  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_run_pool PRIMARY KEY ( run_pool_id ),
	CONSTRAINT idx_run_pool UNIQUE ( name )
 );

CREATE TABLE pm.sample (
	sample_id            varchar  NOT NULL,
	is_blank             bool DEFAULT false NOT NULL,
	details              varchar  ,
	CONSTRAINT pk_sample PRIMARY KEY ( sample_id )
 );

CREATE TABLE pm.sample_plate (
	sample_plate_id      bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	created_on           timestamp  ,
	user_id              bigint  NOT NULL,
	plate_type_id        bigint  NOT NULL,
	notes                varchar  ,
	discarded            bool DEFAULT false NOT NULL,
	CONSTRAINT pk_sample_plate PRIMARY KEY ( sample_plate_id ),
	CONSTRAINT uq_sample_plate_name UNIQUE ( name )
 );

CREATE INDEX idx_sample_plate_plate_type_id ON pm.sample_plate ( plate_type_id );

CREATE INDEX idx_sample_plate ON pm.sample_plate ( user_id );

COMMENT ON TABLE pm.sample_plate IS 'Holds the information about the initial plate that the wet lab creates.';

CREATE TABLE pm.sample_plate_layout (
	sample_plate_id      bigint  NOT NULL,
	sample_id            varchar  ,
	col                  smallint  NOT NULL,
	"row"                smallint  NOT NULL,
	name                 varchar  ,
	notes                varchar
 );

CREATE INDEX idx_sample_plate_layout_sample_id ON pm.sample_plate_layout ( sample_id );

CREATE INDEX idx_sample_plate_layout_sample_plate_id ON pm.sample_plate_layout ( sample_plate_id );

COMMENT ON COLUMN pm.sample_plate_layout.name IS 'The name of the sample in this plate in case that needs to be changed (e.g. if the sample has been plated twice)';

CREATE TABLE pm.shotgun_adapter_aliquot (
	shotgun_adapter_aliquot_id bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	limit_freeze_thaw_cycles integer  NOT NULL,
	CONSTRAINT pk_shotgun_adapter_aliquot PRIMARY KEY ( shotgun_adapter_aliquot_id ),
	CONSTRAINT idx_adapter_aliquot UNIQUE ( name )
 );

CREATE TABLE pm.shotgun_index_aliquot (
	shotgun_index_aliquot_id bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	limit_freeze_thaw_cycles bigint  NOT NULL,
	CONSTRAINT pk_index_aliquot PRIMARY KEY ( shotgun_index_aliquot_id ),
	CONSTRAINT idx_index_aliquot UNIQUE ( name )
 );

CREATE TABLE pm.shotgun_index_tech (
	shotgun_index_tech_id bigserial  NOT NULL,
	name                 varchar(100)  ,
	dual_index           bool  ,
	i5_i7_sameplate      bool  ,
	last_index_idx       integer  ,
	CONSTRAINT pk_shotgun_index_tech PRIMARY KEY ( shotgun_index_tech_id )
 );

CREATE TABLE pm.shotgun_library_prep_kit (
	shotgun_library_prep_kit_id bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_shotgun_library_prep_kit PRIMARY KEY ( shotgun_library_prep_kit_id ),
	CONSTRAINT idx_shotgun_library_prep_kit UNIQUE ( name )
 );

CREATE TABLE pm.shotgun_plate (
	shotgun_plate_id     bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	created_on           timestamp  NOT NULL,
	user_id              bigint  NOT NULL,
	processing_robot_id  bigint  NOT NULL,
	plate_type_id        bigint  NOT NULL,
	volume               real  NOT NULL,
	dna_quantification_date timestamp  ,
	dna_quantification_email varchar  ,
	dna_quantification_volume real  ,
	plate_reader_id      bigint  ,
	CONSTRAINT pk_shotgun_plate PRIMARY KEY ( shotgun_plate_id ),
	CONSTRAINT idx_shotgun_plate UNIQUE ( name )
 );

CREATE INDEX idx_shotgun_plate_1 ON pm.shotgun_plate ( processing_robot_id );

CREATE INDEX idx_shotgun_plate_2 ON pm.shotgun_plate ( plate_type_id );

CREATE INDEX idx_shotgun_plate_3 ON pm.shotgun_plate ( dna_quantification_email );

CREATE INDEX idx_shotgun_plate_4 ON pm.shotgun_plate ( plate_reader_id );

CREATE INDEX idx_shotgun_plate_5 ON pm.shotgun_plate ( user_id );

CREATE TABLE pm.shotgun_plate_layout (
	shotgun_plate_id     bigint  NOT NULL,
	sample_id            varchar  NOT NULL,
	"row"                integer  NOT NULL,
	col                  integer  NOT NULL,
	name                 varchar  ,
	notes                varchar  ,
	dna_concentration    real
 );

CREATE INDEX idx_shotgun_plate_layout ON pm.shotgun_plate_layout ( shotgun_plate_id );

CREATE INDEX idx_shotgun_plate_layout_0 ON pm.shotgun_plate_layout ( sample_id );

CREATE TABLE pm.shotgun_pool (
	shotgun_pool_id      bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	echo_id              bigint  NOT NULL,
	discarded            bool DEFAULT false NOT NULL,
	CONSTRAINT pk_shotgun_pool PRIMARY KEY ( shotgun_pool_id ),
	CONSTRAINT idx_shotgun_pool UNIQUE ( name )
 );

CREATE INDEX idx_shotgun_pool_0 ON pm.shotgun_pool ( echo_id );

CREATE TABLE pm.study (
	study_id             bigint  NOT NULL,
	title                varchar  NOT NULL,
	"alias"              varchar  NOT NULL,
	jira_id              varchar  NOT NULL,
	CONSTRAINT pk_study PRIMARY KEY ( study_id ),
	CONSTRAINT uq_jira_id UNIQUE ( jira_id ) ,
	CONSTRAINT uq_study_title UNIQUE ( title )
 );

CREATE TABLE pm.study_sample (
	study_id             bigint  NOT NULL,
	sample_id            varchar  NOT NULL
 );

CREATE INDEX idx_study_sample_sample_id ON pm.study_sample ( sample_id );

CREATE INDEX idx_study_sample_study_id ON pm.study_sample ( study_id );

CREATE TABLE pm.targeted_primer_plate (
	targeted_primer_plate_id bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	plate_type_id        bigint  NOT NULL,
	notes                varchar  ,
	linker_primer_sequence varchar  NOT NULL,
	target_gene          "pm"."target_region"  NOT NULL,
	target_subfragment   "pm"."target_subfragment"  NOT NULL,
	CONSTRAINT pk_targeted_primer_plate PRIMARY KEY ( targeted_primer_plate_id ),
	CONSTRAINT uq_targeted_primer_plate_name UNIQUE ( name )
 );

CREATE INDEX idx_targeted_primer_plate_plate_type_id ON pm.targeted_primer_plate ( plate_type_id );

CREATE TABLE pm.targeted_primer_plate_layout (
	targeted_primer_plate_id bigint  NOT NULL,
	col                  smallint  NOT NULL,
	"row"                smallint  NOT NULL,
	barcode_sequence     varchar  NOT NULL
 );

CREATE INDEX idx_targeted_primer_plate_layout_targeted_primer_plate_id ON pm.targeted_primer_plate_layout ( targeted_primer_plate_id );

CREATE TABLE pm.tm300_8_tool (
	tm300_8_tool_id      bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_tm300_8_tool PRIMARY KEY ( tm300_8_tool_id ),
	CONSTRAINT uq_tm300_8_tool_name UNIQUE ( name )
 );

CREATE TABLE pm.tm50_8_tool (
	tm50_8_tool_id       bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_tm50_8_tool PRIMARY KEY ( tm50_8_tool_id ),
	CONSTRAINT uq_tm50_8_tool_name UNIQUE ( name )
 );

CREATE TABLE pm.water_lot (
	water_lot_id         bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_water_lot PRIMARY KEY ( water_lot_id ),
	CONSTRAINT uq_water_lot_name UNIQUE ( name )
 );

CREATE TABLE pm.dna_plate (
	dna_plate_id         bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	user_id              bigint  NOT NULL,
	created_on           timestamp  ,
	sample_plate_id      bigint  NOT NULL,
	extraction_robot_id  bigint  NOT NULL,
	extraction_kit_lot_id bigint  NOT NULL,
	extraction_tool_id   bigint  NOT NULL,
	notes                varchar  ,
	CONSTRAINT pk_dna_plate PRIMARY KEY ( dna_plate_id ),
	CONSTRAINT uq_dna_plate_name UNIQUE ( name )
 );

CREATE INDEX idx_dna_plate_extraction_kit_lot_id ON pm.dna_plate ( extraction_kit_lot_id );

CREATE INDEX idx_dna_plate_extraction_robot_id ON pm.dna_plate ( extraction_robot_id );

CREATE INDEX idx_dna_plate_extraction_tool_id ON pm.dna_plate ( extraction_tool_id );

CREATE INDEX idx_dna_plate_sample_plate_id ON pm.dna_plate ( sample_plate_id );

CREATE INDEX idx_dna_plate ON pm.dna_plate ( user_id );

CREATE TABLE pm.dna_plate_well_values (
	dna_plate_id         bigint  NOT NULL,
	"row"                integer  NOT NULL,
	col                  integer  NOT NULL,
	dna_concentration    real  NOT NULL
 );

CREATE INDEX idx_dna_plate_well_values ON pm.dna_plate_well_values ( dna_plate_id );

CREATE TABLE pm.sample_plate_study (
	sample_plate_id      bigint  NOT NULL,
	study_id             bigint  NOT NULL
 );

CREATE INDEX idx_sample_plate_study_sample_plate ON pm.sample_plate_study ( sample_plate_id );

CREATE INDEX idx_sample_plate_study_study_id ON pm.sample_plate_study ( study_id );

CREATE TABLE pm.shotgun_index (
	shotgun_index_id     bigserial  NOT NULL,
	i7_name              varchar  ,
	i7_bases             varchar  ,
	i7_row               integer  ,
	i7_col               integer  ,
	i5_name              varchar  ,
	i5_bases             varchar  ,
	i5_row               integer  ,
	i5_col               integer  ,
	shotgun_index_tech_id bigint  ,
	CONSTRAINT idx_shotgun_index PRIMARY KEY ( shotgun_index_id )
 );

CREATE INDEX idx_shotgun_index_0 ON pm.shotgun_index ( shotgun_index_tech_id );

CREATE TABLE pm.shotgun_normalized_plate (
	shotgun_normalized_plate_id bigserial  NOT NULL,
	shotgun_plate_id     bigint  NOT NULL,
	created_on           timestamp  NOT NULL,
	email                varchar  NOT NULL,
	echo_id              bigint  NOT NULL,
	lp_date              timestamp  ,
	lp_email             varchar  ,
	mosquito             bigint  ,
	shotgun_library_prep_kit_id bigint  ,
	shotgun_adapter_aliquot_id bigint  ,
	qpcr_date            timestamp  ,
	qpcr_email           varchar  ,
	qpcr_std_ladder      varchar  ,
	qpcr_id              bigint  ,
	discarded            bool DEFAULT false NOT NULL,
	CONSTRAINT pk_shotgun_normalized_plate PRIMARY KEY ( shotgun_normalized_plate_id )
 );

CREATE INDEX idx_shotgun_normalized_plate ON pm.shotgun_normalized_plate ( shotgun_plate_id );

CREATE INDEX idx_shotgun_normalized_plate_0 ON pm.shotgun_normalized_plate ( email );

CREATE INDEX idx_shotgun_normalized_plate_1 ON pm.shotgun_normalized_plate ( echo_id );

CREATE INDEX idx_shotgun_normalized_plate_2 ON pm.shotgun_normalized_plate ( lp_email );

CREATE INDEX idx_shotgun_normalized_plate_3 ON pm.shotgun_normalized_plate ( mosquito );

CREATE INDEX idx_shotgun_normalized_plate_4 ON pm.shotgun_normalized_plate ( shotgun_library_prep_kit_id );

CREATE INDEX idx_shotgun_normalized_plate_5 ON pm.shotgun_normalized_plate ( shotgun_adapter_aliquot_id );

CREATE INDEX idx_shotgun_normalized_plate_6 ON pm.shotgun_normalized_plate ( qpcr_email );

CREATE INDEX idx_shotgun_normalized_plate_7 ON pm.shotgun_normalized_plate ( qpcr_id );

CREATE TABLE pm.shotgun_normalized_plate_well_values (
	shotgun_normalized_plate_id bigint  NOT NULL,
	"row"                integer  NOT NULL,
	col                  integer  NOT NULL,
	sample_volume_nl     real  NOT NULL,
	water_volume_nl      real  NOT NULL,
	qpcr_concentration   real  ,
	qpcr_cp              real  ,
	shotgun_index_id     bigint  ,
	shotgun_index_aliquot bigint
 );

CREATE INDEX idx_shotgun_normalized_plate_well_values ON pm.shotgun_normalized_plate_well_values ( shotgun_index_aliquot );

CREATE INDEX idx_shotgun_normalized_plate_well_values_0 ON pm.shotgun_normalized_plate_well_values ( shotgun_index_id );

CREATE INDEX idx_wgs_normalized_plate_well_values ON pm.shotgun_normalized_plate_well_values ( shotgun_normalized_plate_id );

CREATE TABLE pm.shotgun_pool_plate (
	shotgun_pool_plate_id bigserial  NOT NULL,
	shotgun_pool_id      bigint  NOT NULL,
	shotgun_normalized_plate_id bigint  NOT NULL,
	CONSTRAINT pk_shotgun_pool_plate PRIMARY KEY ( shotgun_pool_plate_id ),
	CONSTRAINT idx_shotgun_pool_plate UNIQUE ( shotgun_pool_id, shotgun_normalized_plate_id )
 );

CREATE INDEX idx_shotgun_pool_plate_0 ON pm.shotgun_pool_plate ( shotgun_pool_id );

CREATE INDEX idx_shotgun_pool_plate_1 ON pm.shotgun_pool_plate ( shotgun_normalized_plate_id );

CREATE TABLE pm.shotgun_pool_plate_well_values (
	shotgun_pool_plate_id bigint  NOT NULL,
	"row"                integer  NOT NULL,
	col                  integer  NOT NULL,
	sample_volume_nl     real  NOT NULL
 );

CREATE INDEX idx_shotgun_pool_plate_well_values ON pm.shotgun_pool_plate_well_values ( shotgun_pool_plate_id );

CREATE TABLE pm.targeted_plate (
	targeted_plate_id    bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	created_on           timestamp  NOT NULL,
	user_id              bigint  NOT NULL,
	dna_plate_id         bigint  NOT NULL,
	targeted_primer_plate_id bigint  NOT NULL,
	master_mix_lot_id    bigint  NOT NULL,
	tm300_8_tool_id      bigint  NOT NULL,
	tm50_8_tool_id       bigint  NOT NULL,
	water_lot_id         bigint  NOT NULL,
	processing_robot_id  bigint  NOT NULL,
	discarded            bool DEFAULT false NOT NULL,
	CONSTRAINT pk_targeted_plate PRIMARY KEY ( targeted_plate_id ),
	CONSTRAINT idx_targeted_plate UNIQUE ( name )
 );

CREATE INDEX idx_targeted_plate_1 ON pm.targeted_plate ( dna_plate_id );

CREATE INDEX idx_targeted_plate_2 ON pm.targeted_plate ( targeted_primer_plate_id );

CREATE INDEX idx_targeted_plate_3 ON pm.targeted_plate ( master_mix_lot_id );

CREATE INDEX idx_targeted_plate_4 ON pm.targeted_plate ( tm300_8_tool_id );

CREATE INDEX idx_targeted_plate_5 ON pm.targeted_plate ( tm50_8_tool_id );

CREATE INDEX idx_targeted_plate_6 ON pm.targeted_plate ( water_lot_id );

CREATE INDEX idx_targeted_plate_7 ON pm.targeted_plate ( processing_robot_id );

CREATE INDEX idx_targeted_plate_8 ON pm.targeted_plate ( user_id );

CREATE TABLE pm.targeted_plate_well_values (
	targeted_plate_id    bigint  ,
	"row"                integer  NOT NULL,
	col                  integer  NOT NULL,
	raw_concentration    real  NOT NULL,
	mod_concentration    real
 );

CREATE INDEX idx_targeted_plate_well_values ON pm.targeted_plate_well_values ( targeted_plate_id );

CREATE TABLE pm.targeted_pool (
	targeted_pool_id     bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	targeted_plate_id    bigint  NOT NULL,
	volume               real  NOT NULL,
	discarded            bool DEFAULT false NOT NULL,
	CONSTRAINT pk_targeted_pool PRIMARY KEY ( targeted_pool_id ),
	CONSTRAINT idx_targeted_pool UNIQUE ( name )
 );

CREATE INDEX idx_target_gene_pool_0 ON pm.targeted_pool ( targeted_plate_id );

CREATE TABLE pm.condensed_plates (
	shotgun_plate_id     bigint  NOT NULL,
	dna_plate_id         bigint  NOT NULL,
	"position"           integer  NOT NULL,
	CONSTRAINT condensed_plates_pkey PRIMARY KEY ( shotgun_plate_id, dna_plate_id, "position" )
 );

CREATE INDEX idx_condensed_plates_0 ON pm.condensed_plates ( shotgun_plate_id );

CREATE INDEX idx_condensed_plates_1 ON pm.condensed_plates ( dna_plate_id );

CREATE TABLE pm.protocol_run_pool (
	run_pool_id          bigint  NOT NULL,
	shotgun_pool_id      bigint  ,
	targeted_pool_id     bigint  ,
	percentage           real
 );

CREATE INDEX idx_protocol_run_pool ON pm.protocol_run_pool ( shotgun_pool_id );

CREATE INDEX idx_protocol_run_pool_0 ON pm.protocol_run_pool ( targeted_pool_id );

CREATE INDEX idx_protocol_run_pool_1 ON pm.protocol_run_pool ( run_pool_id );

CREATE TABLE study.sample (
	sample_id            varchar  NOT NULL,
	physical_name        varchar  ,
	is_blank             bool DEFAULT false NOT NULL,
	details              varchar  ,
	notes                varchar  ,
	CONSTRAINT sample_pkey PRIMARY KEY ( sample_id )
 );

CREATE TABLE study.service (
	service_id           bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	url                  varchar  NOT NULL,
	credentials          json  NOT NULL,
	CONSTRAINT service_pkey PRIMARY KEY ( service_id )
 );

CREATE TABLE study.study (
	study_id             bigserial  NOT NULL,
	title                varchar  NOT NULL,
	creator              varchar  NOT NULL,
	created_timestamp    timestamp  NOT NULL,
	qiita_study_id       bigint  ,
	jira_key             varchar  ,
	CONSTRAINT study_pkey PRIMARY KEY ( study_id )
 );

CREATE TABLE study.study_communication_backlog (
	study_id             bigserial  NOT NULL,
	service_id           bigserial  NOT NULL,
	"action"             varchar  NOT NULL,
	attributes           json  NOT NULL,
	status               varchar  NOT NULL,
	error_message        varchar
 );

COMMENT ON TABLE study.study_communication_backlog IS 'field status is enum field of pending or error';

CREATE TABLE study.study_sample (
	study_id             bigserial  NOT NULL,
	sample_id            varchar  NOT NULL
 );

CREATE TABLE users.access_level (
	access_level_id      bigserial  NOT NULL,
	access_level         varchar  NOT NULL,
	description          varchar  NOT NULL,
	CONSTRAINT access_level_pkey PRIMARY KEY ( access_level_id )
 );

CREATE TABLE users."user" (
	user_id              bigserial  NOT NULL,
	name                 varchar  NOT NULL,
	email                varchar  NOT NULL,
	CONSTRAINT user_pkey PRIMARY KEY ( user_id )
 );

CREATE TABLE users.user_access_level (
	access_level_id      integer  NOT NULL,
	user_id              integer  NOT NULL,
	CONSTRAINT user_access_level_pkey PRIMARY KEY ( access_level_id )
 );

CREATE OR REPLACE FUNCTION pm.plate_sample_test()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Check that the sample being plated actually belongs to a study
    -- linked to the plate
    IF (SELECT study_id FROM pm.study_sample WHERE sample_id = NEW.sample_id) NOT IN (SELECT DISTINCT study_id FROM pm.sample_plate_study WHERE sample_plate_id = NEW.sample_plate_id) THEN
        RAISE EXCEPTION 'Sample % does not belong to a study being plated in %', NEW.sample_id, NEW.sample_plate_id;
    END IF;
    RETURN NEW;
END;
$function$;

ALTER TABLE pm.condensed_plates ADD CONSTRAINT fk_condensed_plates_dna_plate FOREIGN KEY ( dna_plate_id ) REFERENCES pm.dna_plate( dna_plate_id );

COMMENT ON CONSTRAINT fk_condensed_plates_dna_plate ON pm.condensed_plates IS '';

ALTER TABLE pm.condensed_plates ADD CONSTRAINT fk_condensed_plates FOREIGN KEY ( shotgun_plate_id ) REFERENCES pm.shotgun_plate( shotgun_plate_id );

COMMENT ON CONSTRAINT fk_condensed_plates ON pm.condensed_plates IS '';

ALTER TABLE pm.dna_plate ADD CONSTRAINT fk_dna_plate FOREIGN KEY ( extraction_kit_lot_id ) REFERENCES pm.extraction_kit_lot( extraction_kit_lot_id );

COMMENT ON CONSTRAINT fk_dna_plate ON pm.dna_plate IS '';

ALTER TABLE pm.dna_plate ADD CONSTRAINT fk_dna_plate_extraction_robot FOREIGN KEY ( extraction_robot_id ) REFERENCES pm.extraction_robot( extraction_robot_id );

COMMENT ON CONSTRAINT fk_dna_plate_extraction_robot ON pm.dna_plate IS '';

ALTER TABLE pm.dna_plate ADD CONSTRAINT fk_dna_plate_extraction_tool FOREIGN KEY ( extraction_tool_id ) REFERENCES pm.extraction_tool( extraction_tool_id );

COMMENT ON CONSTRAINT fk_dna_plate_extraction_tool ON pm.dna_plate IS '';

ALTER TABLE pm.dna_plate ADD CONSTRAINT fk_dna_plate_sample_plate FOREIGN KEY ( sample_plate_id ) REFERENCES pm.sample_plate( sample_plate_id );

COMMENT ON CONSTRAINT fk_dna_plate_sample_plate ON pm.dna_plate IS '';

ALTER TABLE pm.dna_plate ADD CONSTRAINT fk_dna_plate_user FOREIGN KEY ( user_id ) REFERENCES users."user"( user_id );

COMMENT ON CONSTRAINT fk_dna_plate_user ON pm.dna_plate IS '';

ALTER TABLE pm.dna_plate_well_values ADD CONSTRAINT fk_dna_plate_well_values FOREIGN KEY ( dna_plate_id ) REFERENCES pm.dna_plate( dna_plate_id );

COMMENT ON CONSTRAINT fk_dna_plate_well_values ON pm.dna_plate_well_values IS '';

ALTER TABLE pm.protocol_run_pool ADD CONSTRAINT fk_protocol_run_pool_run_pool FOREIGN KEY ( run_pool_id ) REFERENCES pm.run_pool( run_pool_id );

COMMENT ON CONSTRAINT fk_protocol_run_pool_run_pool ON pm.protocol_run_pool IS '';

ALTER TABLE pm.protocol_run_pool ADD CONSTRAINT fk_protocol_run_pool_shotgun_pool FOREIGN KEY ( shotgun_pool_id ) REFERENCES pm.shotgun_pool( shotgun_pool_id );

COMMENT ON CONSTRAINT fk_protocol_run_pool_shotgun_pool ON pm.protocol_run_pool IS '';

ALTER TABLE pm.protocol_run_pool ADD CONSTRAINT fk_protocol_run_pool_targeted_pool_tg FOREIGN KEY ( targeted_pool_id ) REFERENCES pm.targeted_pool( targeted_pool_id );

COMMENT ON CONSTRAINT fk_protocol_run_pool_targeted_pool_tg ON pm.protocol_run_pool IS '';

ALTER TABLE pm.sample_plate ADD CONSTRAINT fk_sample_plate_plate_type FOREIGN KEY ( plate_type_id ) REFERENCES pm.plate_type( plate_type_id );

COMMENT ON CONSTRAINT fk_sample_plate_plate_type ON pm.sample_plate IS '';

ALTER TABLE pm.sample_plate ADD CONSTRAINT fk_sample_plate_user FOREIGN KEY ( user_id ) REFERENCES users."user"( user_id );

COMMENT ON CONSTRAINT fk_sample_plate_user ON pm.sample_plate IS '';

ALTER TABLE pm.sample_plate_layout ADD CONSTRAINT fk_plate_map_sample FOREIGN KEY ( sample_id ) REFERENCES pm.sample( sample_id );

COMMENT ON CONSTRAINT fk_plate_map_sample ON pm.sample_plate_layout IS '';

ALTER TABLE pm.sample_plate_layout ADD CONSTRAINT fk_plate_map_sample_plate FOREIGN KEY ( sample_plate_id ) REFERENCES pm.sample_plate( sample_plate_id );

COMMENT ON CONSTRAINT fk_plate_map_sample_plate ON pm.sample_plate_layout IS '';

ALTER TABLE pm.sample_plate_study ADD CONSTRAINT fk_sample_plate_study FOREIGN KEY ( sample_plate_id ) REFERENCES pm.sample_plate( sample_plate_id );

COMMENT ON CONSTRAINT fk_sample_plate_study ON pm.sample_plate_study IS '';

ALTER TABLE pm.sample_plate_study ADD CONSTRAINT fk_sample_plate_study_study FOREIGN KEY ( study_id ) REFERENCES pm.study( study_id );

COMMENT ON CONSTRAINT fk_sample_plate_study_study ON pm.sample_plate_study IS '';

ALTER TABLE pm.shotgun_index ADD CONSTRAINT fk_shotgun_index_shotgun_index_tech FOREIGN KEY ( shotgun_index_tech_id ) REFERENCES pm.shotgun_index_tech( shotgun_index_tech_id );

COMMENT ON CONSTRAINT fk_shotgun_index_shotgun_index_tech ON pm.shotgun_index IS '';

ALTER TABLE pm.shotgun_normalized_plate ADD CONSTRAINT fk_shotgun_normalized_plate_echo FOREIGN KEY ( echo_id ) REFERENCES pm.echo( echo_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_echo ON pm.shotgun_normalized_plate IS '';

ALTER TABLE pm.shotgun_normalized_plate ADD CONSTRAINT fk_shotgun_normalized_plate_mosquito FOREIGN KEY ( mosquito ) REFERENCES pm.mosquito( mosquito_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_mosquito ON pm.shotgun_normalized_plate IS '';

ALTER TABLE pm.shotgun_normalized_plate ADD CONSTRAINT fk_shotgun_normalized_plate_qpcr FOREIGN KEY ( qpcr_id ) REFERENCES pm.qpcr( qpcr_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_qpcr ON pm.shotgun_normalized_plate IS '';

ALTER TABLE pm.shotgun_normalized_plate ADD CONSTRAINT fk_shotgun_normalized_plate_adapter FOREIGN KEY ( shotgun_adapter_aliquot_id ) REFERENCES pm.shotgun_adapter_aliquot( shotgun_adapter_aliquot_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_adapter ON pm.shotgun_normalized_plate IS '';

ALTER TABLE pm.shotgun_normalized_plate ADD CONSTRAINT fk_shotgun_normalized_plate_kit FOREIGN KEY ( shotgun_library_prep_kit_id ) REFERENCES pm.shotgun_library_prep_kit( shotgun_library_prep_kit_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_kit ON pm.shotgun_normalized_plate IS '';

ALTER TABLE pm.shotgun_normalized_plate ADD CONSTRAINT fk_shotgun_normalized_plate FOREIGN KEY ( shotgun_plate_id ) REFERENCES pm.shotgun_plate( shotgun_plate_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate ON pm.shotgun_normalized_plate IS '';

ALTER TABLE pm.shotgun_normalized_plate_well_values ADD CONSTRAINT fk_shotgun_normalized_plate_well_values FOREIGN KEY ( shotgun_index_id ) REFERENCES pm.shotgun_index( shotgun_index_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_well_values ON pm.shotgun_normalized_plate_well_values IS '';

ALTER TABLE pm.shotgun_normalized_plate_well_values ADD CONSTRAINT fk_shotgun_normalized_plate_well_values_aliquot FOREIGN KEY ( shotgun_index_aliquot ) REFERENCES pm.shotgun_index_aliquot( shotgun_index_aliquot_id );

COMMENT ON CONSTRAINT fk_shotgun_normalized_plate_well_values_aliquot ON pm.shotgun_normalized_plate_well_values IS '';

ALTER TABLE pm.shotgun_normalized_plate_well_values ADD CONSTRAINT fk_wgs_normalized_plate_well_values FOREIGN KEY ( shotgun_normalized_plate_id ) REFERENCES pm.shotgun_normalized_plate( shotgun_normalized_plate_id );

COMMENT ON CONSTRAINT fk_wgs_normalized_plate_well_values ON pm.shotgun_normalized_plate_well_values IS '';

ALTER TABLE pm.shotgun_plate ADD CONSTRAINT fk_shotgun_plate_reader FOREIGN KEY ( plate_reader_id ) REFERENCES pm.plate_reader( plate_reader_id );

COMMENT ON CONSTRAINT fk_shotgun_plate_reader ON pm.shotgun_plate IS '';

ALTER TABLE pm.shotgun_plate ADD CONSTRAINT fk_shotgun_plate_type FOREIGN KEY ( plate_type_id ) REFERENCES pm.plate_type( plate_type_id );

COMMENT ON CONSTRAINT fk_shotgun_plate_type ON pm.shotgun_plate IS '';

ALTER TABLE pm.shotgun_plate ADD CONSTRAINT fk_shotgun_plate_prc_robot FOREIGN KEY ( processing_robot_id ) REFERENCES pm.processing_robot( processing_robot_id );

COMMENT ON CONSTRAINT fk_shotgun_plate_prc_robot ON pm.shotgun_plate IS '';

ALTER TABLE pm.shotgun_plate ADD CONSTRAINT fk_shotgun_plate_user FOREIGN KEY ( user_id ) REFERENCES users."user"( user_id );

COMMENT ON CONSTRAINT fk_shotgun_plate_user ON pm.shotgun_plate IS '';

ALTER TABLE pm.shotgun_plate_layout ADD CONSTRAINT fk_shotgun_plate_layout_sample FOREIGN KEY ( sample_id ) REFERENCES pm.sample( sample_id );

COMMENT ON CONSTRAINT fk_shotgun_plate_layout_sample ON pm.shotgun_plate_layout IS '';

ALTER TABLE pm.shotgun_plate_layout ADD CONSTRAINT fk_shotgun_plate_layout FOREIGN KEY ( shotgun_plate_id ) REFERENCES pm.shotgun_plate( shotgun_plate_id );

COMMENT ON CONSTRAINT fk_shotgun_plate_layout ON pm.shotgun_plate_layout IS '';

ALTER TABLE pm.shotgun_pool ADD CONSTRAINT fk_shotgun_pool_echo FOREIGN KEY ( echo_id ) REFERENCES pm.echo( echo_id );

COMMENT ON CONSTRAINT fk_shotgun_pool_echo ON pm.shotgun_pool IS '';

ALTER TABLE pm.shotgun_pool_plate ADD CONSTRAINT fk_shotgun_pool_plate FOREIGN KEY ( shotgun_normalized_plate_id ) REFERENCES pm.shotgun_normalized_plate( shotgun_normalized_plate_id );

COMMENT ON CONSTRAINT fk_shotgun_pool_plate ON pm.shotgun_pool_plate IS '';

ALTER TABLE pm.shotgun_pool_plate ADD CONSTRAINT fk_shotgun_pool_plate_shotgun_pool FOREIGN KEY ( shotgun_pool_id ) REFERENCES pm.shotgun_pool( shotgun_pool_id );

COMMENT ON CONSTRAINT fk_shotgun_pool_plate_shotgun_pool ON pm.shotgun_pool_plate IS '';

ALTER TABLE pm.shotgun_pool_plate_well_values ADD CONSTRAINT fk_shotgun_pool_plate_well_values FOREIGN KEY ( shotgun_pool_plate_id ) REFERENCES pm.shotgun_pool_plate( shotgun_pool_plate_id );

COMMENT ON CONSTRAINT fk_shotgun_pool_plate_well_values ON pm.shotgun_pool_plate_well_values IS '';

ALTER TABLE pm.study_sample ADD CONSTRAINT fk_study_sample_sample_id FOREIGN KEY ( sample_id ) REFERENCES pm.sample( sample_id );

COMMENT ON CONSTRAINT fk_study_sample_sample_id ON pm.study_sample IS '';

ALTER TABLE pm.study_sample ADD CONSTRAINT fk_study_sample_study_id FOREIGN KEY ( study_id ) REFERENCES pm.study( study_id );

COMMENT ON CONSTRAINT fk_study_sample_study_id ON pm.study_sample IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_targeted_plate_dna_plate FOREIGN KEY ( dna_plate_id ) REFERENCES pm.dna_plate( dna_plate_id );

COMMENT ON CONSTRAINT fk_targeted_plate_dna_plate ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_target_gene_master_mix FOREIGN KEY ( master_mix_lot_id ) REFERENCES pm.master_mix_lot( master_mix_lot_id );

COMMENT ON CONSTRAINT fk_target_gene_master_mix ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_targeted_plate_robot FOREIGN KEY ( processing_robot_id ) REFERENCES pm.processing_robot( processing_robot_id );

COMMENT ON CONSTRAINT fk_targeted_plate_robot ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_target_gene_tm300_tool FOREIGN KEY ( tm300_8_tool_id ) REFERENCES pm.tm300_8_tool( tm300_8_tool_id );

COMMENT ON CONSTRAINT fk_target_gene_tm300_tool ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_targeted_plate_tm50_8_tool FOREIGN KEY ( tm50_8_tool_id ) REFERENCES pm.tm50_8_tool( tm50_8_tool_id );

COMMENT ON CONSTRAINT fk_targeted_plate_tm50_8_tool ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_targeted_plate_water_lot FOREIGN KEY ( water_lot_id ) REFERENCES pm.water_lot( water_lot_id );

COMMENT ON CONSTRAINT fk_targeted_plate_water_lot ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT fk_target_gene_barcode FOREIGN KEY ( targeted_primer_plate_id ) REFERENCES pm.targeted_primer_plate( targeted_primer_plate_id );

COMMENT ON CONSTRAINT fk_target_gene_barcode ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate ADD CONSTRAINT user_id FOREIGN KEY ( user_id ) REFERENCES users."user"( user_id );

COMMENT ON CONSTRAINT user_id ON pm.targeted_plate IS '';

ALTER TABLE pm.targeted_plate_well_values ADD CONSTRAINT fk_fadfasf_targeted_plate FOREIGN KEY ( targeted_plate_id ) REFERENCES pm.targeted_plate( targeted_plate_id );

COMMENT ON CONSTRAINT fk_fadfasf_targeted_plate ON pm.targeted_plate_well_values IS '';

ALTER TABLE pm.targeted_pool ADD CONSTRAINT fk_target_gene_pool FOREIGN KEY ( targeted_plate_id ) REFERENCES pm.targeted_plate( targeted_plate_id );

COMMENT ON CONSTRAINT fk_target_gene_pool ON pm.targeted_pool IS '';

ALTER TABLE pm.targeted_primer_plate ADD CONSTRAINT fk_template_plate_type_id FOREIGN KEY ( plate_type_id ) REFERENCES pm.plate_type( plate_type_id );

COMMENT ON CONSTRAINT fk_template_plate_type_id ON pm.targeted_primer_plate IS '';

ALTER TABLE pm.targeted_primer_plate_layout ADD CONSTRAINT fk_template_barcode_seq_template_id FOREIGN KEY ( targeted_primer_plate_id ) REFERENCES pm.targeted_primer_plate( targeted_primer_plate_id );

COMMENT ON CONSTRAINT fk_template_barcode_seq_template_id ON pm.targeted_primer_plate_layout IS '';

ALTER TABLE study.study_communication_backlog ADD CONSTRAINT service_id FOREIGN KEY ( service_id ) REFERENCES study.service( service_id );

COMMENT ON CONSTRAINT service_id ON study.study_communication_backlog IS '';

ALTER TABLE study.study_communication_backlog ADD CONSTRAINT study_id FOREIGN KEY ( study_id ) REFERENCES study.study( study_id );

COMMENT ON CONSTRAINT study_id ON study.study_communication_backlog IS '';

ALTER TABLE study.study_sample ADD CONSTRAINT sample_id FOREIGN KEY ( sample_id ) REFERENCES study.sample( sample_id );

COMMENT ON CONSTRAINT sample_id ON study.study_sample IS '';

ALTER TABLE study.study_sample ADD CONSTRAINT study_id FOREIGN KEY ( study_id ) REFERENCES study.study( study_id );

COMMENT ON CONSTRAINT study_id ON study.study_sample IS '';

ALTER TABLE users.user_access_level ADD CONSTRAINT access_level_id FOREIGN KEY ( access_level_id ) REFERENCES users.access_level( access_level_id );

COMMENT ON CONSTRAINT access_level_id ON users.user_access_level IS '';

ALTER TABLE users.user_access_level ADD CONSTRAINT user_id FOREIGN KEY ( user_id ) REFERENCES users."user"( user_id );

COMMENT ON CONSTRAINT user_id ON users.user_access_level IS '';
