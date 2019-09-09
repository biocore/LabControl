-- July 23, 2019
-- Create a set of nested views AS an alternative to very large queries
-- comprised of multiple left joins in code.
-- These views are used to map a SequencingProcess's associated
-- PoolComposition's ultimate composition type to the sequencing_process_id.
-- This is used AS a more performant alternative to generating large numbers
-- of Composition objects and iterating through them.
CREATE VIEW labcontrol.vw_map_spid_to_cid AS 
SELECT 
  a.input_composition_id AS composition_id, 
  b.sequencing_process_id 
FROM 
  labcontrol.pool_composition_components a, 
  labcontrol.sequencing_process_lanes b 
WHERE 
  a.output_pool_composition_id = b.pool_composition_id 
ORDER BY 
  b.sequencing_process_id;

CREATE VIEW labcontrol.vw_seq_proc_pool_comp_type_map AS 
SELECT 
  DISTINCT a.composition_type_id, 
  b.sequencing_process_id 
FROM 
  labcontrol.composition a, 
  labcontrol.vw_map_spid_to_cid b 
WHERE 
  a.composition_id = b.composition_id 
UNION 
select 
  DISTINCT a.composition_type_id, 
  b.sequencing_process_id 
FROM 
  labcontrol.composition a, 
  labcontrol.vw_map_spid_to_cid b 
WHERE 
  a.composition_id = b.composition_id 
UNION 
select 
  DISTINCT d.composition_type_id, 
  b.sequencing_process_id 
FROM 
  labcontrol.composition d, 
  labcontrol.pool_composition_components c, 
  labcontrol.pool_composition a, 
  labcontrol.vw_map_spid_to_cid b 
WHERE 
  a.composition_id = b.composition_id 
  and c.output_pool_composition_id = a.pool_composition_id 
  and d.composition_id = c.input_composition_id;

-- As the SequencingProcess no longer has assay (type) AS a property, the
-- legacy column that contained a non-enumerated-type (bare-string) can and
-- should be removed here, to prevent its continued use.
ALTER TABLE labcontrol.sequencing_process DROP COLUMN assay;

-- Note that assay_types are now strings mapped to serial ids and
-- PoolCompositions and SequencingProcesses can reference a legitimate foreign
-- key value now.
CREATE TABLE labcontrol.assay_type (
    assay_type_id SERIAL PRIMARY KEY,
    description VARCHAR
);

-- Currently the only two options (for now).
INSERT INTO labcontrol.assay_type (description) VALUES ('Amplicon');
INSERT INTO labcontrol.assay_type (description) VALUES ('Metagenomics');

-- Previously, a SequencingProcess's assay_type was either 'Amplicon' or
-- 'Metagenomics', based on composition type, hard-coded in different areas.
-- Now, the map between 'Amplicon' and say '16S library prep' is defined
-- explicitly here.
CREATE TABLE labcontrol.comp_to_assay_type_map (
    composition_type_id INTEGER REFERENCES labcontrol.composition_type (composition_type_id),
    assay_type_id INTEGER REFERENCES labcontrol.assay_type (assay_type_id)
);

-- 6,1 maps '16S library prep' to 'Amplicon'
INSERT INTO labcontrol.comp_to_assay_type_map (composition_type_id, assay_type_id) VALUES (6,1);
-- 8,2 maps 'shotgun library prep' to 'Metagenomics'
INSERT INTO labcontrol.comp_to_assay_type_map (composition_type_id, assay_type_id) VALUES (8,2);

-- August 30, 2019
-- Create table to keep track of library prep kit type
CREATE TABLE labcontrol.library_prep_shotgun_kit_type (
    library_prep_shotgun_kit_type_id SERIAL PRIMARY KEY,
    description varchar NOT NULL,
    CONSTRAINT unique_kit_type_description UNIQUE ( description )
);

-- Currently the only two options for library prep kit types.
INSERT INTO labcontrol.library_prep_shotgun_kit_type ( description ) VALUES ('KAPA HyperPlus kit');
INSERT INTO labcontrol.library_prep_shotgun_kit_type ( description ) VALUES ('Nextera kit');

-- add a column to correspond to the kit type and default to 'Kapa' (assumes first value of SERIAL is 1)
-- default here assumes that if nothing is specified, 1 will be taken
ALTER TABLE labcontrol.library_prep_shotgun_process ADD COLUMN library_prep_shotgun_kit_type_id integer NOT NULL DEFAULT 1;
-- make sure that shotgun_process kit_type is indexed on
ALTER TABLE labcontrol.library_prep_shotgun_process
    ADD CONSTRAINT fk_library_prep_shotgun_process_kit_type_id
    FOREIGN KEY ( library_prep_shotgun_kit_type_id )
    REFERENCES labcontrol.library_prep_shotgun_kit_type( library_prep_shotgun_kit_type_id );
