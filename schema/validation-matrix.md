# Validation Test Matrix — v1.2.0 (promoted from v1.2.0-candidate)

# STATUS: EXECUTED 2026-11-12 (SQLite 3.54.1) - RE-RUN after D-1 fix: 112/112 MATCH

Outcome columns were recorded by `tests/validate_schema_candidate.py` against
`schema/v1.2.0.sql` on SQLite 3.54.1. **Expected** stays the proposed
design expectation; **Observed** is the actual result with the SQLite error that
fired. Rerun of 2026-11-12 after the approved D-1 correction: 112/112 MATCH,
0 MISMATCH. The D-1 section below is retained as the record of the defect and
its (now applied) correction.

## Environment requirements (proposed)

- SQLite >= 3.9.0 (expression index with scalar `min`/`max`).
- JSON1 built in (>= 3.38), otherwise enable the extension.
- `PRAGMA foreign_keys = ON` set **outside** any transaction on every
  connection; it is per-connection and defaults OFF.
- No `PRAGMA defer_foreign_keys` is used anywhere; the insertion contract is
  `experimental_run -> anchor event -> time_reference -> interpreted event`.

## Seed fixtures required before FK tests (proposed)

Valid complete parent records for: `source`, `experiment`, `clock_domain`,
`data_file`, `experimental_run` (`run_1`, `run_2`), anchor event `evt_start`,
`time_reference` (`ref_start` anchored on `evt_start`), interpreted event
`evt_ign`, `measurement`, `measurement_channel`, `extraction_record`,
`comparability_assessment`. The cycle-free temporal seeds are inserted in the
documented order below.

---

## 1. Temporal-anchor sequences (accepted from latest review)

| # | Sequence | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | **Positive, plain order:** insert `run_1`; insert anchor event `evt_start` (`time_reference_id = NULL`); insert `time_reference ref_start` (`reference_kind='event'`, `reference_event_id='evt_start'`); insert interpreted event `evt_ign` (`time_reference_id='ref_start'`, `time_base='run_relative_seconds'`) | All four INSERTs PASS under immediate FKs | PASS | all statements executed | MATCH |
| 2 | **Positive, anchor with a different reference:** `evt_start` already points at unrelated `ref_0`; insert `ref_start` anchored on `evt_start`; insert `evt_ign` using `ref_start` | PASS (triggers (C)/(A) see no self-pair) | PASS | all statements executed | MATCH |
| 3 | **Negative, UPDATE path (reported edge case):** insert `evt` (`time_reference_id = NULL`); insert `ref` (`reference_event_id='evt'`); `UPDATE event SET time_reference_id='ref' WHERE event_id='evt'` | REJECT by `trg_event_no_self_anchor_upd` | PASS | IntegrityError: event must not anchor itself via its time_reference | MATCH |
| 4 | **Negative, INSERT on event:** `INSERT INTO event ... (event_id = ref.reference_event_id, time_reference_id = ref)` | REJECT by `trg_event_no_self_anchor_ins` | PASS | IntegrityError: event must not anchor itself via its time_reference | MATCH |
| 5 | **Negative, UPDATE on time_reference:** with `evt.time_reference_id='ref'`, `UPDATE time_reference SET reference_event_id='evt' WHERE time_reference_id='ref'` | REJECT by `trg_time_reference_no_self_anchor_upd` | PASS | IntegrityError: time_reference must not be anchored on an event that references it | MATCH |
| 6 | **Negative, id collision on event UPDATE:** `UPDATE event SET event_id = ref.reference_event_id WHERE event_id='evt_ign' AND time_reference_id='ref'` | REJECT by `trg_event_no_self_anchor_upd` (NEW row) | PASS | IntegrityError: event must not anchor itself via its time_reference | MATCH |
| 7 | **Negative, missing anchor (immediate FK):** insert `time_reference` whose `reference_event_id` does not exist | REJECT by composite FK (no deferral needed) | PASS | IntegrityError: FOREIGN KEY constraint failed | MATCH |
| 8 | **Negative, cross-run reference:** interpreted event in `run_1` with `time_reference_id` belonging to `run_2` | REJECT by composite FK | PASS | IntegrityError: FOREIGN KEY constraint failed | MATCH |
| 9 | **Negative, INSERT on time_reference with reciprocal event:** event already references the reference id being inserted | REJECT by `trg_time_reference_no_self_anchor_ins` | PASS | IntegrityError: time_reference must not be anchored on an event that references it | MATCH |

## 2. Temporal-reference semantics (retained from previous matrix)

| # | Case | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 10 | `time_reference` kind `event`, same-run `reference_event_id` | PASS | PASS | all statements executed | MATCH |
| 11 | kind `absolute`, `utc`, `2008-04-19T12:00:00Z` | PASS | PASS | all statements executed | MATCH |
| 12 | kind `absolute` with `absolute_time_statement` NULL, or date-only value | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: chk_time_reference_kind ; IntegrityError: CHECK constraint failed: reference_absolute_time IS NULL OR reference_absolute_time GLOB '[0-9][0-9][0-9 | MATCH |
| 13 | kind `numeric`, `2.5` `s`, no clock domain, no offset | PASS | PASS | all statements executed | MATCH |
| 14 | kind `numeric` with unit `kpa`, or NULL unit, or an offset set | REJECT | PASS / PASS / PASS | IntegrityError: CHECK constraint failed: reference_numeric_unit IS NULL OR reference_numeric_unit IN ('s','ms','us','ns' ; IntegrityError: CHECK constraint failed: reference_kind <> 'numeric' OR (reference_numeric_value IS NOT NULL AND referen ; IntegrityError: CHECK constraint failed: reference_kind IN ('event','absolute') OR (reference_offset_s IS NULL AND refer | MATCH |
| 15 | kind `numeric` with `clock_domain_id` set, value `2.5 s` | PASS (domain-interpreted, documented rule) | PASS | all statements executed | MATCH |
| 16 | kind `unknown` with all reference fields NULL and no clock domain | PASS | PASS | all statements executed | MATCH |
| 17 | kind `unknown` with `clock_domain_id` or `reference_numeric_uncertainty` set | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: chk_time_reference_kind ; IntegrityError: CHECK constraint failed: reference_kind = 'numeric' OR (reference_numeric_value IS NULL AND reference_nu | MATCH |
| 18 | kind `event` with `reference_offset_uncertainty_s` but no `reference_offset_s` | REJECT | PASS | IntegrityError: CHECK constraint failed: reference_offset_uncertainty_s IS NULL OR reference_offset_s IS NOT NULL | MATCH |
| 19 | kind `event` with offset `-1.5` and uncertainty `0.2` | PASS | PASS | all statements executed | MATCH |
| 20 | `measurement` with `normalizes_run_timeline=1` but foreign-run `time_reference_id` | REJECT | PASS | IntegrityError: FOREIGN KEY constraint failed | MATCH |

## 3. Event time-base integrity

| # | Case | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 21 | `time_base='frame_index'`, `event_frame_start=4821` | PASS | PASS | all statements executed | MATCH |
| 22 | `time_base='frame_index'`, `event_frame_start=-1` | REJECT (>= 0) | PASS | IntegrityError: CHECK constraint failed: event_frame_start IS NULL OR event_frame_start >= 0 | MATCH |
| 23 | `time_base='run_relative_seconds'` with `event_frame_end=900` | REJECT (cross-base end) | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | MATCH |
| 24 | absolute datetime base with `event_relative_start_s` also set | REJECT (mixed bases) | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | MATCH |
| 25 | `event_datetime_end` set with `event_datetime_start` NULL | REJECT | PASS | IntegrityError: CHECK constraint failed: event_datetime_end IS NULL OR event_datetime_start IS NOT NULL | MATCH |
| 26 | `time_base='unknown'` with `clock_domain_id` set | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | MATCH |
| 27 | `time_base='clock_domain_time'` without `clock_domain_id` | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_event_time_base | MATCH |
| 28 | `event_time_original` preserved verbatim alongside any base | PASS | PASS | all statements executed | MATCH |

## 4. measurement_sample timestamps (retained + corrected)

| # | Case | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 29 | ISO 8601 string, status `parsed`, `original_timestamp_parsed=NULL`, `timestamp_epoch_utc` set | PASS | PASS | all statements executed | MATCH |
| 30 | status `parsed`, `original_timestamp_parsed=NULL`, non-ISO representation | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_sample_timestamp_consistency | MATCH |
| 31 | Excel serial `44561.5`, status `ambiguous`, `original_timestamp_parsed=44561.5`, `timestamp_epoch_utc=NULL` | PASS | PASS | all statements executed | MATCH |
| 32 | status `ambiguous` with `timestamp_epoch_utc` populated | REJECT | PASS | IntegrityError: CHECK constraint failed: timestamp_epoch_utc IS NULL OR (timestamp_parsing_status = 'parsed' AND timesta | MATCH |
| 33 | Excel serial parsed with `timestamp_epoch_utc` set | PASS | PASS | all statements executed | MATCH |
| 34 | `timestamp_representation='run_relative_seconds'` with `timestamp_epoch_utc` set | REJECT (conservative policy) | PASS | IntegrityError: CHECK constraint failed: timestamp_epoch_utc IS NULL OR (timestamp_parsing_status = 'parsed' AND timesta | MATCH |
| 35 | `timestamp_epoch_utc=-1e10` | REJECT (domain window 1900-2100) | PASS | IntegrityError: CHECK constraint failed: timestamp_epoch_utc IS NULL OR (timestamp_epoch_utc >= -2208988800 AND timestam | MATCH |
| 36 | `original_timestamp_parsed=-1e10` (source-native) | PASS (no epoch bound) | PASS | all statements executed | MATCH |
| 37 | raw string `'???'`, `unknown_representation`, status `unknown`, parsed/epoch NULL | PASS | PASS | all statements executed | MATCH |
| 38 | status `unknown`, representation NOT `unknown_representation`, `original_timestamp` NULL | PASS (genuinely missing) | PASS | all statements executed | MATCH |
| 39 | `unknown_representation` with status `parsed` | REJECT | PASS | IntegrityError: CHECK constraint failed: (timestamp_representation = 'unknown_representation' AND timestamp_parsing_stat | MATCH |
| 40 | duplicate identical `original_timestamp`, `sample_index` 7 and 8, same channel | PASS (identity is channel+index) | PASS | all statements executed | MATCH |

## 5. measurement_sample values (retained)

| # | Case | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 41 | qualitative `'soot cloud present'`, `valid_qualitative` | PASS | PASS | all statements executed | MATCH |
| 42 | `valid_qualitative` with representation `float` | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | MATCH |
| 43 | coded `'3'` with `coded_value_system`, `valid_coded`, representation `coded` | PASS | PASS | all statements executed | MATCH |
| 44 | `valid_coded` with representation `integer` or without `coded_value_system` | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency ; IntegrityError: CHECK constraint failed: chk_sample_value_consistency | MATCH |
| 45 | `valid_numeric` with representation `qualitative` or `original_value_parsed` NULL | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency ; IntegrityError: CHECK constraint failed: chk_sample_value_consistency | MATCH |
| 46 | `missing` with `original_value='7.2'` | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | MATCH |
| 47 | `invalid` with `quality_flag='ok'` | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency | MATCH |
| 48 | `outlier` with `quality_flag='outlier'` and parsed value | PASS | PASS | all statements executed | MATCH |
| 49 | `above_saturation_limit` without `detection_limit_value`; `below_detection_limit` without unit | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: chk_sample_value_consistency ; IntegrityError: CHECK constraint failed: detection_limit_value IS NULL OR detection_limit_unit IS NOT NULL | MATCH |
| 50 | `below_detection_limit` with value + unit + original value | PASS | PASS | all statements executed | MATCH |
| 51 | `normalized_value` set without `normalization_method`/`normalized_unit` | REJECT | PASS | IntegrityError: CHECK constraint failed: chk_sample_normalization_traceability | MATCH |
| 52 | `normalized_value` with method + unit | PASS | PASS | all statements executed | MATCH |
| 53 | `quality_flag` with a value outside the enum (e.g. `'bogus'`) | REJECT | PASS | IntegrityError: CHECK constraint failed: quality_flag IS NULL OR quality_flag IN ( 'ok','saturated','outlier','contamina | MATCH |

## 6. Run conditions, composition, geometry (retained)

| # | Case | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 54 | `experimental_run` pressure interval set with `pressure_unit` NULL | REJECT | PASS | IntegrityError: CHECK constraint failed: ( pressure IS NULL AND pressure_uncertainty IS NULL AND pressure_interval_low I | MATCH |
| 55 | `pressure_uncertainty` set without any pressure value or unit | REJECT | PASS | IntegrityError: CHECK constraint failed: ( pressure IS NULL AND pressure_uncertainty IS NULL AND pressure_interval_low I | MATCH |
| 56 | temperature/flow `*_uncertainty` set without the value + unit | REJECT | PASS / PASS / PASS | IntegrityError: CHECK constraint failed: temperature_uncertainty IS NULL OR (temperature IS NOT NULL AND temperature_uni ; IntegrityError: CHECK constraint failed: flow_velocity_uncertainty IS NULL OR (flow_velocity IS NOT NULL AND flow_veloci ; IntegrityError: CHECK constraint failed: temperature IS NULL OR temperature_unit IS NOT NULL | MATCH |
| 57 | gravity `0.15` with uncertainty `0.9` (uncertainty > value) | PASS (constraint removed) | PASS | all statements executed | MATCH |
| 58 | `run_composition` fraction uncertainty or approx flag without the fraction | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: mole_fraction_uncertainty IS NULL OR mole_fraction IS NOT NULL ; IntegrityError: CHECK constraint failed: mole_fraction_approx = 0 OR mole_fraction IS NOT NULL | MATCH |
| 59 | `run_composition` same species with `fuel` and `oxidizer` roles | PASS | PASS | all statements executed | MATCH |
| 60 | `solid_fuel_geometry` width set with `width_unit` NULL | REJECT | PASS | IntegrityError: CHECK constraint failed: width IS NULL OR width_unit IS NOT NULL | MATCH |
| 61 | `solid_fuel_geometry` width/length/thickness uncertainty without the value | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: width_uncertainty IS NULL OR width IS NOT NULL ; IntegrityError: CHECK constraint failed: thickness_uncertainty IS NULL OR thickness IS NOT NULL | MATCH |
| 62 | `droplet_geometry` `support_fiber=0` with `fiber_diameter` set | REJECT | PASS | IntegrityError: CHECK constraint failed: support_fiber = 1 OR fiber_diameter IS NULL | MATCH |
| 63 | `droplet_geometry` `support_fiber=1`, `fiber_diameter` set, `fiber_diameter_unit` NULL | REJECT | PASS | IntegrityError: CHECK constraint failed: fiber_diameter IS NULL OR fiber_diameter_unit IS NOT NULL | MATCH |
| 64 | `droplet_geometry` `initial_diameter_uncertainty` / `fiber_diameter_uncertainty` without the value | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: initial_diameter_uncertainty IS NULL OR initial_diameter IS NOT NULL ; IntegrityError: CHECK constraint failed: fiber_diameter_uncertainty IS NULL OR fiber_diameter IS NOT NULL | MATCH |
| 65 | droplet + solid-fuel rows for the same run | REJECT only if optional exclusivity triggers are installed; PASS otherwise (documented) | PASS | IntegrityError: run already has droplet_geometry | MATCH |

## 7. clock_sync, files, provenance, comparability (retained)

| # | Case | Expected (proposed) | Observed (executed) | Observed detail (SQLite error / outcome) | Result |
| --- | --- | --- | --- | --- | --- |
| 66 | two segments (0 and 1) for the same domain pair | PASS | PASS | all statements executed | MATCH |
| 67 | duplicate `sync_segment_id=0` for the same domain pair | REJECT | PASS | IntegrityError: UNIQUE constraint failed: clock_sync.run_id, clock_sync.source_domain_id, clock_sync.target_domain_id, c | MATCH |
| 68 | two distinct segments with NULL `valid_from`/`valid_to` | PASS (only duplicate segment ids rejected) | PASS | all statements executed | MATCH |
| 69 | `sync_status='unknown'` with an offset; `'established'` without method; `'invalidated'` without notes; source == target domain | REJECT | PASS / PASS / PASS / PASS | IntegrityError: CHECK constraint failed: sync_status <> 'unknown' OR (offset_seconds IS NULL AND sync_method IS NULL) ; IntegrityError: CHECK constraint failed: sync_status <> 'established' OR (offset_seconds IS NOT NULL AND sync_method IS  ; IntegrityError: CHECK constraint failed: sync_status <> 'invalidated' OR notes IS NOT NULL ; IntegrityError: CHECK constraint failed: source_domain_id <> target_domain_id | MATCH |
| 70 | `valid_to` earlier than `valid_from` | REJECT | PASS | IntegrityError: CHECK constraint failed: valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to | MATCH |
| 71 | `measurement_channel` `sampling_interval_s=33.3` | PASS (seconds standard) | PASS | all statements executed | MATCH |
| 72 | `conversion_offset` without `conversion_scale`; `conversion_scale=0` | REJECT | PASS / PASS | IntegrityError: CHECK constraint failed: conversion_offset IS NULL OR conversion_scale IS NOT NULL ; IntegrityError: CHECK constraint failed: conversion_scale IS NULL OR conversion_scale <> 0 | MATCH |
| 73 | `conversion_scale=-1.7` (negative calibration slope) | PASS | PASS | all statements executed | MATCH |
| 74 | `data_file` duplicate SHA-256, different `relative_path` | PASS (integrity != identity) | PASS | all statements executed | MATCH |
| 75 | `data_file` SHA-256 not 64 lowercase hex | REJECT | PASS | IntegrityError: CHECK constraint failed: length(sha256_checksum) = 64 AND lower(sha256_checksum) = sha256_checksum AND s | MATCH |
| 76 | `is_archive=0` with `archive_member_count=5` | REJECT | PASS | IntegrityError: CHECK constraint failed: is_archive = 1 OR archive_member_count IS NULL | MATCH |
| 77 | `is_archive=1` with `archive_member_count=NULL` (not yet inspected) | PASS (unknown != zero) | PASS | all statements executed | MATCH |
| 78 | `source.authors` `["A. Smith","B. Jones"]` | PASS | PASS | all statements executed | MATCH |
| 79 | `source.authors` `["A",{"x":1}]`, `[null]`, `[1]`, `[true]`, `[["n"]]` | REJECT (trigger) | PASS / PASS / PASS / PASS / PASS | IntegrityError: source.authors must be a JSON array of strings ; IntegrityError: source.authors must be a JSON array of strings ; IntegrityError: source.authors must be a JSON array of strings ; IntegrityError: source.authors must be a JSON array of strings ; IntegrityError: source.authors must be a JSON array of strings | MATCH |
| 80 | malformed JSON in `source.authors` | REJECT (array CASE) | PASS | OperationalError: malformed JSON | MATCH |
| 81 | `extraction_record.data_file_id` referencing an existing / missing `data_file` | PASS / REJECT | PASS / PASS | all statements executed ; IntegrityError: FOREIGN KEY constraint failed | MATCH |
| 82 | `comparability_assessment` (A,B,subject) then (B,A,subject) | REJECT (expression index — verify on the actual build) | PASS | IntegrityError: UNIQUE constraint failed: index 'ux_comparability_unordered_pair' | MATCH |
| 83 | `not_comparable` without notes; `comparable_after_normalization` without notes; numeric values without `comparison_unit`; `review_status='reviewed'` without `reviewed_by` | REJECT | PASS / PASS / PASS / PASS | IntegrityError: CHECK constraint failed: chk_comparability_classification ; IntegrityError: CHECK constraint failed: chk_comparability_classification ; IntegrityError: CHECK constraint failed: (run1_value_numeric IS NULL AND run2_value_numeric IS NULL) OR comparison_unit  ; IntegrityError: CHECK constraint failed: review_status = 'pending_expert_review' OR reviewed_by IS NOT NULL | MATCH |
| 84 | `qualitatively_comparable` with both text values | PASS | PASS | all statements executed | MATCH |
| 85 | `value_provenance` type/column mismatch (e.g. type `run_composition` with `measurement_id` set) | REJECT | PASS | IntegrityError: CHECK constraint failed: (measurement_sample_id IS NOT NULL) = (provenance_type = 'measurement_sample')  | MATCH |
| 86 | `value_provenance` with two target columns populated | REJECT | PASS | IntegrityError: CHECK constraint failed: (CASE WHEN measurement_sample_id IS NULL THEN 0 ELSE 1 END + CASE WHEN measurem | MATCH |
| 87 | `value_provenance` with `curation_target_run_id` disagreeing with the target's run | PASS at DB level; flagged for curation (application-level rule) | PASS | all statements executed | MATCH |
| 88 | `source_experiment` one experiment cited by two sources | PASS | PASS | all statements executed | MATCH |

## 8. FLEX-specific coverage retained

Partial gravity (#57), Excel serials (#31, #33), repeated timestamps (#40),
unknown-format raw timestamps (#37), partial-gravity onset/offset events with
mixed reported bases (#23, #24), multi-segment clock syncs (#66-#68),
qualitative image-viewer comments (#41), coded smoke/soot classifications
(#43), reversed comparability duplicates (#82), uninspected archives (#77).

## Remaining design notes

- Tests must be executed with `PRAGMA foreign_keys = ON` outside each
  transaction and the SQLite version recorded.
- Tests 2, 9 and 13 are defensive paths that immediate FK enforcement already
  blocks in normal use; they verify the guards hold even in unusual states.
- Cross-run/cross-source provenance agreement (test 87) and clock-sync interval
  overlap are intentionally application-level and cannot be fully expressed as
  schema constraints.
- The schema is a data-integrity foundation: it preserves measurements,
  evidence, and uncertainty but cannot itself establish that a flame has
  chemically extinguished; that interpretation depends on the diagnostics.

## D-1 Schema defect (FOUND then FIXED - correction approved and applied)

First run (2026-11-12): test 83c - `comparability_assessment` with
`run1_value_numeric=1.0`, `run2_value_numeric=2.0`, `comparison_unit=NULL`,
classification `insufficient_information` was **ACCEPTED**, although the
documented rule requires a unit whenever numeric values are present. The CHECK
enforced only the converse direction (`comparison_unit IS NOT NULL` implies both
numeric values are present).

Correction applied to `schema/v1.2.0.sql` (the only change):

```sql
-- before
CHECK (comparison_unit IS NULL
       OR (run1_value_numeric IS NOT NULL AND run2_value_numeric IS NOT NULL)),
-- after
CHECK ((run1_value_numeric IS NULL AND run2_value_numeric IS NULL)
       OR comparison_unit IS NOT NULL),
```

Re-run after the fix: test 83c is now REJECTED by the corrected CHECK
(`CHECK constraint failed: (run1_value_numeric IS NULL AND run2_value_numeric IS NULL)...`).
Text-only `qualitatively_comparable`, numeric+unit+notes, and no-value
`insufficient_information` all remain accepted; no other case changed outcome.

## Harness execution record

- Harness: `tests/validate_schema_candidate.py` (`python3 tests/validate_schema_candidate.py`)
- SQLite: 3.54.1 (CLI and Python `sqlite3` module)
- Structural checks: 20/20 tables, 8/8 triggers, expression index present,
  `PRAGMA foreign_key_check` = no violations, `PRAGMA integrity_check` = `ok`,
  JSON1 available
- Run 1 (2026-11-12, pre-fix): 112 cases, 111 PASS, 1 FAIL (D-1), 0 BLOCKED.
- Run 2 (2026-11-12, post-fix D-1): 112 cases, 112 PASS, 0 FAIL, 0 BLOCKED.
- Each case ran in a fresh in-memory database with the documented fixture order;
  after expected-failure cases the database was re-checked with `integrity_check`,
  `foreign_key_check`, and a usability probe.
- Tests 4, 6, 9 are defensive guards unreachable under immediate FK enforcement;
  they were executed with `PRAGMA foreign_keys = OFF` applied after DDL load
  (the DDL file's own pragma re-enables FK enforcement on the loading connection).
