-- Controlling for the Ids here is more complex. Hence we are going
-- to populate the DB in a function so we can easily keep track of the
-- ids

INSERT INTO labman.labmanager_access (email)
    VALUES ('test@foo.bar'), ('admin@foo.bar'), ('demo@microbio.me'),
           ('LabmanSystem@labman.com');

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

    -- Variables for externally extracted samples
    rc_process_id_none                  BIGINT;
    none_container_id                   BIGINT;
    none_composition_id                 BIGINT;
    none_reagent_composition_id         BIGINT;
    none_reagent_comp_type              BIGINT;

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
    curr_plating_process_id             BIGINT;
    plating_process_type_id             BIGINT;
    deepwell_96_plate_type_id           BIGINT;
    sample_plate_id                     BIGINT;
    curr_sample_plate_id                BIGINT;
    plating_container_id                BIGINT;
    sample_comp_type_id                 BIGINT;
    sample_type_id                      BIGINT;
    plating_composition_id              BIGINT;
    plating_sample_comp_type_id         BIGINT;
    plating_sample_id                   VARCHAR;
    plating_sample_content              VARCHAR;
    vibrio_type_id                      BIGINT;
    blank_type_id                       BIGINT;
    empty_type_id                       BIGINT;
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
    curr_gdna_process_id                BIGINT;
    gdna_subprocess_id                  BIGINT;
    gdna_plate_id                       BIGINT;
    curr_gdna_plate_id                  BIGINT;
    gdna_container_id                   BIGINT;
    gdna_comp_id                        BIGINT;
    gdna_comp_type_id                   BIGINT;
    gdna_subcomposition_id              BIGINT;

    -- Variables for 16S library prep
    lib_prep_16s_process_type_id        BIGINT;
    lib_prep_16s_process_id             BIGINT;
    curr_lib_prep_16s_process_id        BIGINT;
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
    curr_lib_prep_16s_plate_id          BIGINT;
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
    curr_p_pool_process_id              BIGINT;
    p_pool_subprocess_id                BIGINT;
    p_pool_container_id                 BIGINT;
    curr_p_pool_container_id            BIGINT;
    pool_comp_type_id                   BIGINT;
    p_pool_composition_id               BIGINT;
    curr_p_pool_composition_id          BIGINT;
    p_pool_subcomposition_id            BIGINT;
    curr_p_pool_subcomposition_id       BIGINT;

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
    sh_lib_quant_process_id2            BIGINT;
    sh_lib_quant_subprocess_id2         BIGINT;
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

    -- Variables for extra plate/pool creation
    curr_sample_plate_name              VARCHAR;
    curr_gdna_plate_name                VARCHAR;
    curr_lib_prep_plate_name            VARCHAR;
    curr_pool_name                      VARCHAR;
BEGIN
    --------------------------------------------
    -------- CREATE PRIMER WORKING PLATES ------
    --------------------------------------------
    SELECT process_type_id INTO wpp_process_type_id
        FROM labman.process_type
        WHERE description = 'primer working plate creation';
    -- Populate working primer plate info
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (wpp_process_type_id, '10/23/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO wpp_process_id;
    -- Populate the primer_working_plate_creation_process
    SELECT primer_set_id INTO wpp_emp_primer_set_id
        FROM labman.primer_set
        WHERE external_id = 'EMP 16S V4 primer set';
    INSERT INTO labman.primer_working_plate_creation_process (process_id, primer_set_id, master_set_order_number)
        VALUES (wpp_process_id, wpp_emp_primer_set_id, 'EMP PRIMERS MSON 1');

    -- Get the id of the container type "well"
    SELECT container_type_id INTO well_container_type_id
        FROM labman.container_type
        WHERE description = 'well';

    -- Get the id of the primer composition type
    SELECT composition_type_id INTO primer_composition_type_id
        FROM labman.composition_type
        WHERE description = 'primer';

    -- Get the id of the 96-well microtiter plate configuration
    SELECT plate_configuration_id INTO microtiter_96_plate_type_id
        FROM labman.plate_configuration
        WHERE description = '96-well microtiter plate';

    -- Get the id of the 384-well microtiter plate configuration
    SELECT plate_configuration_id INTO microtiter_384_plate_type_id
        FROM labman.plate_configuration
        WHERE description = '384-well microtiter plate';

    -- We need to create 8 plates, since the structure is the same for
    -- all use a for loop to avoid rewriting stuff
    FOR plate_idx IN 1..8 LOOP
        -- The working primer plates are identifier by the template plate number and the
        -- date they're created. Ther are 96-well microtiter plates
        INSERT INTO labman.plate (external_id, plate_configuration_id, discarded)
            VALUES ('EMP 16S V4 primer plate ' || plate_idx::varchar || ' 10/23/2017', microtiter_96_plate_type_id, false)
            RETURNING plate_id INTO wpp_plate_id;

        -- There are 96 well plates - 2 -> well
        FOR idx_row_well IN 1..8 LOOP
            FOR idx_col_well IN 1..12 LOOP
                -- Creating the well information
                INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                    VALUES (well_container_type_id, wpp_process_id, 10)
                    RETURNING container_id INTO wpp_container_id;
                INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                    VALUES (wpp_container_id, wpp_plate_id, idx_row_well, idx_col_well);

                -- Creating the composition information
                INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                    VALUES (primer_composition_type_id, wpp_process_id, wpp_container_id, 10)
                    RETURNING composition_id INTO wpp_composition_id;
                SELECT primer_set_composition_id INTO psc_id
                    FROM labman.primer_set_composition psc
                        JOIN labman.composition c USING (composition_id)
                        JOIN labman.well w USING (container_id)
                        JOIN labman.plate p USING (plate_id)
                    WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_id = 'EMP 16S V4 primer plate ' || plate_idx;
                INSERT INTO labman.primer_composition (composition_id, primer_set_composition_id)
                    VALUES (wpp_composition_id, psc_id);
            END LOOP;  -- Column loop
        END LOOP; -- Row loop
    END LOOP; -- Plate loop

    -- Populate working primer plate info
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (wpp_process_type_id, '10/23/2017 19:20:25-07', 'test@foo.bar')
        RETURNING process_id INTO shotgun_wpp_process_id;
    -- Populate the primer_working_plate_creation_process
    SELECT primer_set_id INTO shotgun_wpp_primer_set_id
        FROM labman.primer_set
        WHERE external_id = 'iTru shotgun primer set';
    INSERT INTO labman.primer_working_plate_creation_process (process_id, primer_set_id, master_set_order_number)
        VALUES (shotgun_wpp_process_id, shotgun_wpp_primer_set_id, 'SHOTGUN PRIMERS MSON 1');
    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('iTru 5 Primer Plate 10/23/2017', microtiter_384_plate_type_id)
        RETURNING plate_id INTO wpp_i5_plate_id;
    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('iTru 7 Primer Plate 10/23/2017', microtiter_384_plate_type_id)
        RETURNING plate_id INTO wpp_i7_plate_id;

    FOR idx_row_well IN 1..16 LOOP
        FOR idx_col_well IN 1..24 LOOP
            -- i5 primer
            -- Creating the well information
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, shotgun_wpp_process_id, 10)
                RETURNING container_id INTO wpp_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (wpp_container_id, wpp_i5_plate_id, idx_row_well, idx_col_well);
            -- Creating the composition information
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (primer_composition_type_id, shotgun_wpp_process_id, wpp_container_id, 10)
                RETURNING composition_id INTO wpp_composition_id;
            INSERT INTO labman.primer_composition (composition_id, primer_set_composition_id)
                VALUES (wpp_composition_id, (SELECT primer_set_composition_id
                                             FROM labman.primer_set_composition psc
                                                JOIN labman.composition c USING (composition_id)
                                                JOIN labman.well w USING (container_id)
                                                JOIN labman.plate p USING (plate_id)
                                             WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_id = 'iTru 5 primer'));

            -- i5 primer
            -- Creating the well information
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, shotgun_wpp_process_id, 10)
                RETURNING container_id INTO wpp_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (wpp_container_id, wpp_i7_plate_id, idx_row_well, idx_col_well);
            -- Creating the composition information
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (primer_composition_type_id, shotgun_wpp_process_id, wpp_container_id, 10)
                RETURNING composition_id INTO wpp_composition_id;
            INSERT INTO labman.primer_composition (composition_id, primer_set_composition_id)
                VALUES (wpp_composition_id, (SELECT primer_set_composition_id
                                             FROM labman.primer_set_composition psc
                                                JOIN labman.composition c USING (composition_id)
                                                JOIN labman.well w USING (container_id)
                                                JOIN labman.plate p USING (plate_id)
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
        FROM labman.process_type
        WHERE description = 'reagent creation';

    SELECT container_type_id INTO tube_container_type_id
        FROM labman.container_type
        WHERE description = 'tube';

    -- Extraction Kit
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017 09:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_ek;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_ek, 10)
        RETURNING container_id INTO ext_kit_container_id;

    INSERT INTO labman.tube (container_id, external_id)
        VALUES (ext_kit_container_id, '157022406');

    SELECT composition_type_id INTO reagent_comp_type
        FROM labman.composition_type
        WHERE description = 'reagent';

    SELECT reagent_composition_type_id INTO ext_kit_reagent_comp_type
        FROM labman.reagent_composition_type
        WHERE description = 'extraction kit';

    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_ek, ext_kit_container_id, 10)
        RETURNING composition_id INTO ext_kit_composition_id;

    INSERT INTO labman.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (ext_kit_composition_id, ext_kit_reagent_comp_type, '157022406')
        RETURNING reagent_composition_id INTO ext_kit_reagent_composition_id;

    -- Master mix
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017 19:10:25-02', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_mm;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_mm, 10)
        RETURNING container_id INTO master_mix_container_id;

    INSERT INTO labman.tube (container_id, external_id)
        VALUES (master_mix_container_id, '443912');

    SELECT reagent_composition_type_id INTO master_mix_reagent_comp_type
        FROM labman.reagent_composition_type
        WHERE description = 'master mix';

    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_mm, master_mix_container_id, 10)
        RETURNING composition_id INTO master_mix_composition_id;

    INSERT INTO labman.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (master_mix_composition_id, master_mix_reagent_comp_type, '443912')
        RETURNING reagent_composition_id INTO master_mix_reagent_composition_id;

    -- Water
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_w;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_w, 10)
        RETURNING container_id INTO water_container_id;

    INSERT INTO labman.tube (container_id, external_id)
        VALUES (water_container_id, 'RNBF7110');

    SELECT reagent_composition_type_id INTO water_reagent_comp_type
        FROM labman.reagent_composition_type
        WHERE description = 'water';

    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_w, water_container_id, 10)
        RETURNING composition_id INTO water_composition_id;

    INSERT INTO labman.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (water_composition_id, water_reagent_comp_type, 'RNBF7110')
        RETURNING reagent_composition_id INTO water_reagent_composition_id;

    -- Kappa Hyper Plus kit
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017 09:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_khp;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_khp, 10)
        RETURNING container_id INTO khp_container_id;

    INSERT INTO labman.tube (container_id, external_id)
        VALUES (khp_container_id, 'KHP1');

    SELECT reagent_composition_type_id INTO khp_reagent_comp_type
        FROM labman.reagent_composition_type
        WHERE description = 'kappa hyper plus kit';

    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_khp, khp_container_id, 10)
        RETURNING composition_id INTO khp_composition_id;

    INSERT INTO labman.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (khp_composition_id, khp_reagent_comp_type, 'KHP1')
        RETURNING reagent_composition_id INTO khp_reagent_composition_id;

    -- Stubs
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '10/23/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_stubs;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_stubs, 10)
        RETURNING container_id INTO stubs_container_id;

    INSERT INTO labman.tube (container_id, external_id)
        VALUES (stubs_container_id, 'STUBS1');

    SELECT reagent_composition_type_id INTO stubs_reagent_comp_type
        FROM labman.reagent_composition_type
        WHERE description = 'shotgun stubs';

    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_stubs, stubs_container_id, 10)
        RETURNING composition_id INTO stubs_composition_id;

    INSERT INTO labman.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (stubs_composition_id, stubs_reagent_comp_type, 'STUBS1')
        RETURNING reagent_composition_id INTO stubs_reagent_composition_id;

    -----------------------------------
    ------ SAMPLE PLATING PROCESS ------
    -----------------------------------
    SELECT process_type_id INTO plating_process_type_id
        FROM labman.process_type
        WHERE description = 'sample plating';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (plating_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO plating_process_id;

    -------------------------------------
    ------ GDNA EXTRACTION PROCESS ------
    -------------------------------------
    SELECT process_type_id INTO gdna_process_type_id
        FROM labman.process_type
        WHERE description = 'gDNA extraction';

    SELECT equipment_id INTO ext_robot_id
        FROM labman.equipment
        WHERE external_id = 'LUCY';

    SELECT equipment_id INTO kf_robot_id
        FROM labman.equipment
        WHERE external_id = 'KF1';

    SELECT equipment_id INTO ext_tool_id
        FROM labman.equipment
        WHERE external_id = '108379Z';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO gdna_process_id;

    INSERT INTO labman.gdna_extraction_process (process_id, epmotion_robot_id, epmotion_tool_id, kingfisher_robot_id, extraction_kit_id)
        VALUES (gdna_process_id, ext_robot_id, ext_tool_id, kf_robot_id, ext_kit_reagent_composition_id)
        RETURNING gdna_extraction_process_id INTO gdna_subprocess_id;

    --------------------------------------
    ------ 16S Library prep process ------
    --------------------------------------
    SELECT process_type_id INTO lib_prep_16s_process_type_id
        FROM labman.process_type
        WHERE description = '16S library prep';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (lib_prep_16s_process_type_id, '10/25/2017 02:10:25-02', 'test@foo.bar')
        RETURNING process_id INTO lib_prep_16s_process_id;

    SELECT equipment_id INTO tm300_8_id
        FROM labman.equipment
        WHERE external_id = '109375A';

    SELECT equipment_id INTO tm50_8_id
        FROM labman.equipment
        WHERE external_id = '311411B';

    SELECT equipment_id INTO proc_robot_id
        FROM labman.equipment
        WHERE external_id = 'JER-E';

    INSERT INTO labman.library_prep_16s_process (process_id, epmotion_robot_id, epmotion_tm300_8_tool_id, epmotion_tm50_8_tool_id, master_mix_id, water_lot_id)
        VALUES (lib_prep_16s_process_id, proc_robot_id, tm300_8_id, tm50_8_id, master_mix_reagent_composition_id, water_reagent_composition_id)
        RETURNING library_prep_16s_process_id INTO lib_prep_16s_subprocess_id;

    ------------------------------------
    ------ QUANTIFICATION PROCESS ------
    ------------------------------------

    SELECT process_type_id INTO pg_quant_process_type_id
        FROM labman.process_type
        WHERE description = 'quantification';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017 19:10:05-07', 'test@foo.bar')
        RETURNING process_id INTO pg_quant_process_id;

    INSERT INTO labman.quantification_process (process_id)
        VALUES (pg_quant_process_id)
        RETURNING quantification_process_id INTO pg_quant_subprocess_id;

    ------------------------------------
    ------ QUANTIFICATION PROCESS ------
    ------------------------------------
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017 01:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO ppg_quant_process_id;

    INSERT INTO labman.quantification_process (process_id)
        VALUES (ppg_quant_process_id)
        RETURNING quantification_process_id INTO ppg_quant_subprocess_id;
    -----------------------------------
    ------ PLATE POOLING PROCESS ------
    -----------------------------------
    SELECT process_type_id INTO p_pool_process_type_id
        FROM labman.process_type
        WHERE description = 'pooling';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO p_pool_process_id;

    INSERT INTO labman.pooling_process (process_id, quantification_process_id, robot_id, destination, pooling_function_data)
        VALUES (p_pool_process_id, pg_quant_subprocess_id, proc_robot_id, 1, '{"function": "amplicon", "parameters": {"total-": 240, "floor-vol-": 2, "floor-conc-": 16}}'::json)
        RETURNING pooling_process_id INTO p_pool_subprocess_id;


    ----------------------------------------
    ------ SEQUENCING POOLING PROCESS ------
    ----------------------------------------
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO s_pool_process_id;

    INSERT INTO labman.pooling_process (process_id, quantification_process_id, robot_id, pooling_function_data)
        VALUES (s_pool_process_id, pg_quant_subprocess_id, proc_robot_id, '{"function": "amplicon_pool", "parameters": {}}'::json)
        RETURNING pooling_process_id INTO s_pool_subprocess_id;

    ---------------------------------
    ------ CREATING THE PLATES ------
    ---------------------------------

    SELECT composition_type_id INTO sample_comp_type_id
        FROM labman.composition_type
        WHERE description = 'sample';

    SELECT sample_composition_type_id INTO sample_type_id
        FROM labman.sample_composition_type
        WHERE external_id = 'experimental sample';

    SELECT sample_composition_type_id INTO vibrio_type_id
        FROM labman.sample_composition_type
        WHERE external_id = 'vibrio.positive.control';

    SELECT sample_composition_type_id INTO blank_type_id
        FROM labman.sample_composition_type
        WHERE external_id = 'blank';

    SELECT sample_composition_type_id INTO empty_type_id
        FROM labman.sample_composition_type
        WHERE external_id = 'empty';

    -- Up to this point we have created all the processes, but we have not created
    -- the different plates that are a result of these processes. The reason that
    -- We did it this way is so we can re-use the same for loop. Otherwise
    -- the SQL gets way more complicated since we will need to query for some
    -- values rather than just directly use them in the for loops that we already have

    SELECT plate_configuration_id INTO deepwell_96_plate_type_id
        FROM labman.plate_configuration
        WHERE description = '96-well deep-well plate';

    -- Sample Plates
    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('Test plate 1', deepwell_96_plate_type_id)
        RETURNING plate_id INTO sample_plate_id;

    -- gDNA plate
    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('Test gDNA plate 1', deepwell_96_plate_type_id)
        RETURNING plate_id INTO gdna_plate_id;

    SELECT composition_type_id INTO gdna_comp_type_id
        FROM labman.composition_type
        WHERE description = 'gDNA';

    -- 16S library prep plate
    SELECT composition_type_id INTO lib_prep_16s_comp_type_id
        FROM labman.composition_type
        WHERE description = '16S library prep';

    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('Test 16S plate 1', deepwell_96_plate_type_id)
        RETURNING plate_id INTO lib_prep_16s_plate_id;

    -- Plate pool
    SELECT composition_type_id INTO pool_comp_type_id
        FROM labman.composition_type
        WHERE description = 'pool';

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, p_pool_process_id, 96)
        RETURNING container_id INTO p_pool_container_id;
    INSERT INTO labman.tube (container_id, external_id)
        VALUES (p_pool_container_id, 'Test Pool from Plate 1');
    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (pool_comp_type_id, p_pool_process_id, p_pool_container_id, 96)
        RETURNING composition_id INTO p_pool_composition_id;
    INSERT INTO labman.pool_composition (composition_id)
        VALUES (p_pool_composition_id)
        RETURNING pool_composition_id INTO p_pool_subcomposition_id;

    -- Quantify plate pools
    INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration)
        VALUES (p_pool_composition_id, ppg_quant_subprocess_id, 25);

    -- Pool sequencing run
    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, s_pool_process_id, 2)
        RETURNING container_id INTO s_pool_container_id;
    INSERT INTO labman.tube (container_id, external_id)
        VALUES (s_pool_container_id, 'Test sequencing pool 1');
    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (pool_comp_type_id, s_pool_process_id, s_pool_container_id, 2)
        RETURNING composition_id INTO s_pool_composition_id;
    INSERT INTO labman.pool_composition (composition_id)
        VALUES (s_pool_composition_id)
        RETURNING pool_composition_id INTO s_pool_subcomposition_id;
    INSERT INTO labman.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
        VALUES (s_pool_subcomposition_id, p_pool_composition_id, 2, 0.25);

    --------------------------------
    ------ SEQUENCING PROCESS ------
    --------------------------------
    SELECT process_type_id INTO sequencing_process_type_id
        FROM labman.process_type
        WHERE description = 'sequencing';

    SELECT equipment_id INTO sequencer_id
        FROM labman.equipment
        WHERE external_id = 'KL-MiSeq';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (sequencing_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO amplicon_sequencing_process_id;

    INSERT INTO labman.sequencing_process (process_id, run_name, experiment, sequencer_id,
                                          fwd_cycles, rev_cycles, assay, principal_investigator)
        VALUES (amplicon_sequencing_process_id, 'Test Run.1', 'TestExperiment1',
                sequencer_id, 151, 151, 'Amplicon', 'test@foo.bar')
        RETURNING sequencing_process_id INTO sequencing_subprocess_id;

    INSERT INTO labman.sequencing_process_lanes (sequencing_process_id, pool_composition_id, lane_number)
        VALUES (sequencing_subprocess_id, s_pool_subcomposition_id, 1);

    INSERT INTO labman.sequencing_process_contacts (sequencing_process_id, contact_id)
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
        FROM labman.equipment
        WHERE external_id = 'Echo550';

    SELECT process_type_id INTO gdna_comp_process_type_id
        FROM labman.process_type
        WHERE description = 'compressed gDNA plates';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_comp_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO gdna_comp_process_id;

    INSERT INTO labman.compression_process (process_id, robot_id)
        VALUES (gdna_comp_process_id, echo_robot_id);

    SELECT composition_type_id INTO compressed_gdna_comp_type_id
        FROM labman.composition_type
        WHERE description = 'compressed gDNA';

    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('Test compressed gDNA plates 1-4', microtiter_384_plate_type_id)
        RETURNING plate_id INTO gdna_comp_plate_id;

    -----------------------------------------
    ------ gDNA QUANTIFICATION PROCESS ------
    -----------------------------------------
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO mg_gdna_quant_process_id;

    INSERT INTO labman.quantification_process (process_id)
        VALUES (mg_gdna_quant_process_id)
        RETURNING quantification_process_id INTO mg_gdna_quant_subprocess_id;

    ----------------------------------------
    ------ gDNA NORMALIZATION PROCESS ------
    ----------------------------------------
    SELECT process_type_id INTO gdna_norm_process_type_id
        FROM labman.process_type
        WHERE description = 'gDNA normalization';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (gdna_norm_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO gdna_norm_process_id;

    INSERT INTO labman.normalization_process (process_id, quantitation_process_id, water_lot_id, normalization_function_data)
        VALUES (gdna_norm_process_id, mg_gdna_quant_subprocess_id, water_reagent_composition_id, '{"function": "default", "parameters": {"total_volume": 3500, "reformat": false, "target_dna": 5, "resolution": 2.5, "min_vol": 2.5, "max_volume": 3500}}'::json)
        RETURNING normalization_process_id INTO gdna_norm_subprocess_id;

    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('Test normalized gDNA plates 1-4', microtiter_384_plate_type_id)
        RETURNING plate_id INTO gdna_norm_plate_id;

    SELECT composition_type_id INTO gdna_norm_comp_type_id
        FROM labman.composition_type
        WHERE description = 'normalized gDNA';

    -------------------------------------
    ------ SHOTGUN LIBRARY PROCESS ------
    -------------------------------------
    SELECT process_type_id INTO shotgun_lib_process_type_id
        FROM labman.process_type
        WHERE description = 'shotgun library prep';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (shotgun_lib_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO shotgun_lib_process_id;

    INSERT INTO labman.library_prep_shotgun_process (process_id, kappa_hyper_plus_kit_id, stub_lot_id, normalization_process_id)
        VALUES (shotgun_lib_process_id, khp_reagent_composition_id, stubs_reagent_composition_id, gdna_norm_subprocess_id);

    INSERT INTO labman.plate (external_id, plate_configuration_id)
        VALUES ('Test shotgun library plates 1-4', microtiter_384_plate_type_id)
        RETURNING plate_id INTO shotgun_lib_plate_id;

    SELECT composition_type_id INTO shotgun_lib_comp_type_id
        FROM labman.composition_type
        WHERE description = 'shotgun library prep';

    combo_idx := 0;

    --------------------------------------------
    ------ LIBRARY QUANTIFICATION PROCESS ------
    --------------------------------------------
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (pg_quant_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO sh_lib_quant_process_id;

    INSERT INTO labman.quantification_process (process_id)
        VALUES (sh_lib_quant_process_id)
        RETURNING quantification_process_id INTO sh_lib_quant_subprocess_id;

    -----------------------------
    ------ POOLING PROCESS ------
    -----------------------------
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (p_pool_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO sh_pool_process_id;

    INSERT INTO labman.pooling_process (process_id, quantification_process_id, robot_id, pooling_function_data)
        VALUES (sh_pool_process_id, sh_lib_quant_subprocess_id, proc_robot_id, '{"function": "equal", "parameters": {"volume-": 200, "lib-size-": 500}}')
        RETURNING pooling_process_id INTO sh_pool_subprocess_id;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, sh_pool_process_id, 384)
        RETURNING container_id INTO sh_pool_container_id;
    INSERT INTO labman.tube (container_id, external_id)
        VALUES (sh_pool_container_id, 'Test pool from Shotgun plates 1-4');
    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (pool_comp_type_id, sh_pool_process_id, sh_pool_container_id, 384)
        RETURNING composition_id INTO sh_pool_composition_id;
    INSERT INTO labman.pool_composition (composition_id)
        VALUES (sh_pool_composition_id)
        RETURNING pool_composition_id INTO sh_pool_subcomposition_id;

    --------------------------------
    ------ SEQUENCING PROCESS ------
    --------------------------------
    SELECT equipment_id INTO sequencer_id
        FROM labman.equipment
        WHERE external_id = 'IGM-HiSeq4000';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (sequencing_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
        RETURNING process_id INTO shotgun_sequencing_process_id;

    INSERT INTO labman.sequencing_process (process_id, run_name, experiment, sequencer_id,
                                          fwd_cycles, rev_cycles, assay, principal_investigator)
        VALUES (shotgun_sequencing_process_id, 'TestShotgunRun1', 'TestExperimentShotgun1',
                sequencer_id, 151, 151, 'Metagenomics','test@foo.bar')
        RETURNING sequencing_process_id INTO shotgun_sequencing_subprocess_id;

    INSERT INTO labman.sequencing_process_lanes (sequencing_process_id, pool_composition_id, lane_number)
        VALUES (shotgun_sequencing_subprocess_id, sh_pool_subcomposition_id, 1);

    INSERT INTO labman.sequencing_process_contacts (sequencing_process_id, contact_id)
        VALUES (shotgun_sequencing_subprocess_id, 'shared@foo.bar'),
               (shotgun_sequencing_subprocess_id, 'demo@microbio.me');

    ------------------------------------------
    ------ SEQUENCING PROCESS ERROR CASE------
    ------------------------------------------
    SELECT equipment_id INTO sequencer_id
        FROM labman.equipment
        WHERE external_id = 'IGM-HiSeq4000';

    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (sequencing_process_type_id, '10/25/2017', 'test@foo.bar')
        RETURNING process_id INTO shotgun_sequencing_process_id;

    INSERT INTO labman.sequencing_process (process_id, run_name, experiment, sequencer_id,
                                          fwd_cycles, rev_cycles, assay, principal_investigator)
        VALUES (shotgun_sequencing_process_id, 'TestNewRun1', 'TestExperimentNew1',
                sequencer_id, 151, 151, 'NewKindOfAssay','test@foo.bar')
        RETURNING sequencing_process_id INTO shotgun_sequencing_subprocess_id;

    INSERT INTO labman.sequencing_process_lanes (sequencing_process_id, pool_composition_id, lane_number)
        VALUES (shotgun_sequencing_subprocess_id, sh_pool_subcomposition_id, 1);

    INSERT INTO labman.sequencing_process_contacts (sequencing_process_id, contact_id)
        VALUES (shotgun_sequencing_subprocess_id, 'shared@foo.bar'),
               (shotgun_sequencing_subprocess_id, 'demo@microbio.me');


    --------------------------------------------
    ---- LIBRARY QUANTIFICATION PROCESS REDO ---
    --------------------------------------------
    -- Putting it here at the end so a not to screw up any of the ids expected for
    -- processes defined above.
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id, notes)
        VALUES (pg_quant_process_type_id, '10/26/2017 03:10:25-07', 'test@foo.bar', 'Requantification--oops')
        RETURNING process_id INTO sh_lib_quant_process_id2;

    INSERT INTO labman.quantification_process (process_id)
        VALUES (sh_lib_quant_process_id2)
        RETURNING quantification_process_id INTO sh_lib_quant_subprocess_id2;


    --------------------------------------------
    --- WELLS, CONTAINERS, COMPOSITIONS, ETC ---
    --------------------------------------------
    -- loop through as many fake samples as would be on 4 96-well plates
    FOR plate_increment IN 1..4 LOOP
        -- use the plate/pool created above AND
        -- make additional plates and pools for 3 new plates so can do a
        -- realistic compression step.
        -- Note: Could make all the plates/pools here, but I want to limit
        -- how much I change the ids of the existing plates/pools/processes,
        -- since they are hard-coded into the unit tests.
        IF plate_increment = 1 THEN
            curr_plating_process_id := plating_process_id;
            curr_sample_plate_id := sample_plate_id;
            curr_gdna_process_id := gdna_process_id;
            curr_gdna_plate_id := gdna_plate_id;
            curr_lib_prep_16s_process_id := lib_prep_16s_process_id;
            curr_lib_prep_16s_plate_id := lib_prep_16s_plate_id;
            curr_p_pool_process_id := p_pool_process_id;
            curr_p_pool_container_id := p_pool_container_id;
            curr_p_pool_composition_id := p_pool_composition_id;
            curr_p_pool_subcomposition_id := p_pool_subcomposition_id;
        ELSE
            -- Make a new sample plating process and a new sample plate
            INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
                VALUES (plating_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
                RETURNING process_id INTO curr_plating_process_id;

            curr_sample_plate_name := 'Test plate ' || plate_increment;
            INSERT INTO labman.plate (external_id, plate_configuration_id)
                VALUES (curr_sample_plate_name, deepwell_96_plate_type_id)
                RETURNING plate_id INTO curr_sample_plate_id;

            -- Make a new gdna extraction process and a new gdna plate
            INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
                VALUES (gdna_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
                RETURNING process_id INTO curr_gdna_process_id;

            INSERT INTO labman.gdna_extraction_process (process_id, epmotion_robot_id, epmotion_tool_id, kingfisher_robot_id, extraction_kit_id)
                VALUES (curr_gdna_process_id, ext_robot_id, ext_tool_id, kf_robot_id, ext_kit_reagent_composition_id);

            curr_gdna_plate_name := 'Test gDNA plate ' || plate_increment;
            INSERT INTO labman.plate (external_id, plate_configuration_id)
                VALUES (curr_gdna_plate_name, deepwell_96_plate_type_id)
                RETURNING plate_id INTO curr_gdna_plate_id;

            -- Make a new 16s library prep process and a new 16s lib prep plate
            INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
                VALUES (lib_prep_16s_process_type_id, '10/25/2017 02:10:25-02', 'test@foo.bar')
                RETURNING process_id INTO curr_lib_prep_16s_process_id;

            INSERT INTO labman.library_prep_16s_process (process_id, epmotion_robot_id, epmotion_tm300_8_tool_id, epmotion_tm50_8_tool_id, master_mix_id, water_lot_id)
                VALUES (curr_lib_prep_16s_process_id, proc_robot_id, tm300_8_id, tm50_8_id, master_mix_reagent_composition_id, water_reagent_composition_id);

            curr_lib_prep_plate_name := 'Test 16S plate ' || plate_increment;
            INSERT INTO labman.plate (external_id, plate_configuration_id)
                VALUES (curr_lib_prep_plate_name, deepwell_96_plate_type_id)
                RETURNING plate_id INTO curr_lib_prep_16s_plate_id;

            -- Make a new plate pooling process and plate pool
            INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
                VALUES (p_pool_process_type_id, '10/25/2017 19:10:25-07', 'test@foo.bar')
                RETURNING process_id INTO curr_p_pool_process_id;

            INSERT INTO labman.pooling_process (process_id, quantification_process_id, robot_id, destination, pooling_function_data)
                VALUES (curr_p_pool_process_id, pg_quant_subprocess_id, proc_robot_id, 1, '{"function": "amplicon", "parameters": {"total-": 240, "floor-vol-": 2, "floor-conc-": 16}}'::json);

            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (tube_container_type_id, p_pool_process_id, 96)
                RETURNING container_id INTO curr_p_pool_container_id;

            curr_pool_name := 'Test Pool from Plate ' || plate_increment;
            INSERT INTO labman.tube (container_id, external_id)
                VALUES (curr_p_pool_container_id, curr_pool_name);

            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (pool_comp_type_id, curr_p_pool_process_id, curr_p_pool_container_id, 96)
                RETURNING composition_id INTO curr_p_pool_composition_id;

            INSERT INTO labman.pool_composition (composition_id)
                VALUES (curr_p_pool_composition_id)
                RETURNING pool_composition_id INTO curr_p_pool_subcomposition_id;

            -- Make a new plate pool quantification calculation
            INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration)
                VALUES (curr_p_pool_composition_id, ppg_quant_subprocess_id, 25);

            INSERT INTO labman.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
                VALUES (s_pool_subcomposition_id, curr_p_pool_composition_id, 2, 0.25);
        END IF;

        FOR idx_col_well IN 1..12 LOOP
            FOR idx_row_well IN 1..8 LOOP

            -- generate fake data for the current sample for all the
            -- different values we will need to input for it throughout
            -- both amplicon and shotgun pipelines.
            -- to make this easier, we are going to put the same 12 samples
            -- in the first 6 rows of the sample plate, in the 7th row we are
            -- going to put vibrio controls, and in the 8th row we are going
            -- to leave it for blanks

            IF idx_row_well <= 6 THEN
                -- Get information for a sample
                plating_sample_comp_type_id := sample_type_id;
                SELECT sample_id INTO plating_sample_id
                    FROM qiita.study_sample
                    WHERE study_id = 1
                    ORDER BY sample_id
                    OFFSET (idx_row_well - 1)
                    LIMIT 1;
                plating_sample_content := plating_sample_id || '.' || curr_sample_plate_id::text || '.' || chr(ascii('@') + idx_row_well) || idx_col_well::text;
                gdna_sample_conc := 12.068;
                norm_dna_vol := 415;
                norm_water_vol := 3085;
                sh_lib_raw_sample_conc := 12.068;
                sh_lib_comp_sample_conc := 36.569;
            ELSIF idx_row_well = 7 THEN
                -- Get information for vibrio
                plating_sample_comp_type_id := vibrio_type_id;
                plating_sample_id := NULL;
                plating_sample_content := 'vibrio.positive.control.' || curr_sample_plate_id::text || '.G' || idx_col_well::text;
                gdna_sample_conc := 6.089;
                norm_dna_vol := 820;
                norm_water_vol := 2680;
                sh_lib_raw_sample_conc := 8.904;
                sh_lib_comp_sample_conc := 26.981;
            ELSIF idx_col_well = 12 THEN
                -- The last column of the last row will get an empty value
                plating_sample_comp_type_id := empty_type_id;
                plating_sample_id := NULL;
                plating_sample_content := 'empty.' || curr_sample_plate_id::text || '.H12';
            ELSE
                -- We are in the 8th row, get information for blanks
                plating_sample_comp_type_id := blank_type_id;
                plating_sample_id := NULL;
                plating_sample_content := 'blank.' || curr_sample_plate_id::text || '.H' || idx_col_well::text;
                gdna_sample_conc := 0.342;
                norm_dna_vol := 3500;
                norm_water_vol := 0;
                sh_lib_raw_sample_conc := 0.342;
                sh_lib_comp_sample_conc := 1.036;
            END IF;

            -- container, well, and composition for the current sample on sample plate
            -- (note there are 4 of these plates--hence use of curr_sample_plate_id)
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, curr_plating_process_id, 10)
                RETURNING container_id INTO plating_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (plating_container_id, curr_sample_plate_id, idx_row_well, idx_col_well);
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (sample_comp_type_id, curr_plating_process_id, plating_container_id, 10)
                RETURNING composition_id INTO plating_composition_id;
            INSERT INTO labman.sample_composition (composition_id, sample_composition_type_id, sample_id, content)
                VALUES (plating_composition_id, plating_sample_comp_type_id, plating_sample_id, plating_sample_content)
                RETURNING sample_composition_id INTO plating_sample_composition_id;

            CONTINUE WHEN idx_row_well = 8 AND idx_col_well = 12;

            -- container, well, and composition for the current sample on gdna plate
            -- (note there are 4 of these plates--hence use of curr_gdna_plate_id)
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, curr_gdna_process_id, 10)
                RETURNING container_id INTO gdna_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (gdna_container_id, curr_gdna_plate_id, idx_row_well, idx_col_well);
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (gdna_comp_type_id, curr_gdna_process_id, gdna_container_id, 10)
                RETURNING composition_id INTO gdna_comp_id;
            INSERT INTO labman.gdna_composition (composition_id, sample_composition_id)
                VALUES (gdna_comp_id, plating_sample_composition_id)
                RETURNING gdna_composition_id INTO gdna_subcomposition_id;

            -- primer for the current sample's position on the EMP 16S primer plate 1
            -- TODO: Should I change this to use different primer plates for the four gdna plates?
            SELECT primer_composition_id INTO primer_comp_id
                FROM labman.primer_composition
                    JOIN labman.composition USING (composition_id)
                    JOIN labman.well USING (container_id)
                    JOIN labman.plate USING (plate_id)
                WHERE row_num = idx_row_well
                    AND col_num = idx_col_well
                    AND external_id = 'EMP 16S V4 primer plate 1 10/23/2017';

            -- container, well, and composition for the current sample on library prep plate
            -- (note there are 4 of these plates--hence use of curr_lib_prep_16s_plate_id)
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, curr_lib_prep_16s_process_id, 10)
                RETURNING container_id INTO lib_prep_16s_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (lib_prep_16s_container_id, curr_lib_prep_16s_plate_id, idx_row_well, idx_col_well);
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (lib_prep_16s_comp_type_id, curr_lib_prep_16s_process_id, lib_prep_16s_container_id, 10)
                RETURNING composition_id INTO lib_prep_16s_composition_id;
            INSERT INTO labman.library_prep_16s_composition (composition_id, gdna_composition_id, primer_composition_id)
                VALUES (lib_prep_16s_composition_id, gdna_subcomposition_id, primer_comp_id);

            -- concentration calculation for current sample's quantification
            -- (Note there are NOT 4 of these; it is possible to quantify more than one plate in the same process)
            IF idx_row_well <= 7 THEN
                INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration, computed_concentration)
                    VALUES (lib_prep_16s_composition_id, pg_quant_subprocess_id, 20., 60.6060);
            ELSE
                INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration, computed_concentration)
                    VALUES (lib_prep_16s_composition_id, pg_quant_subprocess_id, 1., 3.0303);
            END IF;

            -- pool composition component for current sample in plate pool
            -- (note there are 4 different plate pools--hence curr_p_pool_subcomposition_id)
            INSERT INTO labman.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
                VALUES (curr_p_pool_subcomposition_id, lib_prep_16s_composition_id, 1, 1/96);

            -- METAGENOMICS:
            IF plate_increment = 1 THEN
              row_pad := 0;
              col_pad := 0;
            ELSIF plate_increment = 2 THEN
              row_pad := 0;
              col_pad := 1;
            ELSIF plate_increment = 3 THEN
              row_pad := 1;
              col_pad := 0;
            ELSIF plate_increment = 4 THEN
              row_pad := 1;
              col_pad := 1;
            END IF;

            mg_row_id := ((idx_row_well - 1) * 2) + row_pad + 1;
            mg_col_id := ((idx_col_well - 1) * 2) + col_pad + 1;

            -- container, well, and composition for current sample's gdna compression onto the 384-well plate
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, gdna_comp_process_id, 10)
                RETURNING container_id INTO gdna_comp_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (gdna_comp_container_id, gdna_comp_plate_id, mg_row_id, mg_col_id);
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (compressed_gdna_comp_type_id, gdna_comp_process_id, gdna_comp_container_id, 10)
                RETURNING composition_id INTO gdna_comp_comp_id;
            INSERT INTO labman.compressed_gdna_composition (composition_id, gdna_composition_id)
                VALUES (gdna_comp_comp_id, gdna_subcomposition_id)
                RETURNING compressed_gdna_composition_id INTO gdna_comp_subcomposition_id;

            -- concentration calculation for current sample's compressed gdna quantification
            INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration)
                VALUES (gdna_comp_comp_id, mg_gdna_quant_subprocess_id, gdna_sample_conc);

            -- container, well, and composition for current sample on the normalized plate
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, gdna_norm_process_id, 3500)
                RETURNING container_id INTO gdna_norm_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (gdna_norm_container_id, gdna_norm_plate_id, mg_row_id, mg_col_id);
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (gdna_norm_comp_type_id, gdna_norm_process_id, gdna_norm_container_id, 3500)
                RETURNING composition_id INTO gdna_norm_comp_id;
            INSERT INTO labman.normalized_gdna_composition (composition_id, compressed_gdna_composition_id, dna_volume, water_volume)
                VALUES (gdna_norm_comp_id, gdna_comp_subcomposition_id, norm_dna_vol, norm_water_vol)
                RETURNING normalized_gdna_composition_id INTO gdna_norm_subcomp_id;

            -- shotgun primer combo for current sample, given current combo index
            SELECT primer_composition_id INTO i5_primer_id
                FROM labman.shotgun_combo_primer_set c
                    JOIN labman.primer_composition pci5 ON c.i5_primer_set_composition_id = pci5.primer_set_composition_id
                WHERE shotgun_combo_primer_set_id = (combo_idx + 1);
            SELECT primer_composition_id INTO i7_primer_id
                FROM labman.shotgun_combo_primer_set c
                    JOIN labman.primer_composition pci7 ON c.i7_primer_set_composition_id = pci7.primer_set_composition_id
                WHERE shotgun_combo_primer_set_id = (combo_idx + 1);
            combo_idx := combo_idx + 1;

            -- container, well, and composition for current sample on the library plate
            INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
                VALUES (well_container_type_id, shotgun_lib_process_id, 4000)
                RETURNING container_id INTO shotgun_lib_container_id;
            INSERT INTO labman.well (container_id, plate_id, row_num, col_num)
                VALUES (shotgun_lib_container_id, shotgun_lib_plate_id, mg_row_id, mg_col_id);
            INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
                VALUES (shotgun_lib_comp_type_id, shotgun_lib_process_id, shotgun_lib_container_id, 4000)
                RETURNING composition_id INTO shotgun_lib_comp_id;
            INSERT INTO labman.library_prep_shotgun_composition (composition_id, normalized_gdna_composition_id, i5_primer_composition_id, i7_primer_composition_id)
                VALUES (shotgun_lib_comp_id, gdna_norm_subcomp_id, i5_primer_id, i7_primer_id);

            -- concentration calculations for current sample's quantification on the library plate
            INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration, computed_concentration)
                VALUES (shotgun_lib_comp_id, sh_lib_quant_subprocess_id, sh_lib_raw_sample_conc, sh_lib_comp_sample_conc);

            -- concentration calculations for current sample's RE-quantification on the library plate
            INSERT INTO labman.concentration_calculation (quantitated_composition_id, upstream_process_id, raw_concentration, computed_concentration)
                VALUES (shotgun_lib_comp_id, sh_lib_quant_subprocess_id2, sh_lib_raw_sample_conc+1, sh_lib_comp_sample_conc+2);

            -- pool composition component for current sample in final shotgun pool
            INSERT INTO labman.pool_composition_components (output_pool_composition_id, input_composition_id, input_volume, percentage_of_output)
                VALUES (sh_pool_subcomposition_id, shotgun_lib_comp_id, 1, 1/384);

            END LOOP; -- index col well
        END LOOP; -- index row well
    END LOOP; -- plate increment

    -- Update the combo index value
    UPDATE labman.shotgun_primer_set SET current_combo_index = combo_idx;

    -- Add 'Not applicable' reagents for externally extracted samples
    INSERT INTO labman.process (process_type_id, run_date, run_personnel_id)
        VALUES (rc_process_type_id, '05/01/1984', 'test@foo.bar')
        RETURNING process_id INTO rc_process_id_none;

    INSERT INTO labman.container (container_type_id, latest_upstream_process_id, remaining_volume)
        VALUES (tube_container_type_id, rc_process_id_none, 42)
        RETURNING container_id INTO none_container_id;

    INSERT INTO labman.tube (container_id, external_id)
        VALUES (none_container_id, 'Not applicable');

    SELECT reagent_composition_type_id INTO none_reagent_comp_type
        FROM labman.reagent_composition_type
        WHERE description = 'extraction kit';

    INSERT INTO labman.composition (composition_type_id, upstream_process_id, container_id, total_volume)
        VALUES (reagent_comp_type, rc_process_id_none, none_container_id, 42)
        RETURNING composition_id INTO none_composition_id;

    INSERT INTO labman.reagent_composition (composition_id, reagent_composition_type_id, external_lot_id)
        VALUES (none_composition_id, none_reagent_comp_type, 'Not applicable')
        RETURNING reagent_composition_id INTO none_reagent_composition_id;

END $do$
