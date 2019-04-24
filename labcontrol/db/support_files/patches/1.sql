-- April 2, 2019
-- Implicitly track the date and time of plate creation
ALTER TABLE labman.plate ADD COLUMN creation_timestamp timestamp NOT NULL default now();
