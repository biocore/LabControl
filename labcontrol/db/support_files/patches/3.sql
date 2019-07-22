-- July 22, 2019
-- Adding a new table to record assay types

CREATE TABLE labcontrol.assay_type (
    assay_type_id       SERIAL PRIMARY KEY,
    description         varchar(1000)
);

COMMENT ON TABLE labcontrol.assay_type IS 'List of assay types. Add future types here as they become available';

ALTER TABLE labcontrol.process ADD COLUMN assay_type_id INTEGER;
ALTER TABLE labcontrol.process ADD CONSTRAINT fk_assay_type FOREIGN KEY (assay_type_id) REFERENCES labcontrol.assay_type(assay_type_id);

INSERT INTO labcontrol.assay_type (description) VALUES ('Amplicon');
INSERT INTO labcontrol.assay_type (description) VALUES ('Metagenomics');
