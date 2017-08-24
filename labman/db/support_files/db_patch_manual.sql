ALTER TABLE labman.gdna_well ADD CONSTRAINT fk_gdna_well_gdna_content_id FOREIGN KEY ( content_id ) REFERENCES qiita.study_sample( sample_id );
