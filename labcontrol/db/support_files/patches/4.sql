-- August 30, 2019
-- Create table to keep track of library prep kit type
CREATE TABLE labcontrol.shotgun_library_prep_kit_type (
    library_prep_kit_type_id SERIAL NOT NULL,
    description          varchar(100)  NOT NULL,
    CONSTRAINT pk_kit PRIMARY KEY ( library_prep_kit_type_id )
);

-- Currently the only two options for library prep kit types.
INSERT INTO labcontrol.shotgun_library_prep_kit_type (description) VALUES ('Kapa');
INSERT INTO labcontrol.shotgun_library_prep_kit_type (description) VALUES ('Nextera');

-- TODO 503 add column to labcontrol.library_prep_shotgun_process ?
