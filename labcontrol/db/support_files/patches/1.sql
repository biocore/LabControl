-- April 2, 2019
-- Implicitly track the date and time of plate creation
ALTER TABLE labcontrol.plate ADD COLUMN creation_timestamp timestamp NOT NULL default now();

-- May 9, 2019
-- Add constraints to existing columns for wells.
ALTER TABLE labcontrol.well ADD CONSTRAINT rowchk CHECK (row_num > 0);
ALTER TABLE labcontrol.well ADD CONSTRAINT colchk CHECK (col_num > 0);
