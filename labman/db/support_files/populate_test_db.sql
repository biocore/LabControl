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
    wpp_plate_id                        BIGINT;
    wpp_container_id                    BIGINT;
    wpp_composition_id                  BIGINT;
    primer_composition_type_id          BIGINT;
    microtiter_96_plate_type_id         BIGINT;
    psc_id                              BIGINT;
    shotgun_wpp_process_id              BIGINT;
    shotgun_wpp_primer_set_id           BIGINT;
    wpp_i5_plate_id                     BIGINT;
    wpp_i7_plate_id                     BIGINT;

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
    plating_sample_content              VARCHAR;
    vibrio_type_id                      BIGINT;
    blank_type_id                       BIGINT;
    plating_sample_composition_id       BIGINT;

    -- Variables for extraction
    ext_robot_id                        BIGINT;
    kf_robot_id                         BIGINT;
    ext_kit_container_id                BIGINT;
    ext_kit_reagent_comp_type           BIGINT;
    ext_kit_reagent_composition_id      BIGINT;
    ext_kit_composition_id              BIGINT;
    ext_tool_id                         BIGINT;
    gdna_process_type_id                BIGINT;
    gdna_process_id                     BIGINT;
    gdna_subprocess_id                  BIGINT;
    gdna_plate_id                       BIGINT;
    gdna_container_id                   BIGINT;
    gdna_comp_id                        BIGINT;
    gdna_comp_type_id                   BIGINT;
    gdna_subcomposition_id              BIGINT;

    -- Variables for 16S library prep
    lib_prep_16s_process_type_id        BIGINT;
    lib_prep_16s_process_id             BIGINT;
    lib_prep_16s_subprocess_id          BIGINT;
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

    -- Variables for manual quantification
    ppg_quant_process_id                BIGINT;
    ppg_quant_subprocess_id             BIGINT;

    -- Variables for sequencing pooling creation
    s_pool_process_id                   BIGINT;
    s_pool_subprocess_id                BIGINT;
    s_pool_container_id                 BIGINT;
    s_pool_composition_id               BIGINT;
    s_pool_subcomposition_id            BIGINT;

    -- Variables for sequencing
    amplicon_sequencing_process_id      BIGINT;
    sequencing_process_type_id          BIGINT;
    sequencer_id                        BIGINT;
    sequencing_subprocess_id            BIGINT;

    -- Metagenomics variables
    row_pad                             INTEGER;
    col_pad                             INTEGER;
    microtiter_384_plate_type_id        BIGINT;
    mg_row_id                           BIGINT;
    mg_col_id                           BIGINT;

    -- Variables for gDNA plate compression
    compressed_gdna_comp_type_id        BIGINT;
    echo_robot_id                       BIGINT;
    gdna_comp_process_type_id           BIGINT;
    gdna_comp_process_id                BIGINT;
    gdna_comp_container_id              BIGINT;
    gdna_comp_comp_id                   BIGINT;
    gdna_comp_subcomposition_id         BIGINT;
    gdna_comp_plate_id                  BIGINT;

    -- Variables for gDNA quantification
    mg_gdna_quant_process_id            BIGINT;
    mg_gdna_quant_subprocess_id         BIGINT;
    gdna_sample_conc                    REAL;

    -- Variables for gDNA normalization
    gdna_norm_process_type_id           BIGINT;
    gdna_norm_process_id                BIGINT;
    gdna_norm_subprocess_id             BIGINT;
    gdna_norm_plate_id                  BIGINT;
    gdna_norm_container_id              BIGINT;
    gdna_norm_comp_type_id              BIGINT;
    gdna_norm_comp_id                   BIGINT;
    norm_dna_vol                        REAL;
    norm_water_vol                      REAL;
    gdna_norm_subcomp_id                BIGINT;

    -- Variables for shotgun library prep
    rc_process_id_khp                   BIGINT;
    khp_container_id                    BIGINT;
    khp_reagent_comp_type               BIGINT;
    khp_composition_id                  BIGINT;
    khp_reagent_composition_id          BIGINT;
    rc_process_id_stubs                 BIGINT;
    stubs_container_id                  BIGINT;
    stubs_reagent_comp_type             BIGINT;
    stubs_composition_id                BIGINT;
    stubs_reagent_composition_id        BIGINT;
    shotgun_lib_process_type_id         BIGINT;
    shotgun_lib_process_id              BIGINT;
    shotgun_lib_plate_id                BIGINT;
    shotgun_lib_comp_type_id            BIGINT;
    shotgun_lib_container_id            BIGINT;
    shotgun_lib_comp_id                 BIGINT;
    combo_idx                           BIGINT;
    i5_primer_id                        BIGINT;
    i7_primer_id                        BIGINT;

    -- Variables for shotgun lib concentration
    sh_lib_quant_process_id             BIGINT;
    sh_lib_quant_subprocess_id          BIGINT;
    sh_lib_raw_sample_conc              REAL;
    sh_lib_comp_sample_conc             REAL;

    -- Variables for shotgun pooling
    sh_pool_process_id                  BIGINT;
    sh_pool_subprocess_id               BIGINT;
    sh_pool_subcomposition_id           BIGINT;
    sh_pool_container_id                BIGINT;
    sh_pool_composition_id              BIGINT;

    -- Variables for shotgun sequencing
    shotgun_sequencing_process_id       BIGINT;
    shotgun_sequencing_subprocess_id    BIGINT;
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
        WHERE external_id = 'EMP 16S V4 primer set';
    INSERT INTO qiita.primer_working_plate_creation_process (process_id, primer_set_id, master_set_order_number)
        VALUES (wpp_process_id, wpp_emp_primer_set_id, 'EMP PRIMERS MSON 1');

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

    -- Get the id of the 384-well microtiter plate configuration
    SELECT plate_configuration_id INTO microtiter_384_plate_type_id
        FROM qiita.plate_configuration
        WHERE description = '384-well microtiter plate';

    -- We need to create 8 plates, since the structure is the same for
    -- all use a for loop to avoid rewriting stuff
    FOR plate_idx IN 1..8 LOOP
        -- The working primer plates are identifier by the template plate number and the
        -- date they're created. Ther are 96-well microtiter plates
        INSERT INTO qiita.plate (external_id, plate_configuration_id, discarded)
            VALUES ('EMP 16S V4 primer plate ' || plate_idx::varchar || ' 10/23/2017', microtiter_96_plate_type_id, false)
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
                    WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_id = 'EMP 16S V4 primer plate ' || plate_idx;
                INSERT INTO qiita.primer_composition (composition_id, primer_set_composition_id)
                    VALUES (wpp_composition_id, psc_id);
            END LOOP;  -- Column loop
        END LOOP; -- Row loop
    END LOOP; -- Plate loop

    -- Populate working primer plate info
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (wpp_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO shotgun_wpp_process_id;
    -- Populate the primer_working_plate_creation_process
    SELECT primer_set_id INTO shotgun_wpp_primer_set_id
        FROM qiita.primer_set
        WHERE external_id = 'iTru shotgun primer set';
    INSERT INTO qiita.primer_working_plate_creation_process (process_id, primer_set_id, master_set_order_number)
        VALUES (shotgun_wpp_process_id, shotgun_wpp_primer_set_id, 'SHOTGUN PRIMERS MSON 1');
    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('iTru 5 Primer Plate 10/23/2017', microtiter_384_plate_type_id)
        RETURNING plate_id INTO wpp_i5_plate_id;
    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('iTru 7 Primer Plate 10/23/2017', microtiter_384_plate_type_id)
        RETURNING plate_id INTO wpp_i7_plate_id;

    FOR idx_row_well IN 1..16 LOOP
        FOR idx_col_well IN 1..24 LOOP
            -- i5 primer
            -- Creating the well information
            INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, shotgun_wpp_process_id, 10)
                RETURNING container_id INTO wpp_container_id;
            INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                VALUES (wpp_container_id, wpp_i5_plate_id, idx_row_well, idx_col_well);
            -- Creating the composition information
            INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (primer_composition_type_id, shotgun_wpp_process_id, wpp_container_id, 10)
                RETURNING composition_id INTO wpp_composition_id;
            INSERT INTO qiita.primer_composition (composition_id, primer_set_composition_id)
                VALUES (wpp_composition_id, (SELECT primer_set_composition_id
                                             FROM qiita.primer_set_composition psc
                                                JOIN qiita.composition c USING (composition_id)
                                                JOIN qiita.well w USING (container_id)
                                                JOIN qiita.plate p USING (plate_id)
                                             WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_id = 'iTru 5 primer'));

            -- i5 primer
            -- Creating the well information
            INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, shotgun_wpp_process_id, 10)
                RETURNING container_id INTO wpp_container_id;
            INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                VALUES (wpp_container_id, wpp_i7_plate_id, idx_row_well, idx_col_well);
            -- Creating the composition information
            INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (primer_composition_type_id, shotgun_wpp_process_id, wpp_container_id, 10)
                RETURNING composition_id INTO wpp_composition_id;
            INSERT INTO qiita.primer_composition (composition_id, primer_set_composition_id)
                VALUES (wpp_composition_id, (SELECT primer_set_composition_id
                                             FROM qiita.primer_set_composition psc
                                                JOIN qiita.composition c USING (composition_id)
                                                JOIN qiita.well w USING (container_id)
                                                JOIN qiita.plate p USING (plate_id)
                                             WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_id = 'iTru 7 primer'));
        END LOOP; -- Column loop
    END LOOP; -- Row loop


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

    -- Kappa Hyper Plus kit
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_khp;

    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_khp, 10)
        RETURNING container_id INTO khp_container_id;

    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (khp_container_id, 'KHP1');

    SELECT reagent_composition_type_id INTO khp_reagent_comp_type
        FROM qiita.reagent_composition_type
        WHERE description = 'kappa hyper plus kit';

    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_khp, khp_container_id, 10)
        RETURNING composition_id INTO khp_composition_id;

    INSERT INTO qiita.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (khp_composition_id, khp_reagent_comp_type, 'KHP1')
        RETURNING reagent_composition_id INTO khp_reagent_composition_id;

    -- Stubs
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_stubs;

    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_stubs, 10)
        RETURNING container_id INTO stubs_container_id;

    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (stubs_container_id, 'STUBS1');

    SELECT reagent_composition_type_id INTO stubs_reagent_comp_type
        FROM qiita.reagent_composition_type
        WHERE description = 'shotgun stubs';

    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_stubs, stubs_container_id, 10)
        RETURNING composition_id INTO stubs_composition_id;

    INSERT INTO qiita.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (stubs_composition_id, stubs_reagent_comp_type, 'STUBS1')
        RETURNING reagent_composition_id INTO stubs_reagent_composition_id;

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

    SELECT equipment_id INTO kf_robot_id
        FROM qiita.equipment
        WHERE external_id = 'KF1';

    SELECT equipment_id INTO ext_tool_id
        FROM qiita.equipment
        WHERE external_id = '108379Z';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO gdna_process_id;

    INSERT INTO qiita.gdna_extraction_process (process_id, epmotion_robot_id, epmotion_tool_id, kingfisher_robot_id, extraction_kit_id)
        VALUES (gdna_process_id, ext_robot_id, ext_tool_id, kf_robot_id, ext_kit_reagent_composition_id)
        RETURNING gdna_extraction_process_id INTO gdna_subprocess_id;

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

    INSERT INTO qiita.library_prep_16s_process (process_id, epmotion_robot_id, epmotion_tm300_8_tool_id, epmotion_tm50_8_tool_id, master_mix_id, water_lot_id)
        VALUES (lib_prep_16s_process_id, proc_robot_id, tm300_8_id, tm50_8_id, master_mix_reagent_composition_id, water_reagent_composition_id)
        RETURNING library_prep_16s_process_id INTO lib_prep_16s_subprocess_id;

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

    ------------------------------------
    ------ QUANTIFICATION PROCESS ------
    ------------------------------------
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO ppg_quant_process_id;

    INSERT INTO qiita.quantification_process (process_id)
        VALUES (ppg_quant_process_id)
        RETURNING quantification_process_id INTO ppg_quant_subprocess_id;
    -----------------------------------
    ------ PLATE POOLING PROCESS ------
    -----------------------------------
    SELECT process_type_id INTO p_pool_process_type_id
        FROM qiita.process_type
        WHERE description = 'pooling';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO p_pool_process_id;

    INSERT INTO qiita.pooling_process (process_id, quantification_process_id, robot_id, destination, pooling_function_data)
        VALUES (p_pool_process_id, pg_quant_subprocess_id, proc_robot_id, 1, '{"function": "amplicon", "parameters": {"dna-amount-": 240, "min-val-": 1, "max-val-": 15, "blank-val-": 2}}'::json)
        RETURNING pooling_process_id INTO p_pool_subprocess_id;

    ----------------------------------------
    ------ SEQUENCING POOLING PROCESS ------
    ----------------------------------------
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO s_pool_process_id;

    INSERT INTO qiita.pooling_process (process_id, quantification_process_id, robot_id, pooling_function_data)
        VALUES (s_pool_process_id, pg_quant_subprocess_id, proc_robot_id, '{"function": "amplicon_pool", "parameters": {}}'::json)
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
        WHERE description = 'vibrio.positive.control';

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

    -- Quantify plate pools
    INSERT INTO qiita.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration)
        VALUES (p_pool_composition_id, ppg_quant_subprocess_id, 1.5);

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
        RETURNING process_id INTO amplicon_sequencing_process_id;

    INSERT INTO qiita.sequencing_process (process_id, run_name, experiment, sequencer_id,
                                          fwd_cycles, rev_cycles, assay, principal_investigator)
        VALUES (amplicon_sequencing_process_id, 'Test Run.1', 'TestExperiment1',
                sequencer_id, 151, 151, 'Amplicon', 'test@foo.bar')
        RETURNING sequencing_process_id INTO sequencing_subprocess_id;

        INSERT INTO qiita.sequencing_process_lanes (sequencing_process_id, pool_composition_id, lane_number)
            VALUES (sequencing_subprocess_id, s_pool_subcomposition_id, 1);

    INSERT INTO qiita.sequencing_process_contacts (sequencing_process_id, contact_id)
        VALUES (sequencing_subprocess_id, 'shared@foo.bar'),
               (sequencing_subprocess_id, 'admin@foo.bar'),
               (sequencing_subprocess_id, 'demo@microbio.me');

    ------------------------------------
    ------------------------------------
    ------ ADD A METAGENOMICS RUN ------
    ------------------------------------
    ------------------------------------

    --------------------------------------------
    ------ gDNA PLATE COMPRESSION PROCESS ------
    --------------------------------------------
    SELECT equipment_id INTO echo_robot_id
        FROM qiita.equipment
        WHERE external_id = 'Echo550';

    SELECT process_type_id INTO gdna_comp_process_type_id
        FROM qiita.process_type
        WHERE description = 'compress gDNA plates';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_comp_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO gdna_comp_process_id;

    INSERT INTO qiita.compression_process (process_id, robot_id)
        VALUES (gdna_comp_process_id, echo_robot_id);

    SELECT composition_type_id INTO compressed_gdna_comp_type_id
        FROM qiita.composition_type
        WHERE description = 'compressed gDNA';

    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test compressed gDNA plate 1', microtiter_384_plate_type_id)
        RETURNING plate_id INTO gdna_comp_plate_id;

    -----------------------------------------
    ------ gDNA QUANTIFICATION PROCESS ------
    -----------------------------------------
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO mg_gdna_quant_process_id;

    INSERT INTO qiita.quantification_process (process_id)
        VALUES (mg_gdna_quant_process_id)
        RETURNING quantification_process_id INTO mg_gdna_quant_subprocess_id;

    ----------------------------------------
    ------ gDNA NORMALIZATION PROCESS ------
    ----------------------------------------
    SELECT process_type_id INTO gdna_norm_process_type_id
        FROM qiita.process_type
        WHERE description = 'gDNA normalization';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_norm_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO gdna_norm_process_id;

    INSERT INTO qiita.normalization_process (process_id, quantitation_process_id, water_lot_id, normalization_function_data)
        VALUES (gdna_norm_process_id, mg_gdna_quant_subprocess_id, water_reagent_composition_id, '{"function": "default", "parameters": {"total_volume": 3500, "reformat": false, "target_dna": 5, "resolution": 2.5, "min_vol": 2.5, "max_volume": 3500}}'::json)
        RETURNING normalization_process_id INTO gdna_norm_subprocess_id;

    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test normalized gDNA plate 1', microtiter_384_plate_type_id)
        RETURNING plate_id INTO gdna_norm_plate_id;

    SELECT composition_type_id INTO gdna_norm_comp_type_id
        FROM qiita.composition_type
        WHERE description = 'normalized gDNA';

    -------------------------------------
    ------ SHOTGUN LIBRARY PROCESS ------
    -------------------------------------
    SELECT process_type_id INTO shotgun_lib_process_type_id
        FROM qiita.process_type
        WHERE description = 'shotgun library prep';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (shotgun_lib_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO shotgun_lib_process_id;

    INSERT INTO qiita.library_prep_shotgun_process (process_id, kappa_hyper_plus_kit_id, stub_lot_id, normalization_process_id)
        VALUES (shotgun_lib_process_id, khp_reagent_composition_id, stubs_reagent_composition_id, gdna_norm_subprocess_id);

    INSERT INTO qiita.plate (external_id, plate_configuration_id)
        VALUES ('Test shotgun library plate 1', microtiter_384_plate_type_id)
        RETURNING plate_id INTO shotgun_lib_plate_id;

    SELECT composition_type_id INTO shotgun_lib_comp_type_id
        FROM qiita.composition_type
        WHERE description = 'shotgun library prep';

    combo_idx := 0;

    --------------------------------------------
    ------ LIBRARY QUANTIFICATION PROCESS ------
    --------------------------------------------
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO sh_lib_quant_process_id;

    INSERT INTO qiita.quantification_process (process_id)
        VALUES (sh_lib_quant_process_id)
        RETURNING quantification_process_id INTO sh_lib_quant_subprocess_id;

    -----------------------------
    ------ POOLING PROCESS ------
    -----------------------------
    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO sh_pool_process_id;

    INSERT INTO qiita.pooling_process (process_id, quantification_process_id, robot_id, pooling_function_data)
        VALUES (sh_pool_process_id, sh_lib_quant_subprocess_id, proc_robot_id, '{"function": "equal", "parameters": {"volume-": 200, "lib-size-": 500}}')
        RETURNING pooling_process_id INTO sh_pool_subprocess_id;

    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, sh_pool_process_id, 384)
        RETURNING container_id INTO sh_pool_container_id;
    INSERT INTO qiita.tube (container_id, external_id)
        VALUES (sh_pool_container_id, 'Test pool from Shotgun plate 1');
    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (pool_comp_type_id, sh_pool_process_id, sh_pool_container_id, 384)
        RETURNING composition_id INTO sh_pool_composition_id;
    INSERT INTO qiita.pool_composition (composition_id)
        VALUES (sh_pool_composition_id)
        RETURNING pool_composition_id INTO sh_pool_subcomposition_id;

    --------------------------------
    ------ SEQUENCING PROCESS ------
    --------------------------------
    SELECT equipment_id INTO sequencer_id
        FROM qiita.equipment
        WHERE external_id = 'IGM-HiSeq4000';

    INSERT INTO qiita.process (process_type_id, run_date, run_personnel_id)
        VALUES (sequencing_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO shotgun_sequencing_process_id;

    INSERT INTO qiita.sequencing_process (process_id, run_name, experiment, sequencer_id,
                                          fwd_cycles, rev_cycles, assay, principal_investigator)
        VALUES (shotgun_sequencing_process_id, 'TestShotgunRun1', 'TestExperimentShotgun1',
                sequencer_id, 151, 151, 'Metagenomics','test@foo.bar')
        RETURNING sequencing_process_id INTO shotgun_sequencing_subprocess_id;

    INSERT INTO qiita.sequencing_process_lanes (sequencing_process_id, pool_composition_id, lane_number)
        VALUES (shotgun_sequencing_subprocess_id, sh_pool_subcomposition_id, 1);

    INSERT INTO qiita.sequencing_process_contacts (sequencing_process_id, contact_id)
        VALUES (shotgun_sequencing_subprocess_id, 'shared@foo.bar'),
               (shotgun_sequencing_subprocess_id, 'demo@microbio.me');


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
                plating_sample_content := plating_sample_id || '.' || sample_plate_id::text || '.' || chr(ascii('@') + idx_row_well) || idx_col_well::text;
                gdna_sample_conc := 12.068;
                norm_dna_vol := 415;
                norm_water_vol := 3085;
                sh_lib_raw_sample_conc := 12.068;
                sh_lib_comp_sample_conc := 36.569;
            ELSIF idx_row_well = 7 THEN
                -- Get information for plating vibrio
                plating_sample_comp_type_id := vibrio_type_id;
                plating_sample_id := NULL;
                plating_sample_content := 'vibrio.positive.control.' || sample_plate_id::text || '.G' || idx_col_well::text;
                gdna_sample_conc := 6.089;
                norm_dna_vol := 820;
                norm_water_vol := 2680;
                sh_lib_raw_sample_conc := 8.904;
                sh_lib_comp_sample_conc := 26.981;
            ELSE
                -- We are in the 8th row, get information for plating blanks
                plating_sample_comp_type_id := blank_type_id;
                plating_sample_id := NULL;
                plating_sample_content := 'blank.' || sample_plate_id::text || '.H' || idx_col_well::text;
                gdna_sample_conc := 0.342;
                norm_dna_vol := 3500;
                norm_water_vol := 0;
                sh_lib_raw_sample_conc := 0.342;
                sh_lib_comp_sample_conc := 1.036;
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
            INSERT INTO qiita.sample_composition (composition_id, sample_composition_type_id, sample_id, content)
                VALUES (plating_composition_id, plating_sample_comp_type_id, plating_sample_id, plating_sample_content)
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
                    AND external_id = 'EMP 16S V4 primer plate 1 10/23/2017';
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
            INSERT INTO qiita.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration, computed_concentration)
                VALUES (lib_prep_16s_composition_id, pg_quant_subprocess_id, 1.5, 1.5);

            -- Pool plate
            INSERT INTO qiita.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
                VALUES (p_pool_subcomposition_id, lib_prep_16s_composition_id, 1, 1/96);

            -- METAGENOMICS:
            FOR row_pad IN 0..1 LOOP
                FOR col_pad IN 0..1 LOOP
                    mg_row_id := ((idx_row_well - 1) * 2 + row_pad) + 1;
                    mg_col_id := ((idx_col_well - 1) * 2 + col_pad) + 1;
                    -- Compress plate (use the same plate 4 times)
                    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                        VALUES (well_container_type_id, gdna_comp_process_id, 10)
                        RETURNING container_id INTO gdna_comp_container_id;
                    INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                        VALUES (gdna_comp_container_id, gdna_comp_plate_id, mg_row_id, mg_col_id);
                    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                        VALUES (compressed_gdna_comp_type_id, gdna_comp_process_id, gdna_comp_container_id, 10)
                        RETURNING composition_id INTO gdna_comp_comp_id;
                    INSERT INTO qiita.compressed_gdna_composition (composition_id, gdna_composition_id)
                        VALUES (gdna_comp_comp_id, gdna_subcomposition_id)
                        RETURNING compressed_gdna_composition_id INTO gdna_comp_subcomposition_id;

                    -- Quantify plate
                    INSERT INTO qiita.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration)
                        VALUES (gdna_comp_comp_id, mg_gdna_quant_subprocess_id, gdna_sample_conc);

                    -- Normalize plate
                    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                        VALUES (well_container_type_id, gdna_norm_process_id, 3500)
                        RETURNING container_id INTO gdna_norm_container_id;
                    INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                        VALUES (gdna_norm_container_id, gdna_norm_plate_id, mg_row_id, mg_col_id);
                    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                        VALUES (gdna_norm_comp_type_id, gdna_norm_process_id, gdna_norm_container_id, 3500)
                        RETURNING composition_id INTO gdna_norm_comp_id;
                    INSERT INTO qiita.normalized_gdna_composition (composition_id, compressed_gdna_composition_id, dna_volume, water_volume)
                        VALUES (gdna_norm_comp_id, gdna_comp_subcomposition_id, norm_dna_vol, norm_water_vol)
                        RETURNING normalized_gdna_composition_id INTO gdna_norm_subcomp_id;

                    -- Library plate
                    SELECT primer_composition_id INTO i5_primer_id
                        FROM qiita.shotgun_combo_primer_set c
                            JOIN qiita.primer_composition pci5 ON c.i5_primer_set_composition_id = pci5.primer_set_composition_id
                        WHERE shotgun_combo_primer_set_id = (combo_idx + 1);
                    SELECT primer_composition_id INTO i7_primer_id
                        FROM qiita.shotgun_combo_primer_set c
                            JOIN qiita.primer_composition pci7 ON c.i7_primer_set_composition_id = pci7.primer_set_composition_id
                        WHERE shotgun_combo_primer_set_id = (combo_idx + 1);
                    combo_idx := combo_idx + 1;
                    INSERT INTO qiita.container (container_type_id, latest_upstream_process_id, remaining_volume)
                        VALUES (well_container_type_id, shotgun_lib_process_id, 4000)
                        RETURNING container_id INTO shotgun_lib_container_id;
                    INSERT INTO qiita.well (container_id, plate_id, row_num, col_num)
                        VALUES (shotgun_lib_container_id, shotgun_lib_plate_id, mg_row_id, mg_col_id);
                    INSERT INTO qiita.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                        VALUES (shotgun_lib_comp_type_id, shotgun_lib_process_id, shotgun_lib_container_id, 4000)
                        RETURNING composition_id INTO shotgun_lib_comp_id;
                    INSERT INTO qiita.library_prep_shotgun_composition (composition_id, normalized_gdna_composition_id, i5_primer_composition_id, i7_primer_composition_id)
                        VALUES (shotgun_lib_comp_id, gdna_norm_subcomp_id, i5_primer_id, i7_primer_id);

                    -- Quantify library plate
                    INSERT INTO qiita.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration, computed_concentration)
                        VALUES (shotgun_lib_comp_id, sh_lib_quant_subprocess_id, sh_lib_raw_sample_conc, sh_lib_comp_sample_conc);

                    -- Pooling
                    INSERT INTO qiita.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
                        VALUES (sh_pool_subcomposition_id, shotgun_lib_comp_id, 1, 1/384);
                END LOOP; -- Shotgun col pad
            END LOOP; -- Shotgun row pad

        END LOOP; -- index col well
    END LOOP; -- index row well

    -- Update the combo index value
    UPDATE qiita.shotgun_primer_set SET current_combo_index = combo_idx;

END $do$
