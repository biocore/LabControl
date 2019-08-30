-- August 30, 2019
-- Create table to keep track of library prep kit type
CREATE TABLE labcontrol.library_prep_shotgun_kit_type (
    library_prep_shotgun_kit_type_id SERIAL NOT NULL,
    description varchar(100) NOT NULL,
    CONSTRAINT pk_library_prep_shotgun_kit PRIMARY KEY ( library_prep_shotgun_kit_type_id ),
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
