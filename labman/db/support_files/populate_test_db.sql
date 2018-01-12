-- Controlling for the Ids here is more complex. Hence we are going
-- to populate the DB in a function so we can easily keep track of the
-- ids

DO $do$
DECLARE
    -- General index variables
    idx_row_well                        INT;
    idx_col_well                        INT;
    plate_idx                           INT;
    well_container_type_id              BIGINT;
    tube_container_type_id              BIGINT;

    -- Reagent creation variables
    rc_process_type_id                  BIGINT;
    rc_process_id_ek                    BIGINT;
    rc_process_id_mm                    BIGINT;
    rc_process_id_w                     BIGINT;
    reagent_comp_type                   BIGINT;

    -- Variables for primer working plates
    wpp_process_type_id                 BIGINT;
    wpp_process_id                      BIGINT;
    wpp_emp_primer_set_id               BIGINT;
    wpp_creation_process_id             BIGINT;
    wpp_plate_id                        BIGINT;
    wpp_container_id                    BIGINT;
    wpp_composition_id                  BIGINT;
    primer_composition_type_id          BIGINT;
    microtiter_96_plate_type_id         BIGINT;
    psc_id                              BIGINT;

    -- Variables for sample plating
    plating_process_id                  BIGINT;
    plating_process_type_id             BIGINT;
    deepwell_96_plate_type_id           BIGINT;
    sample_plate_id                     BIGINT;
    plating_container_id                BIGINT;
    sample_comp_type_id                 BIGINT;
    sample_type_id                      BIGINT;
    plating_composition_id              BIGINT;
    plating_sample_comp_type_id         BIGINT;
    plating_sample_id                   VARCHAR;
    vibrio_type_id                      BIGINT;
    blank_type_id                       BIGINT;
    plating_sample_composition_id       BIGINT;

    -- Variables for extraction
    ext_robot_id                        BIGINT;
    ext_kit_container_id                BIGINT;
    ext_kit_reagent_comp_type           BIGINT;
    ext_kit_reagent_composition_id      BIGINT;
    ext_kit_composition_id              BIGINT;
    ext_tool_id                         BIGINT;
    gdna_process_type_id                BIGINT;
    gdna_process_id                     BIGINT;
    gdna_plate_id                       BIGINT;
    gdna_container_id                   BIGINT;
    gdna_comp_id                        BIGINT;
    gdna_comp_type_id                   BIGINT;
    gdna_subcomposition_id              BIGINT;

    -- Variables for 16S library prep
    lib_prep_16s_process_type_id        BIGINT;
    lib_prep_16s_process_id             BIGINT;
    master_mix_container_id             BIGINT;
    master_mix_reagent_comp_type        BIGINT;
    master_mix_composition_id           BIGINT;
    master_mix_reagent_composition_id   BIGINT;
    water_container_id                  BIGINT;
    water_composition_id                BIGINT;
    water_reagent_comp_type             BIGINT;
    water_reagent_composition_id        BIGINT;
    tm300_8_id                          BIGINT;
    tm50_8_id                           BIGINT;
    proc_robot_id                       BIGINT;
    lib_prep_16s_plate_id               BIGINT;
    lib_prep_16s_container_id           BIGINT;
    lib_prep_16s_comp_type_id           BIGINT;
    lib_prep_16s_composition_id         BIGINT;
    primer_comp_id                      BIGINT;

    -- Variables for pico green quantification
    pg_quant_process_type_id            BIGINT;
    pg_quant_process_id                 BIGINT;
    pg_quant_subprocess_id              BIGINT;

    -- Variables for plate pooling creation
    p_pool_process_type_id              BIGINT;
    p_pool_process_id                   BIGINT;
    p_pool_subprocess_id                BIGINT;
    p_pool_container_id                 BIGINT;
    pool_comp_type_id                   BIGINT;
    p_pool_composition_id               BIGINT;
    p_pool_subcomposition_id            BIGINT;

    -- Variables for sequencing pooling creation
    s_pool_process_id                   BIGINT;
    s_pool_subprocess_id                BIGINT;
    s_pool_container_id                 BIGINT;
    s_pool_composition_id               BIGINT;
    s_pool_subcomposition_id            BIGINT;

    -- Variables for sequencing
    sequencing_process_id               BIGINT;
    sequencing_process_type_id          BIGINT;
    sequencer_id                        BIGINT;

    -- Metagenomics variables
    row_pad                             INTEGER;
    col_pad                             INTEGER;
    microtiter_384_plate_type_id        BIGINT;

    -- Variables for gDNA plate compression
    gdna_comp_process_type_id           BIGINT;
    gdna_comp_process_id                BIGINT;
    gdna_comp_container_id              BIGINT;
    gdna_comp_comp_id                   BIGINT;
    gdna_comp_subcomposition_id         BIGINT;
    gdna_comp_plate_id                  BIGINT;
BEGIN
    --------------------------------------------
    -------- CREATE PRIMER WORKING PLATES ------
    --------------------------------------------
    SELECT process_type_id INTO wpp_process_type_id
        FROM qiita.process_type
        WHERE description = 'primer working plate creation';
    -- Populate working primer plate info
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (wpp_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO wpp_process_id;
    -- Populate the primer_working_plate_creation_process
    SELECT primer_set_id INTO wpp_emp_primer_set_id
        FROM qiita.primer_set
        WHERE external_id = 'EMP primer set';
    INSERT INTO qiita.primer_working_plate_creation_process (process_id, primer_set_id, master_set_order_number)
        VALUES (wpp_process_id, wpp_emp_primer_set_id, 'EMP PRIMERS MSON 1')
        RETURNING primer_working_plate_creation_process_id INTO wpp_creation_process_id;

    -- Get the id of the container type "well"
    SELECT container_type_id INTO well_container_type_id
        FROM qiita.container_type
        WHERE description = 'well';

    -- Get the id of the primer composition type
    SELECT composition_type_id INTO primer_composition_type_id
        FROM qiita.composition_type
        WHERE description = 'primer';

    -- Get the id of the 96-well microtiter plate configuration
    SELECT plate_configuration_id INTO microtiter_96_plate_type_id
        FROM qiita.plate_configuration
        WHERE description = '96-well microtiter plate';

    -- We need to create 8 plates, since the structure is the same for
    -- all use a for loop to avoid rewriting stuff
    FOR plate_idx IN 1..8 LOOP
        -- The working primer plates are identifier by the template plate number and the
        -- date they're created. Ther are 96-well microtiter plates
        INSERT INTO qiita.plate (external_id, plate_configuration_id, discarded)
            VALUES ('EMP Primer plate ' || plate_idx::varchar || ' 10/23/2017', microtiter_96_plate_type_id, false)
            RETURNING plate_id INTO wpp_plate_id;

        -- There are 96 well plates - 2 -> well
        FOR idx_row_well IN 1..8 LOOP
            FOR idx_col_well IN 1..12 LOOP
                -- Creating the well information
                INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                    VALUES (well_container_type_id, wpp_process_id, 10)
                    RETURNING container_id INTO wpp_container_id;
                INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                    VALUES (wpp_container_id, wpp_plate_id, idx_row_well, idx_col_well);

                -- Creating the composition information
                INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                    VALUES (primer_composition_type_id, wpp_process_id, wpp_container_id, 10)
                    RETURNING composition_id INTO wpp_composition_id;
                SELECT primer_set_composition_id INTO psc_id
                    FROM qiita.primer_set_composition psc
                        JOIN qiita.composition c USING (composition_id)
                        JOIN qiita.well w USING (container_id)
                        JOIN qiita.plate p USING (plate_id)
                    WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_id = 'EMP primer plate ' || plate_idx;
                INSERT INTO qiita.primer_composition (composition_id, primer_set_composition_id)
                    VALUES (wpp_composition_id, psc_id);
            END LOOP;  -- Column loop
        END LOOP; -- Row loop
    END LOOP; -- Plate loop

    ---------------------------
    ---------------------------
    ------ ADD A 16S RUN ------
    ---------------------------
    ---------------------------

    -- Create reagents composition for all the reagents needed
    SELECT process_type_id INTO rc_process_type_id
        FROM qiita.process_type
        WHERE description = 'reagent creation';

    SELECT container_type_id INTO tube_container_type_id
        FROM qiita.container_type
        WHERE description = 'tube';

    -- Extraction Kit
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_ek;

    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_ek, 10)
        RETURNING container_id INTO ext_kit_container_id;

    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (ext_kit_container_id, '157022406');

    SELECT composition_type_id INTO reagent_comp_type
        FROM qiita.composition_type
        WHERE description = 'reagent';

    SELECT reagent_composition_type_id INTO ext_kit_reagent_comp_type
        FROM qiita.reagent_composition_type
        WHERE description = 'extraction kit';

    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_ek, ext_kit_container_id, 10)
        RETURNING composition_id INTO ext_kit_composition_id;

    INSERT INTO qiita.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (ext_kit_composition_id, ext_kit_reagent_comp_type, '157022406')
        RETURNING reagent_composition_id INTO ext_kit_reagent_composition_id;

    -- Master mix
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_mm;

    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_mm, 10)
        RETURNING container_id INTO master_mix_container_id;

    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (master_mix_container_id, '443912');

    SELECT reagent_composition_type_id INTO master_mix_reagent_comp_type
        FROM qiita.reagent_composition_type
        WHERE description = 'master mix';

    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_mm, master_mix_container_id, 10)
        RETURNING composition_id INTO master_mix_composition_id;

    INSERT INTO qiita.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (master_mix_composition_id, master_mix_reagent_comp_type, '443912')
        RETURNING reagent_composition_id INTO master_mix_reagent_composition_id;

    -- Water
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_w;

    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_w, 10)
        RETURNING container_id INTO water_container_id;

    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (water_container_id, 'RNBF7110');

    SELECT reagent_composition_type_id INTO water_reagent_comp_type
        FROM qiita.reagent_composition_type
        WHERE description = 'water';

    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_w, water_container_id, 10)
        RETURNING composition_id INTO water_composition_id;

    INSERT INTO qiita.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (water_composition_id, water_reagent_comp_type, 'RNBF7110')
        RETURNING reagent_composition_id INTO water_reagent_composition_id;

    -----------------------------------
    ------ SAMPLE PLATING PROCESS ------
    -----------------------------------
    SELECT process_type_id INTO plating_process_type_id
        FROM qiita.process_type
        WHERE description = 'sample plating';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (plating_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO plating_process_id;

    -------------------------------------
    ------ GDNA EXTRACTION PROCESS ------
    -------------------------------------
    SELECT process_type_id INTO gdna_process_type_id
        FROM qiita.process_type
        WHERE description = 'gDNA extraction';

    SELECT equipment_id INTO ext_robot_id
        FROM qiita.equipment
        WHERE external_id = 'LUCY';

    SELECT equipment_id INTO ext_tool_id
        FROM qiita.equipment
        WHERE external_id = '108379Z';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO gdna_process_id;

    INSERT INTO qiita.gdna_extraction_process (process_id, extraction_robot_id, extraction_kit_id, extraction_tool_id)
        VALUES (gdna_process_id, ext_robot_id, ext_kit_reagent_composition_id, ext_tool_id);

    --------------------------------------
    ------ 16S Library prep process ------
    --------------------------------------
    SELECT process_type_id INTO lib_prep_16s_process_type_id
        FROM qiita.process_type
        WHERE description = '16S library prep';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (lib_prep_16s_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO lib_prep_16s_process_id;

    SELECT equipment_id INTO tm300_8_id
        FROM qiita.equipment
        WHERE external_id = '109375A';

    SELECT equipment_id INTO tm50_8_id
        FROM qiita.equipment
        WHERE external_id = '311411B';

    SELECT equipment_id INTO proc_robot_id
        FROM qiita.equipment
        WHERE external_id = 'JER-E';

    INSERT INTO qiita.library_prep_16s_process (process_id, master_mix_id, tm300_8_tool_id, tm50_8_tool_id, water_id, processing_robot_id)
        VALUES (lib_prep_16s_process_id, master_mix_reagent_composition_id, tm300_8_id, tm50_8_id, water_reagent_composition_id, proc_robot_id);

    ------------------------------------
    ------ QUANTIFICATION PROCESS ------
    ------------------------------------

    SELECT process_type_id INTO pg_quant_process_type_id
        FROM qiita.process_type
        WHERE description = 'quantification';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO pg_quant_process_id;

    INSERT INTO qiita.quantification_process (process_id)
        VALUES (pg_quant_process_id)
        RETURNING quantification_process_id INTO pg_quant_subprocess_id;

    -----------------------------------
    ------ PLATE POOLING PROCESS ------
    -----------------------------------
    SELECT process_type_id INTO p_pool_process_type_id
        FROM qiita.process_type
        WHERE description = 'pooling';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO p_pool_process_id;

    INSERT INTO qiita.pooling_process (process_id, quantification_process_id, robot_id)
        VALUES (p_pool_process_id, pg_quant_subprocess_id, proc_robot_id)
        RETURNING pooling_process_id INTO p_pool_subprocess_id;

    ----------------------------------------
    ------ SEQUENCING POOLING PROCESS ------
    ----------------------------------------
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO s_pool_process_id;

    INSERT INTO qiita.pooling_process (process_id, quantification_process_id, robot_id)
        VALUES (s_pool_process_id, pg_quant_subprocess_id, proc_robot_id)
        RETURNING pooling_process_id INTO s_pool_subprocess_id;

    ---------------------------------
    ------ CREATING THE PLATES ------
    ---------------------------------

    -- Up to this point we have created all the processes, but we have not created
    -- the different plates that are a result of these processes. The reason that
    -- We did it this way is so we can re-use the same for loop. Otherwise
    -- the SQL gets way more complicated since we will need to query for some
    -- values rather than just directly use them in the for loops that we already have

    SELECT plate_configuration_id INTO deepwell_96_plate_type_id
        FROM qiita.plate_configuration
        WHERE description = '96-well deep-well plate';

    -- Sample Plate
    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test plate 1', deepwell_96_plate_type_id)
        RETURNING plate_id INTO sample_plate_id;

    SELECT composition_type_id INTO sample_comp_type_id
        FROM qiita.composition_type
        WHERE description = 'sample';

    SELECT sample_composition_type_id INTO sample_type_id
        FROM qiita.sample_composition_type
        WHERE description = 'experimental sample';

    SELECT sample_composition_type_id INTO vibrio_type_id
        FROM qiita.sample_composition_type
        WHERE description = 'vibrio positive control';

    SELECT sample_composition_type_id INTO blank_type_id
        FROM qiita.sample_composition_type
        WHERE description = 'blank';

    -- gDNA plate
    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test gDNA plate 1', deepwell_96_plate_type_id)
        RETURNING plate_id INTO gdna_plate_id;

    SELECT composition_type_id INTO gdna_comp_type_id
        FROM qiita.composition_type
        WHERE description = 'gDNA';

    -- 16S library prep plate
    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test 16S plate 1', deepwell_96_plate_type_id)
        RETURNING plate_id INTO lib_prep_16s_plate_id;

    SELECT composition_type_id INTO lib_prep_16s_comp_type_id
        FROM qiita.composition_type
        WHERE description = '16S library prep';

    -- Pool plate
    SELECT composition_type_id INTO pool_comp_type_id
        FROM qiita.composition_type
        WHERE description = 'pool';
    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, p_pool_process_id, 96)
        RETURNING container_id INTO p_pool_container_id;
    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (p_pool_container_id, 'Test Pool from Plate 1');
    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (pool_comp_type_id, p_pool_process_id, p_pool_container_id, 96)
        RETURNING composition_id INTO p_pool_composition_id;
    INSERT INTO qiita.pool_composition (composition_id)
        VALUES (p_pool_composition_id)
        RETURNING pool_composition_id INTO p_pool_subcomposition_id;

    -- Pool sequencing run
    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, s_pool_process_id, 2)
        RETURNING container_id INTO s_pool_container_id;
    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (s_pool_container_id, 'Test sequencing pool 1');
    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (pool_comp_type_id, s_pool_process_id, s_pool_container_id, 2)
        RETURNING composition_id INTO s_pool_composition_id;
    INSERT INTO qiita.pool_composition (composition_id)
        VALUES (s_pool_composition_id)
        RETURNING pool_composition_id INTO s_pool_subcomposition_id;
    INSERT INTO qiita.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
        VALUES (s_pool_subcomposition_id, p_pool_composition_id, 2, 1);

    --------------------------------
    ------ SEQUENCING PROCESS ------
    --------------------------------
    SELECT process_type_id INTO sequencing_process_type_id
        FROM qiita.process_type
        WHERE description = 'sequencing';

    SELECT equipment_id INTO sequencer_id
        FROM qiita.equipment
        WHERE external_id = 'KL-MiSeq';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (sequencing_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO sequencing_process_id;

    INSERT INTO qiita.sequencing_process (process_id, pool_composition_id, sequencer_id, fwd_cycles, rev_cycles,
                                          principal_investigator, contact_0, contact_1, contact_2, assay, run_name)
        VALUES (sequencing_process_id, s_pool_subcomposition_id, sequencer_id, 151, 151,
                'test@foo.bar', 'shared@foo.bar', 'admin@foo.bar', 'demo@microbio.me', 'test assay', 'TestRun1');

    ------------------------------------
    ------------------------------------
    ------ ADD A METAGENOMICS RUN ------
    ------------------------------------
    ------------------------------------

    --------------------------------------------
    ------ gDNA PLATE COMPRESSION PROCESS ------
    --------------------------------------------
    SELECT process_type_id INTO gdna_comp_process_type_id
        FROM qiita.process_type
        WHERE description = 'compress gDNA plates';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_comp_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO gdna_comp_process_id;

    SELECT plate_configuration_id INTO microtiter_384_plate_type_id
        FROM qiita.plate_configuration
        WHERE description = '384-well microtiter plate';

    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test compressed gDNA plate 1', microtiter_384_plate_type_id)
        RETURNING plate_id INTO gdna_comp_plate_id;


    -- Start plating samples - to make this easier, we are going to plate the
    -- same 12 samples in the first 6 rows of the plate, in the 7th row we are
    -- going to plate vibrio controls and in the 8th row we are going to leave
    -- it for blanks
    FOR idx_row_well IN 1..8 LOOP
        FOR idx_col_well IN 1..12 LOOP
            IF idx_row_well <= 6 THEN
                -- Get information for plating a sample
                plating_sample_comp_type_id := sample_type_id;
                SELECT sample_id INTO plating_sample_id
                    FROM qiita.study_sample
                    WHERE study_id = 1
                    ORDER BY sample_id
                    OFFSET (idx_col_well - 1)
                    LIMIT 1;
            ELSIF idx_row_well = 7 THEN
                -- Get information for plating vibrio
                plating_sample_comp_type_id := vibrio_type_id;
                plating_sample_id := NULL;
            ELSE
                -- We are in the 8th row, get information for plating blanks
                plating_sample_comp_type_id := blank_type_id;
                plating_sample_id := NULL;
            END IF;

            -- SAMPLE WELLS
            INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, plating_process_id, 10)
                RETURNING container_id INTO plating_container_id;
            INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                VALUES (plating_container_id, sample_plate_id, idx_row_well, idx_col_well);
            INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (sample_comp_type_id, plating_process_id, plating_container_id, 10)
                RETURNING composition_id INTO plating_composition_id;
            INSERT INTO qiita.sample_composition (composition_id, sample_composition_type_id, sample_id)
                VALUES (plating_composition_id, plating_sample_comp_type_id, plating_sample_id)
                RETURNING sample_composition_id INTO plating_sample_composition_id;

            -- GDNA WELLS
            INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, gdna_process_id, 10)
                RETURNING container_id INTO gdna_container_id;
            INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                VALUES (gdna_container_id, gdna_plate_id, idx_row_well, idx_col_well);
            INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (gdna_comp_type_id, gdna_process_id, gdna_container_id, 10)
                RETURNING composition_id INTO gdna_comp_id;
            INSERT INTO qiita.gdna_composition (composition_id, sample_composition_id)
                VALUES (gdna_comp_id, plating_sample_composition_id)
                RETURNING gdna_composition_id INTO gdna_subcomposition_id;

            -- 16S LIBRARY PREP WELLS
            SELECT primer_composition_id INTO primer_comp_id
                FROM qiita.primer_composition
                    JOIN qiita.composition USING (composition_id)
                    JOIN qiita.well USING (container_id)
                    JOIN qiita.plate USING (plate_id)
                WHERE row_num = idx_row_well
                    AND col_num = idx_col_well
                    AND external_id = 'EMP Primer plate 1 10/23/2017';
            INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, lib_prep_16s_process_id, 10)
                RETURNING container_id INTO lib_prep_16s_container_id;
            INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                VALUES (lib_prep_16s_container_id, lib_prep_16s_plate_id, idx_row_well, idx_col_well);
            INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (lib_prep_16s_comp_type_id, lib_prep_16s_process_id, lib_prep_16s_container_id, 10)
                RETURNING composition_id INTO lib_prep_16s_composition_id;
            INSERT INTO qiita.library_prep_16s_composition (composition_id, gdna_composition_id, primer_composition_id)
                VALUES (lib_prep_16s_composition_id, gdna_subcomposition_id, primer_comp_id);

            -- Quantification
            INSERT INTO qiita.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration)
                VALUES (lib_prep_16s_composition_id, pg_quant_subprocess_id, 1.5);

            -- Pool plate
            INSERT INTO qiita.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
                VALUES (p_pool_subcomposition_id, lib_prep_16s_composition_id, 1, 1/96);

            -- METAGENOMICS:
            FOR row_pad IN 0..1 LOOP
                FOR col_pad IN 0..1 LOOP
                    -- Compress plate (use the same plate 4 times)
                    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                        VALUES (well_container_type_id, gdna_comp_process_id, 10)
                        RETURNING container_id INTO gdna_comp_container_id;
                    INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                        VALUES (gdna_comp_container_id, gdna_comp_plate_id, ((idx_row_well - 1) * 2 + row_pad) + 1, ((idx_col_well - 1) * 2 + col_pad) + 1);
                    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                        VALUES (gdna_comp_type_id, gdna_comp_process_id, gdna_comp_container_id, 10)
                        RETURNING composition_id INTO gdna_comp_comp_id;
                    INSERT INTO qiita.gdna_composition (composition_id, sample_composition_id)
                        VALUES (gdna_comp_comp_id, plating_sample_composition_id)
                        RETURNING gdna_composition_id INTO gdna_comp_subcomposition_id;
                END LOOP;
            END LOOP;

        END LOOP;
    END LOOP;
END $do$
