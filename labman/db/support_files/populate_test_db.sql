-- Controlling for the Ids here is more complex. Hence we are going
-- to populate the DB in a function so we can easily keep track of the
-- ids

DO $do$
DECLARE
    wpp_process_type_id         bigint;
    wpp_process_id              bigint;
    wpp_emp_primer_set_id       bigint;
    wpp_creation_process_id     bigint;
    wpp_plate_id                bigint;
    wpp_container_id            bigint;
    wpp_composition_id          bigint;
    plate_idx                   int;
    idx_row_well                int;
    idx_col_well                int;
    well_container_type_id      bigint;
    primer_composition_type_id  bigint;
    microtiter_96_plate_type_id bigint;
    psc_id                      bigint;
BEGIN
    -- Create the new working plates
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
        WHERE external_identifier = 'EMP primer set';
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
        INSERT INTO qiita.plate (external_identifier, plate_configuration_id, discarded)
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
                    WHERE w.row_num = idx_row_well AND w.col_num = idx_col_well AND p.external_identifier = 'EMP primer plate ' || plate_idx;
                INSERT INTO qiita.primer_composition (composition_id, primer_set_composition_id)
                    VALUES (wpp_composition_id, psc_id);
            END LOOP;  -- Column loop
        END LOOP; -- Row loop
    END LOOP; -- Plate loop

    -- Add a 16S run
END $do$
