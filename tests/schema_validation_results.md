# Schema validation results — v1.2.0 (promoted from v1.2.0-candidate)

- Harness: `tests/validate_schema_candidate.py`
- SQLite version (python sqlite3): 3.54.1
- SQLite version (CLI): 3.54.1
- Executed: 2026-11-12T05:58:19+00:00
- Schema file: schema/v1.2.0.sql
- Promotion record: run 1 on v1.2.0-candidate.sql = 111/112 (defect D-1); one-line CHECK correction applied; run 2 = 112/112; promoted to v1.2.0.sql.
- Tests executed: 112  passed: 112  failed: 0  blocked: 0
- Tables: 20/20 expected present: True
- Triggers present: True (8)
- Expression index present: True
- PRAGMA foreign_key_check: no violations
- PRAGMA integrity_check: ok
- JSON1: available


## 1. Temporal-anchor sequences

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 1 | pass | PASS | all statements executed | PASS |
| 2 | pass | PASS | all statements executed | PASS |
| 3 | fail | PASS | IntegrityError: event must not anchor itself via its time_reference | PASS |
| 4 (FK-OFF defensive) | fail | PASS | IntegrityError: event must not anchor itself via its time_reference | PASS |
| 5 | fail | PASS | IntegrityError: time_reference must not be anchored on an event that references it | PASS |
| 6 (FK-OFF defensive) | fail | PASS | IntegrityError: event must not anchor itself via its time_reference | PASS |
| 7 | fail | PASS | IntegrityError: FOREIGN KEY constraint failed | PASS |
| 8 | fail | PASS | IntegrityError: FOREIGN KEY constraint failed | PASS |
| 9 (FK-OFF defensive) | fail | PASS | IntegrityError: time_reference must not be anchored on an event that references it | PASS |

## 2. Temporal-reference semantics

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 10 | pass | PASS | all statements executed | PASS |
| 11 | pass | PASS | all statements executed | PASS |
| 12 | fail | PASS | IntegrityError: CHECK constraint failed: chk_time_reference_kind | PASS |
| 12 | fail | PASS | IntegrityError: CHECK constraint failed: reference_absolute_time IS NULL
           OR reference_absolute_time GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*' | PASS |
| 13 | pass | PASS | all statements executed | PASS |
| 14 | fail | PASS | IntegrityError: CHECK constraint failed: reference_numeric_unit IS NULL
        OR reference_numeric_unit IN ('s','ms','us','ns','min','frame','count') | PASS |
| 14 | fail | PASS | IntegrityError: CHECK constraint failed: reference_kind <> 'numeric'
           OR (reference_numeric_value IS NOT NULL AND reference_numeric_unit IS NOT NULL) | PASS |
| 14 | fail | PASS | IntegrityError: CHECK constraint failed: reference_kind IN ('event','absolute')
           OR (reference_offset_s IS NULL AND reference_offset_uncertainty_s IS NULL) | PASS |
| 15 | pass | PASS | all statements executed | PASS |
| 16 | pass | PASS | all statements executed | PASS |
| 17 | fail | PASS | IntegrityError: CHECK constraint failed: chk_time_reference_kind | PASS |
| 17 | fail | PASS | IntegrityError: CHECK constraint failed: reference_kind = 'numeric'
           OR (reference_numeric_value IS NULL AND reference_numeric_unit IS NULL
               AND reference_numeric_uncertainty IS NULL) | PASS |
| 18 | fail | PASS | IntegrityError: CHECK constraint failed: reference_offset_uncertainty_s IS NULL OR reference_offset_s IS NOT NULL | PASS |
| 19 | pass | PASS | all statements executed | PASS |
| 20 | fail | PASS | IntegrityError: FOREIGN KEY constraint failed | PASS |

## 3. Event time-base integrity

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 21 | pass | PASS | all statements executed | PASS |
| 22 | fail | PASS | IntegrityError: CHECK constraint failed: event_frame_start IS NULL OR event_frame_start >= 0 | PASS |
| 23 | fail | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | PASS |
| 24 | fail | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | PASS |
| 25 | fail | PASS | IntegrityError: CHECK constraint failed: event_datetime_end IS NULL OR event_datetime_start IS NOT NULL | PASS |
| 26 | fail | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | PASS |
| 27 | fail | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | PASS |
| 28 | pass | PASS | all statements executed | PASS |

## 4. measurement_sample timestamps

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 29 | pass | PASS | all statements executed | PASS |
| 30 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_timestamp_consistency | PASS |
| 31 | pass | PASS | all statements executed | PASS |
| 32 | fail | PASS | IntegrityError: CHECK constraint failed: timestamp_epoch_utc IS NULL
        OR (timestamp_parsing_status = 'parsed'
            AND timestamp_representation IN (
                'iso8601_datetime','unix_time','excel_serial_number','labview_timestamp')) | PASS |
| 33 | pass | PASS | all statements executed | PASS |
| 34 | fail | PASS | IntegrityError: CHECK constraint failed: timestamp_epoch_utc IS NULL
        OR (timestamp_parsing_status = 'parsed'
            AND timestamp_representation IN (
                'iso8601_datetime','unix_time','excel_serial_number','labview_timestamp')) | PASS |
| 35 | fail | PASS | IntegrityError: CHECK constraint failed: timestamp_epoch_utc IS NULL
           OR (timestamp_epoch_utc >= -2208988800 AND timestamp_epoch_utc < 4102444800) | PASS |
| 36 | pass | PASS | all statements executed | PASS |
| 37 | pass | PASS | all statements executed | PASS |
| 38 | pass | PASS | all statements executed | PASS |
| 39 | fail | PASS | IntegrityError: CHECK constraint failed: (timestamp_representation = 'unknown_representation'
         AND timestamp_parsing_status = 'unknown'
         AND original_timestamp_parsed IS NULL
         AND timestamp_epoch_utc IS NULL)
        OR timestamp_representation <> 'unknown_representation' | PASS |
| 40 | pass | PASS | all statements executed | PASS |

## 5. measurement_sample values

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 41 | pass | PASS | all statements executed | PASS |
| 42 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 43 | pass | PASS | all statements executed | PASS |
| 44 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 44 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 45 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 45 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 46 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 47 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 48 | pass | PASS | all statements executed | PASS |
| 49 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | PASS |
| 49 | fail | PASS | IntegrityError: CHECK constraint failed: detection_limit_value IS NULL OR detection_limit_unit IS NOT NULL | PASS |
| 50 | pass | PASS | all statements executed | PASS |
| 51 | fail | PASS | IntegrityError: CHECK constraint failed: chk_sample_normalization_traceability | PASS |
| 52 | pass | PASS | all statements executed | PASS |
| 53 | fail | PASS | IntegrityError: CHECK constraint failed: quality_flag IS NULL OR quality_flag IN (
            'ok','saturated','outlier','contaminated','interpolated','repeated','estimated','suspect') | PASS |

## 6. Run conditions, composition, geometry

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 54 | fail | PASS | IntegrityError: CHECK constraint failed: (
            pressure IS NULL
            AND pressure_uncertainty IS NULL
            AND pressure_interval_low IS NULL
            AND pressure_interval_high IS NULL
        )
        OR pressure_unit IS NOT NULL | PASS |
| 55 | fail | PASS | IntegrityError: CHECK constraint failed: (
            pressure IS NULL
            AND pressure_uncertainty IS NULL
            AND pressure_interval_low IS NULL
            AND pressure_interval_high IS NULL
        )
        OR pressure_unit IS NOT NULL | PASS |
| 56 | fail | PASS | IntegrityError: CHECK constraint failed: temperature_uncertainty IS NULL
           OR (temperature IS NOT NULL AND temperature_unit IS NOT NULL) | PASS |
| 56 | fail | PASS | IntegrityError: CHECK constraint failed: flow_velocity_uncertainty IS NULL
           OR (flow_velocity IS NOT NULL AND flow_velocity_unit IS NOT NULL) | PASS |
| 56 | fail | PASS | IntegrityError: CHECK constraint failed: temperature IS NULL OR temperature_unit IS NOT NULL | PASS |
| 57 | pass | PASS | all statements executed | PASS |
| 58 | fail | PASS | IntegrityError: CHECK constraint failed: mole_fraction_uncertainty IS NULL OR mole_fraction IS NOT NULL | PASS |
| 58 | fail | PASS | IntegrityError: CHECK constraint failed: mole_fraction_approx = 0 OR mole_fraction IS NOT NULL | PASS |
| 59 | pass | PASS | all statements executed | PASS |
| 60 | fail | PASS | IntegrityError: CHECK constraint failed: width IS NULL OR width_unit IS NOT NULL | PASS |
| 61 | fail | PASS | IntegrityError: CHECK constraint failed: width_uncertainty IS NULL OR width IS NOT NULL | PASS |
| 61 | fail | PASS | IntegrityError: CHECK constraint failed: thickness_uncertainty IS NULL OR thickness IS NOT NULL | PASS |
| 62 | fail | PASS | IntegrityError: CHECK constraint failed: support_fiber = 1 OR fiber_diameter IS NULL | PASS |
| 63 | fail | PASS | IntegrityError: CHECK constraint failed: fiber_diameter IS NULL OR fiber_diameter_unit IS NOT NULL | PASS |
| 64 | fail | PASS | IntegrityError: CHECK constraint failed: initial_diameter_uncertainty IS NULL OR initial_diameter IS NOT NULL | PASS |
| 64 | fail | PASS | IntegrityError: CHECK constraint failed: fiber_diameter_uncertainty IS NULL OR fiber_diameter IS NOT NULL | PASS |
| 65 | fail | PASS | IntegrityError: run already has droplet_geometry | PASS |

## 7. clock_sync, files, provenance, comparability

| # | Expected | Observed | Detail | Status |
| --- | --- | --- | --- | --- |
| 66 | pass | PASS | all statements executed | PASS |
| 67 | fail | PASS | IntegrityError: UNIQUE constraint failed: clock_sync.run_id, clock_sync.source_domain_id, clock_sync.target_domain_id, clock_sync.sync_segment_id | PASS |
| 68 | pass | PASS | all statements executed | PASS |
| 69 | fail | PASS | IntegrityError: CHECK constraint failed: sync_status <> 'unknown'
           OR (offset_seconds IS NULL AND sync_method IS NULL) | PASS |
| 69 | fail | PASS | IntegrityError: CHECK constraint failed: sync_status <> 'established'
           OR (offset_seconds IS NOT NULL AND sync_method IS NOT NULL) | PASS |
| 69 | fail | PASS | IntegrityError: CHECK constraint failed: sync_status <> 'invalidated' OR notes IS NOT NULL | PASS |
| 69 | fail | PASS | IntegrityError: CHECK constraint failed: source_domain_id <> target_domain_id | PASS |
| 70 | fail | PASS | IntegrityError: CHECK constraint failed: valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to | PASS |
| 71 | pass | PASS | all statements executed | PASS |
| 72 | fail | PASS | IntegrityError: CHECK constraint failed: conversion_offset IS NULL OR conversion_scale IS NOT NULL | PASS |
| 72 | fail | PASS | IntegrityError: CHECK constraint failed: conversion_scale IS NULL OR conversion_scale <> 0 | PASS |
| 73 | pass | PASS | all statements executed | PASS |
| 74 | pass | PASS | all statements executed | PASS |
| 75 | fail | PASS | IntegrityError: CHECK constraint failed: length(sha256_checksum) = 64
        AND lower(sha256_checksum) = sha256_checksum
        AND sha256_checksum NOT GLOB '*[^0-9a-f]*' | PASS |
| 76 | fail | PASS | IntegrityError: CHECK constraint failed: is_archive = 1 OR archive_member_count IS NULL | PASS |
| 77 | pass | PASS | all statements executed | PASS |
| 78 | pass | PASS | all statements executed | PASS |
| 79 | fail | PASS | IntegrityError: source.authors must be a JSON array of strings | PASS |
| 79 | fail | PASS | IntegrityError: source.authors must be a JSON array of strings | PASS |
| 79 | fail | PASS | IntegrityError: source.authors must be a JSON array of strings | PASS |
| 79 | fail | PASS | IntegrityError: source.authors must be a JSON array of strings | PASS |
| 79 | fail | PASS | IntegrityError: source.authors must be a JSON array of strings | PASS |
| 80 | fail | PASS | OperationalError: malformed JSON | PASS |
| 81 | pass | PASS | all statements executed | PASS |
| 81 | fail | PASS | IntegrityError: FOREIGN KEY constraint failed | PASS |
| 82 | fail | PASS | IntegrityError: UNIQUE constraint failed: index 'ux_comparability_unordered_pair' | PASS |
| 83 | fail | PASS | IntegrityError: CHECK constraint failed: chk_comparability_classification | PASS |
| 83 | fail | PASS | IntegrityError: CHECK constraint failed: chk_comparability_classification | PASS |
| 83 | fail | PASS | IntegrityError: CHECK constraint failed: (run1_value_numeric IS NULL AND run2_value_numeric IS NULL)
           OR comparison_unit IS NOT NULL | PASS |
| 83 | fail | PASS | IntegrityError: CHECK constraint failed: review_status = 'pending_expert_review' OR reviewed_by IS NOT NULL | PASS |
| 84 | pass | PASS | all statements executed | PASS |
| 85 | fail | PASS | IntegrityError: CHECK constraint failed: (measurement_sample_id IS NOT NULL) = (provenance_type = 'measurement_sample')
    AND (measurement_channel_id IS NOT NULL) = (provenance_type = 'measurement_channel')
    AND (measurement_id IS NOT NULL) = (provenance_type = 'measurement')
    AND (event_id IS NOT NULL) = (provenance_type = 'event')
    AND (time_reference_id IS NOT NULL) = (provenance_type = 'time_reference')
    AND (run_id IS NOT NULL) = (provenance_type = 'experimental_run')
    AND (run_composition_id IS NOT NULL) = (provenance_type = 'run_composition')
    AND (droplet_geometry_id IS NOT NULL) = (provenance_type = 'droplet_geometry')
    AND (solid_fuel_geometry_id IS NOT NULL) = (provenance_type = 'solid_fuel_geometry')
    AND (comparability_assessment_id IS NOT NULL) = (provenance_type = 'comparability_assessment')
    AND (experiment_id IS NOT NULL) = (provenance_type = 'experiment')
    AND (source_id IS NOT NULL) = (provenance_type = 'source') | PASS |
| 86 | fail | PASS | IntegrityError: CHECK constraint failed: (CASE WHEN measurement_sample_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN measurement_channel_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN measurement_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN event_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN time_reference_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN run_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN run_composition_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN droplet_geometry_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN solid_fuel_geometry_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN comparability_assessment_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN experiment_id IS NULL THEN 0 ELSE 1 END
       + CASE WHEN source_id IS NULL THEN 0 ELSE 1 END) = 1 | PASS |
| 87 | pass | PASS | all statements executed | PASS |
| 88 | pass | PASS | all statements executed | PASS |
