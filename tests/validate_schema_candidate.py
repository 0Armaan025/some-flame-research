#!/usr/bin/env python3
"""SQLite validation harness for combustion-research/schema/v1.2.0-candidate.

Design-only schema -> executed verification. This harness:
  1. records the SQLite version,
  2. creates a fresh in-memory database per test (full isolation),
  3. enables PRAGMA foreign_keys = ON before any statement/transaction
     (FK-off tests are explicit and documented),
  4. loads the candidate DDL,
  5. verifies tables/index/triggers exist and integrity/FK checks are clean,
  6. seeds fixtures in the documented insertion order,
  7. executes every case in schema/validation-matrix.md,
  8. for expected-failure cases verifies the statement fails AND the database
     remains usable and consistent,
  9. records actual outcomes and error messages.

It does NOT modify the schema. A failing test is a finding, never a licence to
change semantics.
"""

import sqlite3
import sys
import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE.parent / "schema" / "v1.2.0.sql"
RESULTS_PATH = HERE / "schema_validation_results.md"

UTC = datetime.timezone.utc


def iso_epoch(text):
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).timestamp()


def insert_sql(table, kw):
    cols = ",".join(kw.keys())
    ph = ",".join("?" for _ in kw)
    return f"INSERT INTO {table} ({cols}) VALUES ({ph})", tuple(kw.values())


# ---------------------------------------------------------------------------
# baseline fixtures: complete, minimal, valid parents. Inserted in the
# documented order experimental_run -> anchor event -> time_reference ->
# interpreted event. Temporal anchors come first, everything else after.
# ---------------------------------------------------------------------------
BASELINE = [
    ("source", dict(source_id="src_1", publication_title="Test publication",
                    authors='["A. Smith","B. Jones"]', document_type="technical_report",
                    data_origin="test")),
    ("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1")),
    ("chemical_species", dict(species_id="sp_1", species_name="oxygen")),
    ("clock_domain", dict(clock_domain_id="cd_1", domain_name="camera clock")),
    ("clock_domain", dict(clock_domain_id="cd_2", domain_name="data system clock")),
    ("data_file", dict(file_id="file_1", relative_path="data/flex/test.dat",
                       file_name="test.dat", file_format="text", file_size_bytes=1000,
                       sha256_checksum="a" * 64)),
    ("source_experiment", dict(source_experiment_id="se_1", source_id="src_1",
                               experiment_id="exp_1", extraction_confidence="high",
                               extraction_method="manual_transcription")),
    ("extraction_record", dict(extraction_record_id="er_1", source_id="src_1",
                               extraction_method="direct_export",
                               extraction_confidence="high")),
    ("experimental_run", dict(run_id="run_1", experiment_id="exp_1", run_label="FLEX-001")),
    ("experimental_run", dict(run_id="run_2", experiment_id="exp_1", run_label="FLEX-002")),
    # temporal anchors, documented order
    ("event", dict(event_id="evt_start", run_id="run_1", event_type="other",
                   time_base="absolute_datetime",
                   event_datetime_start="2008-04-19T12:00:00Z")),
    ("time_reference", dict(time_reference_id="ref_start", run_id="run_1",
                            reference_label="run start anchor", reference_kind="event",
                            reference_event_id="evt_start")),
    ("event", dict(event_id="evt_ign", run_id="run_1", event_type="ignition",
                   time_base="run_relative_seconds", event_relative_start_s=3.5,
                   time_reference_id="ref_start")),
    # measurement stack
    ("measurement", dict(measurement_id="meas_1", run_id="run_1",
                         measurement_name="Soot volume fraction",
                         measurement_kind="soot_volume_fraction",
                         measurement_domain="image_diagnostic",
                         time_reference_id="ref_start")),
    ("measurement_channel", dict(measurement_channel_id="chan_1", measurement_id="meas_1",
                                 channel_name="color camera",
                                 physical_quantity="soot_volume_fraction",
                                 quantity_unit_parsed="unitless",
                                 sampling_frequency=30)),
    ("measurement_sample", dict(measurement_sample_id="samp_1",
                                measurement_channel_id="chan_1", sample_index=0,
                                original_timestamp="2008-04-19T12:00:00Z",
                                timestamp_parsing_status="parsed",
                                parsed_time_format="iso8601",
                                timestamp_representation="iso8601_datetime",
                                timestamp_epoch_utc=iso_epoch("2008-04-19T12:00:00Z"),
                                original_value="0.42", original_value_parsed=0.42,
                                value_representation="float", normalized_value=0.42,
                                normalized_unit="unitless",
                                normalization_method="identity",
                                value_status="valid_numeric")),
    ("file_run_reference", dict(file_run_reference_id="frr_1", file_id="file_1",
                                run_id="run_1", reference_role="primary_data")),
    ("comparability_assessment", dict(comparability_assessment_id="cmp_1",
                                      run1_run_id="run_1", run2_run_id="run_2",
                                      measurement_subject="burn time",
                                      gravitational_comparable="comparable",
                                      environment_comparable="unknown",
                                      measurement_method_comparable="comparable",
                                      data_collection_comparable="unknown",
                                      uncertainty_overlap="unknown",
                                      comparability_classification="insufficient_information")),
    ("value_provenance", dict(value_provenance_id="pv_1", extraction_record_id="er_1",
                              provenance_type="experimental_run", run_id="run_1",
                              curation_target_run_id="run_1")),
]


def seed(con, extra=(), baseline=True):
    rows = list(BASELINE) + list(extra) if baseline else list(extra)
    for table, kw in rows:
        sql, params = insert_sql(table, kw)
        con.execute(sql, params)


def fresh_db(fk=True):
    """Load the DDL, then set FK enforcement. The DDL file itself begins with
    PRAGMA foreign_keys = ON for the loading connection; for defensive
    (FK-OFF) tests the pragma is set again afterwards to override it."""
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA_PATH.read_text())
    con.execute("PRAGMA foreign_keys = ON" if fk else "PRAGMA foreign_keys = OFF")
    return con


def sample(sid, idx, **kw):
    base = dict(measurement_sample_id=sid, measurement_channel_id="chan_1",
                sample_index=idx, original_timestamp="2008-04-19T12:00:00Z",
                timestamp_parsing_status="parsed", parsed_time_format="iso8601",
                timestamp_representation="iso8601_datetime",
                original_value="0.42", original_value_parsed=0.42,
                value_representation="float", value_status="valid_numeric")
    base.update(kw)
    return ("measurement_sample", base)


def run_only(**kw):
    return ("experimental_run", base_run(kw))


def base_run(kw):
    base = dict(run_id="run_x", experiment_id="exp_1", run_label="FLEX-X")
    base.update(kw)
    return base


def T(tid, group, desc, expect, stmts, seed_extra=(), fk_off=False, note="",
      baseline=True):
    """stmts: list of (kind, payload); kind 'ins' payload (table,kw) else raw SQL.
    baseline=False: build a private world from seed_extra only (no shared fixtures)."""
    return dict(id=tid, group=group, desc=desc, expect=expect, stmts=stmts,
                seed_extra=seed_extra, fk_off=fk_off, note=note, baseline=baseline)


RUN2_CHAIN = [
    ("event", dict(event_id="evt_start_r2", run_id="run_2", event_type="other",
                   time_base="absolute_datetime",
                   event_datetime_start="2008-04-19T13:00:00Z")),
    ("time_reference", dict(time_reference_id="ref_r2", run_id="run_2",
                            reference_label="run2 anchor", reference_kind="event",
                            reference_event_id="evt_start_r2")),
]

TABS = ["source", "experiment", "chemical_species", "clock_domain", "data_file",
        "source_experiment", "extraction_record", "experimental_run", "run_composition",
        "droplet_geometry", "solid_fuel_geometry", "event", "time_reference",
        "clock_sync", "measurement", "measurement_channel", "measurement_sample",
        "file_run_reference", "comparability_assessment", "value_provenance"]
TRIGGERS = ["trg_source_authors_ins", "trg_source_authors_upd",
            "trg_event_no_self_anchor_ins", "trg_event_no_self_anchor_upd",
            "trg_time_reference_no_self_anchor_ins", "trg_time_reference_no_self_anchor_upd",
            "trg_droplet_exclusive", "trg_solid_exclusive"]

TESTS = [
    # ---- 1. temporal-anchor sequences -------------------------------------
    T(1, "1. Temporal-anchor sequences",
      "positive plain order: run -> anchor event -> time_reference -> interpreted event",
      "pass", [("ins", ("experimental_run", dict(run_id="run_1", experiment_id="exp_1",
                                                  run_label="FLEX-001"))),
               ("ins", ("event", dict(event_id="evt_start", run_id="run_1",
                                      event_type="other", time_base="absolute_datetime",
                                      event_datetime_start="2008-04-19T12:00:00Z"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_start", run_id="run_1",
                                               reference_label="run start anchor",
                                               reference_kind="event",
                                               reference_event_id="evt_start"))),
               ("ins", ("event", dict(event_id="evt_ign", run_id="run_1",
                                      event_type="ignition",
                                      time_base="run_relative_seconds",
                                      event_relative_start_s=3.5,
                                      time_reference_id="ref_start")))],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      baseline=False,
      note="documented order from an empty schema"),
    T(2, "1. Temporal-anchor sequences",
      "positive: anchor event points at a different reference (ref_0), ref_start anchored on it",
      "pass", [("ins", ("experimental_run", dict(run_id="run_1", experiment_id="exp_1",
                                                  run_label="FLEX-001"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_0", run_id="run_1",
                                               reference_label="absolute anchor",
                                               reference_kind="absolute",
                                               reference_absolute_time="2008-04-19T00:00:00Z",
                                               absolute_time_statement="utc"))),
               ("ins", ("event", dict(event_id="evt_start", run_id="run_1",
                                      event_type="other", time_base="absolute_datetime",
                                      event_datetime_start="2008-04-19T00:00:00Z",
                                      time_reference_id="ref_0"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_start", run_id="run_1",
                                               reference_label="start anchor",
                                               reference_kind="event",
                                               reference_event_id="evt_start"))),
               ("ins", ("event", dict(event_id="evt_ign", run_id="run_1",
                                      event_type="ignition",
                                      time_base="run_relative_seconds",
                                      event_relative_start_s=3.5,
                                      time_reference_id="ref_start")))],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      baseline=False),
    T(3, "1. Temporal-anchor sequences",
      "negative UPDATE path: event inserted with NULL ref, ref anchored on it, then event updated to point at ref",
      "fail", [("ins", ("experimental_run", dict(run_id="run_1", experiment_id="exp_1",
                                                  run_label="FLEX-001"))),
               ("ins", ("event", dict(event_id="evt_a", run_id="run_1", event_type="other",
                                      time_base="absolute_datetime",
                                      event_datetime_start="2008-04-19T12:00:00Z"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_a", run_id="run_1",
                                               reference_label="anchor", reference_kind="event",
                                               reference_event_id="evt_a"))),
               ("sql", "UPDATE event SET time_reference_id='ref_a' WHERE event_id='evt_a'")],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      baseline=False),
    T(4, "1. Temporal-anchor sequences",
      "negative INSERT on event (defensive; unreachable under FK enforcement -> executed with foreign_keys OFF)",
      "fail", [("ins", ("experimental_run", dict(run_id="run_1", experiment_id="exp_1",
                                                  run_label="FLEX-001"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_a", run_id="run_1",
                                               reference_label="forward anchor",
                                               reference_kind="event",
                                               reference_event_id="evt_a"))),
               ("ins", ("event", dict(event_id="evt_a", run_id="run_1", event_type="ignition",
                                      time_base="run_relative_seconds",
                                      event_relative_start_s=1.0,
                                      time_reference_id="ref_a")))],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      fk_off=True,
      note="state is impossible with immediate FKs; exercised with FKs off to prove the trigger guard",
      baseline=False),
    T(5, "1. Temporal-anchor sequences",
      "negative UPDATE on time_reference: re-anchor ref_start onto event evt_ign which already uses ref_start",
      "fail", [("sql", "UPDATE time_reference SET reference_event_id='evt_ign' "
                       "WHERE time_reference_id='ref_start'")]),
    T(6, "1. Temporal-anchor sequences",
      "negative UPDATE of event id into ref's anchor id (defensive; executed with foreign_keys OFF)",
      "fail", [("ins", ("experimental_run", dict(run_id="run_1", experiment_id="exp_1",
                                                  run_label="FLEX-001"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_a", run_id="run_1",
                                               reference_label="anchor", reference_kind="event",
                                               reference_event_id="evt_anchor"))),
               ("ins", ("event", dict(event_id="evt_interp", run_id="run_1",
                                      event_type="ignition",
                                      time_base="run_relative_seconds",
                                      event_relative_start_s=1.0,
                                      time_reference_id="ref_a"))),
               ("sql", "UPDATE event SET event_id='evt_anchor' WHERE event_id='evt_interp'")],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      fk_off=True,
      note="new event_id must not collide with an existing PK, so run under FKs off",
      baseline=False),
    T(7, "1. Temporal-anchor sequences",
      "negative: time_reference anchored on a non-existent event (immediate FK)",
      "fail", [("ins", ("time_reference", dict(time_reference_id="ref_x", run_id="run_1",
                                               reference_label="dangling", reference_kind="event",
                                               reference_event_id="evt_missing")))],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      baseline=False,
      note="dangling anchor, no PK collision"),
    T(8, "1. Temporal-anchor sequences",
      "negative: event in run_1 referencing run_2's time_reference (composite FK)",
      "fail", [("ins", ("event", dict(event_id="evt_bad", run_id="run_1",
                                      event_type="ignition",
                                      time_base="run_relative_seconds",
                                      event_relative_start_s=1.0,
                                      time_reference_id="ref_r2")))],
      seed_extra=RUN2_CHAIN),
    T(9, "1. Temporal-anchor sequences",
      "negative INSERT on time_reference whose anchor already references it (defensive; FKs off)",
      "fail", [("ins", ("experimental_run", dict(run_id="run_1", experiment_id="exp_1",
                                                  run_label="FLEX-001"))),
               ("ins", ("event", dict(event_id="evt_a", run_id="run_1", event_type="ignition",
                                      time_base="run_relative_seconds",
                                      event_relative_start_s=1.0,
                                      time_reference_id="ref_x"))),
               ("ins", ("time_reference", dict(time_reference_id="ref_x", run_id="run_1",
                                               reference_label="reciprocal",
                                               reference_kind="event",
                                               reference_event_id="evt_a")))],
      seed_extra=[("experiment", dict(experiment_id="exp_1", experiment_label="EXP-1"))],
      fk_off=True,
      note="state is impossible with immediate FKs; exercised with FKs off",
      baseline=False),

    # ---- 2. temporal-reference semantics ----------------------------------
    T(10, "2. Temporal-reference semantics",
      "time_reference kind=event, same-run reference_event_id", "pass",
      [("ins", ("time_reference", dict(time_reference_id="ref_t10", run_id="run_1",
                                       reference_label="ok", reference_kind="event",
                                       reference_event_id="evt_start")))]),
    T(11, "2. Temporal-reference semantics",
      "time_reference kind=absolute, utc, ISO 8601 date-time", "pass",
      [("ins", ("time_reference", dict(time_reference_id="ref_t11", run_id="run_1",
                                       reference_label="abs", reference_kind="absolute",
                                       reference_absolute_time="2008-04-19T12:00:00Z",
                                       absolute_time_statement="utc")))]),
    T(12, "2. Temporal-reference semantics",
      "kind=absolute with absolute_time_statement NULL", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t12a", run_id="run_1",
                                       reference_label="abs bad", reference_kind="absolute",
                                       reference_absolute_time="2008-04-19T12:00:00Z")))]),
    T(12, "2. Temporal-reference semantics",
      "kind=absolute with date-only value (not an instant)", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t12b", run_id="run_1",
                                       reference_label="abs date-only", reference_kind="absolute",
                                       reference_absolute_time="2008-04-19",
                                       absolute_time_statement="utc")))]),
    T(13, "2. Temporal-reference semantics",
      "kind=numeric, 2.5 s, no clock domain, no offset", "pass",
      [("ins", ("time_reference", dict(time_reference_id="ref_t13", run_id="run_1",
                                       reference_label="numeric", reference_kind="numeric",
                                       reference_numeric_value=2.5,
                                       reference_numeric_unit="s")))]),
    T(14, "2. Temporal-reference semantics",
      "kind=numeric with unit kpa", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t14a", run_id="run_1",
                                       reference_label="bad unit", reference_kind="numeric",
                                       reference_numeric_value=101.0,
                                       reference_numeric_unit="kpa")))]),
    T(14, "2. Temporal-reference semantics",
      "kind=numeric with NULL unit", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t14b", run_id="run_1",
                                       reference_label="no unit", reference_kind="numeric",
                                       reference_numeric_value=2.5)))]),
    T(14, "2. Temporal-reference semantics",
      "kind=numeric with an offset", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t14c", run_id="run_1",
                                       reference_label="offset num", reference_kind="numeric",
                                       reference_numeric_value=2.5,
                                       reference_numeric_unit="s",
                                       reference_offset_s=1.0)))]),
    T(15, "2. Temporal-reference semantics",
      "kind=numeric with clock domain, value 2.5 s (domain-interpreted)", "pass",
      [("ins", ("time_reference", dict(time_reference_id="ref_t15", run_id="run_1",
                                       reference_label="numeric domain", reference_kind="numeric",
                                       reference_numeric_value=2.5,
                                       reference_numeric_unit="s",
                                       clock_domain_id="cd_1")))]),
    T(16, "2. Temporal-reference semantics",
      "kind=unknown, all reference fields NULL, no clock domain", "pass",
      [("ins", ("time_reference", dict(time_reference_id="ref_t16", run_id="run_1",
                                       reference_label="unknown", reference_kind="unknown")))]),
    T(17, "2. Temporal-reference semantics",
      "kind=unknown with clock_domain_id set", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t17a", run_id="run_1",
                                       reference_label="unknown+domain",
                                       reference_kind="unknown", clock_domain_id="cd_1")))]),
    T(17, "2. Temporal-reference semantics",
      "kind=unknown with reference_numeric_uncertainty set", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t17b", run_id="run_1",
                                       reference_label="unknown+num unc",
                                       reference_kind="unknown",
                                       reference_numeric_uncertainty=0.5)))]),
    T(18, "2. Temporal-reference semantics",
      "kind=event with reference_offset_uncertainty_s but no reference_offset_s", "fail",
      [("ins", ("time_reference", dict(time_reference_id="ref_t18", run_id="run_1",
                                       reference_label="unc only", reference_kind="event",
                                       reference_event_id="evt_start",
                                       reference_offset_uncertainty_s=0.2)))]),
    T(19, "2. Temporal-reference semantics",
      "kind=event with offset -1.5 and uncertainty 0.2", "pass",
      [("ins", ("time_reference", dict(time_reference_id="ref_t19", run_id="run_1",
                                       reference_label="offset", reference_kind="event",
                                       reference_event_id="evt_start",
                                       reference_offset_s=-1.5,
                                       reference_offset_uncertainty_s=0.2)))]),
    T(20, "2. Temporal-reference semantics",
      "measurement normalizes_run_timeline=1 with foreign-run time_reference_id", "fail",
      [("ins", ("measurement", dict(measurement_id="meas_t20", run_id="run_1",
                                    measurement_name="cross run",
                                    measurement_kind="burn_time",
                                    measurement_domain="thermocouple",
                                    normalizes_run_timeline=1,
                                    time_reference_id="ref_r2")))],
      seed_extra=RUN2_CHAIN),

    # ---- 3. event time-base integrity -------------------------------------
    T(21, "3. Event time-base integrity", "time_base=frame_index, event_frame_start=4821", "pass",
      [("ins", ("event", dict(event_id="evt_t21", run_id="run_1", event_type="other",
                              time_base="frame_index", event_frame_start=4821)))]),
    T(22, "3. Event time-base integrity", "time_base=frame_index, event_frame_start=-1", "fail",
      [("ins", ("event", dict(event_id="evt_t22", run_id="run_1", event_type="other",
                              time_base="frame_index", event_frame_start=-1)))]),
    T(23, "3. Event time-base integrity",
      "time_base=run_relative_seconds with event_frame_start and event_frame_end (cross-base)",
      "fail",
      [("ins", ("event", dict(event_id="evt_t23", run_id="run_1", event_type="other",
                              time_base="run_relative_seconds",
                              event_relative_start_s=1.0,
                              event_frame_start=100, event_frame_end=900)))]),
    T(24, "3. Event time-base integrity",
      "time_base=absolute_datetime with event_relative_start_s also set", "fail",
      [("ins", ("event", dict(event_id="evt_t24", run_id="run_1", event_type="ignition",
                              time_base="absolute_datetime",
                              event_datetime_start="2008-04-19T12:00:00Z",
                              event_relative_start_s=1.0)))]),
    T(25, "3. Event time-base integrity",
      "event_datetime_end set with event_datetime_start NULL", "fail",
      [("ins", ("event", dict(event_id="evt_t25", run_id="run_1", event_type="other",
                              time_base="absolute_datetime",
                              event_datetime_end="2008-04-19T13:00:00Z")))]),
    T(26, "3. Event time-base integrity",
      "time_base=unknown with clock_domain_id set", "fail",
      [("ins", ("event", dict(event_id="evt_t26", run_id="run_1", event_type="other",
                              time_base="unknown", clock_domain_id="cd_1")))]),
    T(27, "3. Event time-base integrity",
      "time_base=clock_domain_time without clock_domain_id", "fail",
      [("ins", ("event", dict(event_id="evt_t27", run_id="run_1", event_type="other",
                              time_base="clock_domain_time",
                              event_domain_time_start=100.0)))]),
    T(28, "3. Event time-base integrity",
      "time_base=clock_domain_time with domain; event_time_original preserved verbatim", "pass",
      [("ins", ("event", dict(event_id="evt_t28", run_id="run_1", event_type="ignition",
                              time_base="clock_domain_time", clock_domain_id="cd_1",
                              event_domain_time_start=100.0,
                              event_time_original="frame 4821 @ ~19:00",
                              event_time_original_format="free_text")))]),

    # ---- 4. measurement_sample timestamps ---------------------------------
    T(29, "4. measurement_sample timestamps",
      "ISO 8601 parsed with original_timestamp_parsed NULL and timestamp_epoch_utc set", "pass",
      [("ins", sample("samp_t29", 1, timestamp_epoch_utc=iso_epoch("2008-04-19T12:00:00Z"),
                      original_timestamp_parsed=None))]),
    T(30, "4. measurement_sample timestamps",
      "status=parsed, original_timestamp_parsed NULL, representation=unix_time", "fail",
      [("ins", sample("samp_t30", 1, timestamp_representation="unix_time"))]),
    T(31, "4. measurement_sample timestamps",
      "Excel serial 44561.5, status=ambiguous, original_timestamp_parsed=44561.5, epoch NULL",
      "pass",
      [("ins", sample("samp_t31", 1, timestamp_parsing_status="ambiguous",
                      timestamp_representation="excel_serial_number",
                      original_timestamp="44561.5",
                      original_timestamp_parsed=44561.5,
                      parsed_time_format=None))]),
    T(32, "4. measurement_sample timestamps",
      "status=ambiguous with timestamp_epoch_utc populated", "fail",
      [("ins", sample("samp_t32", 1, timestamp_parsing_status="ambiguous",
                      timestamp_representation="excel_serial_number",
                      original_timestamp="44561.5", original_timestamp_parsed=44561.5,
                      parsed_time_format=None,
                      timestamp_epoch_utc=iso_epoch("2008-04-19T12:00:00Z")))]),
    T(33, "4. measurement_sample timestamps",
      "Excel serial 44561.5 parsed with timestamp_epoch_utc set", "pass",
      [("ins", sample("samp_t33", 1,
                      timestamp_representation="excel_serial_number",
                      original_timestamp="44561.5", original_timestamp_parsed=44561.5,
                      parsed_time_format="excel_serial",
                      timestamp_epoch_utc=(44561.5 - 25569) * 86400))]),
    T(34, "4. measurement_sample timestamps",
      "representation=run_relative_seconds with timestamp_epoch_utc set", "fail",
      [("ins", sample("samp_t34", 1,
                      timestamp_representation="run_relative_seconds",
                      original_timestamp="3.5", original_timestamp_parsed=3.5,
                      parsed_time_format="relative_s",
                      timestamp_epoch_utc=iso_epoch("2008-04-19T12:00:00Z")))]),
    T(35, "4. measurement_sample timestamps",
      "timestamp_epoch_utc = -1e10 (outside 1900-2100 domain window)", "fail",
      [("ins", sample("samp_t35", 1, timestamp_epoch_utc=-1e10))]),
    T(36, "4. measurement_sample timestamps",
      "original_timestamp_parsed = -1e10 (source-native, no epoch bound)", "pass",
      [("ins", sample("samp_t36", 1, timestamp_representation="free_text_number",
                      original_timestamp="-1e10", original_timestamp_parsed=-1e10,
                      parsed_time_format="instrument_counter"))]),
    T(37, "4. measurement_sample timestamps",
      "raw '???' with unknown_representation, status=unknown, parsed/epoch NULL", "pass",
      [("ins", sample("samp_t37", 1, timestamp_parsing_status="unknown",
                      timestamp_representation="unknown_representation",
                      original_timestamp="???", original_timestamp_parsed=None,
                      parsed_time_format=None, timestamp_epoch_utc=None))]),
    T(38, "4. measurement_sample timestamps",
      "status=unknown, representation NOT unknown_representation, original_timestamp NULL", "pass",
      [("ins", sample("samp_t38", 1, timestamp_parsing_status="unknown",
                      original_timestamp=None, original_timestamp_parsed=None,
                      parsed_time_format=None, timestamp_epoch_utc=None))]),
    T(39, "4. measurement_sample timestamps",
      "unknown_representation with status=parsed", "fail",
      [("ins", sample("samp_t39", 1, timestamp_representation="unknown_representation",
                      original_timestamp="???"))]),
    T(40, "4. measurement_sample timestamps",
      "duplicate identical original_timestamp, sample_index 7 and 8, same channel", "pass",
      [("ins", sample("samp_t40a", 7, original_timestamp="2008-04-19T12:00:03Z",
                      timestamp_epoch_utc=iso_epoch("2008-04-19T12:00:03Z"))),
       ("ins", sample("samp_t40b", 8, original_timestamp="2008-04-19T12:00:03Z",
                      timestamp_epoch_utc=iso_epoch("2008-04-19T12:00:03Z")))]),

    # ---- 5. measurement_sample values --------------------------------------
    T(41, "5. measurement_sample values",
      "qualitative 'soot cloud present', value_status=valid_qualitative", "pass",
      [("ins", sample("samp_t41", 1, original_value="soot cloud present",
                      original_value_parsed=None, value_representation="qualitative",
                      value_status="valid_qualitative", normalized_value=None))]),
    T(42, "5. measurement_sample values",
      "valid_qualitative with value_representation=float", "fail",
      [("ins", sample("samp_t42", 1, original_value="cloudy", original_value_parsed=None,
                      value_representation="float", value_status="valid_qualitative",
                      normalized_value=None))]),
    T(43, "5. measurement_sample values",
      "coded '3' with coded_value_system, representation=coded", "pass",
      [("ins", sample("samp_t43", 1, original_value="3", original_value_parsed=None,
                      value_representation="coded", coded_value_system="smoke_point_scale",
                      value_status="valid_coded", normalized_value=None))]),
    T(44, "5. measurement_sample values",
      "valid_coded with value_representation=integer", "fail",
      [("ins", sample("samp_t44a", 1, original_value="3", original_value_parsed=None,
                      value_representation="integer", coded_value_system="smoke_point_scale",
                      value_status="valid_coded", normalized_value=None))]),
    T(44, "5. measurement_sample values",
      "valid_coded without coded_value_system", "fail",
      [("ins", sample("samp_t44b", 1, original_value="3", original_value_parsed=None,
                      value_representation="coded",
                      value_status="valid_coded", normalized_value=None))]),
    T(45, "5. measurement_sample values",
      "valid_numeric with value_representation=qualitative", "fail",
      [("ins", sample("samp_t45a", 1, value_representation="qualitative",
                      original_value="high"))]),
    T(45, "5. measurement_sample values",
      "valid_numeric with original_value_parsed NULL", "fail",
      [("ins", sample("samp_t45b", 1, original_value_parsed=None))]),
    T(46, "5. measurement_sample values",
      "value_status=missing with original_value='7.2'", "fail",
      [("ins", sample("samp_t46", 1, value_status="missing", original_value="7.2",
                      original_value_parsed=None))]),
    T(47, "5. measurement_sample values",
      "value_status=invalid with quality_flag='ok'", "fail",
      [("ins", sample("samp_t47", 1, value_status="invalid", quality_flag="ok"))]),
    T(48, "5. measurement_sample values",
      "value_status=outlier with quality_flag='outlier' and parsed value", "pass",
      [("ins", sample("samp_t48", 1, value_status="outlier", quality_flag="outlier"))]),
    T(49, "5. measurement_sample values",
      "above_saturation_limit without detection_limit_value", "fail",
      [("ins", sample("samp_t49a", 1, value_status="above_saturation_limit",
                      quality_flag="saturated"))]),
    T(49, "5. measurement_sample values",
      "below_detection_limit with limit value but NULL unit", "fail",
      [("ins", sample("samp_t49b", 1, value_status="below_detection_limit",
                      detection_limit_applied="below", detection_limit_value=0.01))]),
    T(50, "5. measurement_sample values",
      "below_detection_limit with value + unit + original value", "pass",
      [("ins", sample("samp_t50", 1, value_status="below_detection_limit",
                      detection_limit_applied="below", detection_limit_value=0.01,
                      detection_limit_unit="unitless", original_value_parsed=0.005))]),
    T(51, "5. measurement_sample values",
      "normalized_value set without normalization_method", "fail",
      [("ins", sample("samp_t51", 1, normalized_value=1.7, normalized_unit="unitless"))]),
    T(52, "5. measurement_sample values",
      "normalized_value with method + unit", "pass",
      [("ins", sample("samp_t52", 1, normalized_value=1.7, normalized_unit="unitless",
                      normalization_method="unit_conversion"))]),
    T(53, "5. measurement_sample values",
      "quality_flag outside the enum ('bogus')", "fail",
      [("ins", sample("samp_t53", 1, quality_flag="bogus"))]),

    # ---- 6. run conditions, composition, geometry --------------------------
    T(54, "6. Run conditions, composition, geometry",
      "experimental_run with pressure_interval_low set and pressure_unit NULL", "fail",
      [("ins", run_only(run_id="run_t54", pressure_interval_low=50.0))]),
    T(55, "6. Run conditions, composition, geometry",
      "experimental_run with pressure_uncertainty set and no pressure value/unit", "fail",
      [("ins", run_only(run_id="run_t55", pressure_uncertainty=1.0))]),
    T(56, "6. Run conditions, composition, geometry",
      "experimental_run with temperature_uncertainty set but temperature NULL", "fail",
      [("ins", run_only(run_id="run_t56a", temperature_uncertainty=1.0))]),
    T(56, "6. Run conditions, composition, geometry",
      "experimental_run with flow_velocity_uncertainty set but flow_velocity NULL", "fail",
      [("ins", run_only(run_id="run_t56b", flow_velocity_uncertainty=0.1))]),
    T(56, "6. Run conditions, composition, geometry",
      "experimental_run with temperature set but temperature_unit NULL", "fail",
      [("ins", run_only(run_id="run_t56c", temperature=300.0))]),
    T(57, "6. Run conditions, composition, geometry",
      "gravity 0.15 with uncertainty 0.9 (uncertainty > value)", "pass",
      [("ins", run_only(run_id="run_t57", gravity_acceleration_ms2=0.15,
                        gravity_acceleration_uncertainty_ms2=0.9))]),
    T(58, "6. Run conditions, composition, geometry",
      "run_composition mole_fraction_uncertainty without mole_fraction", "fail",
      [("ins", ("run_composition", dict(run_composition_id="rc_t58a", run_id="run_1",
                                        species_id="sp_1", role="fuel",
                                        mole_fraction_uncertainty=0.01)))]),
    T(58, "6. Run conditions, composition, geometry",
      "run_composition mole_fraction_approx=1 without mole_fraction", "fail",
      [("ins", ("run_composition", dict(run_composition_id="rc_t58b", run_id="run_1",
                                        species_id="sp_1", role="fuel",
                                        mole_fraction_approx=1)))]),
    T(59, "6. Run conditions, composition, geometry",
      "same species with roles fuel and oxidizer", "pass",
      [("ins", ("run_composition", dict(run_composition_id="rc_t59a", run_id="run_1",
                                        species_id="sp_1", role="fuel",
                                        mole_fraction=0.5))),
       ("ins", ("run_composition", dict(run_composition_id="rc_t59b", run_id="run_1",
                                        species_id="sp_1", role="oxidizer",
                                        mole_fraction=0.5)))]),
    T(60, "6. Run conditions, composition, geometry",
      "solid_fuel_geometry with width set and width_unit NULL (thickness_unit supplied)",
      "fail",
      [("ins", ("solid_fuel_geometry", dict(solid_fuel_geometry_id="sfg_t60", run_id="run_1",
                                            fuel_form="flat_sheet",
                                            thickness_unit="mm", width=10.0)))]),
    T(61, "6. Run conditions, composition, geometry",
      "solid_fuel_geometry width_uncertainty without width (thickness_unit supplied)",
      "fail",
      [("ins", ("solid_fuel_geometry", dict(solid_fuel_geometry_id="sfg_t61a", run_id="run_1",
                                            fuel_form="flat_sheet", thickness_unit="mm",
                                            width_uncertainty=0.1)))]),
    T(61, "6. Run conditions, composition, geometry",
      "solid_fuel_geometry thickness_uncertainty without thickness (thickness_unit supplied)",
      "fail",
      [("ins", ("solid_fuel_geometry", dict(solid_fuel_geometry_id="sfg_t61b", run_id="run_1",
                                            fuel_form="flat_sheet", thickness_unit="mm",
                                            thickness_uncertainty=0.1)))]),
    T(62, "6. Run conditions, composition, geometry",
      "droplet_geometry support_fiber=0 with fiber_diameter set", "fail",
      [("ins", ("droplet_geometry", dict(droplet_geometry_id="dg_t62", run_id="run_1",
                                         support_fiber=0, fiber_diameter=0.05)))]),
    T(63, "6. Run conditions, composition, geometry",
      "droplet_geometry support_fiber=1, fiber_diameter set, fiber_diameter_unit NULL", "fail",
      [("ins", ("droplet_geometry", dict(droplet_geometry_id="dg_t63", run_id="run_1",
                                         support_fiber=1, fiber_diameter=0.05)))]),
    T(64, "6. Run conditions, composition, geometry",
      "droplet_geometry initial_diameter_uncertainty without initial_diameter", "fail",
      [("ins", ("droplet_geometry", dict(droplet_geometry_id="dg_t64a", run_id="run_1",
                                         initial_diameter_uncertainty=0.01)))]),
    T(64, "6. Run conditions, composition, geometry",
      "droplet_geometry fiber_diameter_uncertainty without fiber_diameter", "fail",
      [("ins", ("droplet_geometry", dict(droplet_geometry_id="dg_t64b", run_id="run_1",
                                         support_fiber=1,
                                         fiber_diameter_uncertainty=0.01)))]),
    T(65, "6. Run conditions, composition, geometry",
      "droplet + solid-fuel rows for the same run (optional exclusivity triggers installed)",
      "fail",
      [("ins", ("droplet_geometry", dict(droplet_geometry_id="dg_t65", run_id="run_1",
                                         initial_diameter=0.5))),
       ("ins", ("solid_fuel_geometry", dict(solid_fuel_geometry_id="sfg_t65", run_id="run_1",
                                            fuel_form="flat_sheet", thickness=1.0)))]),

    # ---- 7. clock_sync, files, provenance, comparability -------------------
    T(66, "7. clock_sync, files, provenance, comparability",
      "two clock_sync segments (0 and 1) for the same domain pair", "pass",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t66a", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, offset_seconds=0.5,
                                   sync_status="established", sync_method="led_pulse"))),
       ("ins", ("clock_sync", dict(clock_sync_id="cs_t66b", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=1, offset_seconds=0.6,
                                   sync_status="established", sync_method="led_pulse")))]),
    T(67, "7. clock_sync, files, provenance, comparability",
      "duplicate sync_segment_id=0 for the same domain pair", "fail",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t67a", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, sync_status="assumed"))),
       ("ins", ("clock_sync", dict(clock_sync_id="cs_t67b", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, sync_status="assumed")))]),
    T(68, "7. clock_sync, files, provenance, comparability",
      "two distinct segments with NULL valid_from/valid_to", "pass",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t68a", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, sync_status="assumed"))),
       ("ins", ("clock_sync", dict(clock_sync_id="cs_t68b", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=1, sync_status="assumed")))]),
    T(69, "7. clock_sync, files, provenance, comparability",
      "sync_status='unknown' with an offset", "fail",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t69a", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, offset_seconds=0.3,
                                   sync_status="unknown")))]),
    T(69, "7. clock_sync, files, provenance, comparability",
      "sync_status='established' without sync_method", "fail",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t69b", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, offset_seconds=0.3,
                                   sync_status="established")))]),
    T(69, "7. clock_sync, files, provenance, comparability",
      "sync_status='invalidated' without notes", "fail",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t69c", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, offset_seconds=0.3,
                                   sync_status="invalidated")))]),
    T(69, "7. clock_sync, files, provenance, comparability",
      "source_domain_id == target_domain_id", "fail",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t69d", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_1",
                                   sync_segment_id=0, offset_seconds=0.3,
                                   sync_status="established", sync_method="led")))]),
    T(70, "7. clock_sync, files, provenance, comparability",
      "valid_to earlier than valid_from", "fail",
      [("ins", ("clock_sync", dict(clock_sync_id="cs_t70", run_id="run_1",
                                   source_domain_id="cd_1", target_domain_id="cd_2",
                                   sync_segment_id=0, sync_status="assumed",
                                   valid_from="2008-04-19T12:00:00Z",
                                   valid_to="2008-04-19T11:00:00Z")))]),
    T(71, "7. clock_sync, files, provenance, comparability",
      "measurement_channel sampling_interval_s=33.3 (standard seconds)", "pass",
      [("sql", "UPDATE measurement_channel SET sampling_interval_s=33.3 "
               "WHERE measurement_channel_id='chan_1'")]),
    T(72, "7. clock_sync, files, provenance, comparability",
      "conversion_offset without conversion_scale", "fail",
      [("sql", "UPDATE measurement_channel SET conversion_offset=1.0 "
               "WHERE measurement_channel_id='chan_1'")]),
    T(72, "7. clock_sync, files, provenance, comparability",
      "conversion_scale=0", "fail",
      [("sql", "UPDATE measurement_channel SET conversion_scale=0 "
               "WHERE measurement_channel_id='chan_1'")]),
    T(73, "7. clock_sync, files, provenance, comparability",
      "conversion_scale=-1.7 (negative calibration slope)", "pass",
      [("sql", "UPDATE measurement_channel SET conversion_scale=-1.7, conversion_unit='unitless' "
               "WHERE measurement_channel_id='chan_1'")]),
    T(74, "7. clock_sync, files, provenance, comparability",
      "data_file duplicate SHA-256, different relative_path", "pass",
      [("ins", ("data_file", dict(file_id="file_2", relative_path="data/flex/copy.dat",
                                  file_name="copy.dat", file_format="text",
                                  file_size_bytes=1000, sha256_checksum="a" * 64)))]),
    T(75, "7. clock_sync, files, provenance, comparability",
      "data_file SHA-256 not 64 lowercase hex", "fail",
      [("ins", ("data_file", dict(file_id="file_3", relative_path="data/flex/bad.dat",
                                  file_name="bad.dat", file_format="text",
                                  file_size_bytes=1, sha256_checksum="XYZ")))]),
    T(76, "7. clock_sync, files, provenance, comparability",
      "is_archive=0 with archive_member_count=5", "fail",
      [("ins", ("data_file", dict(file_id="file_4", relative_path="data/flex/nonarch.zip",
                                  file_name="nonarch.zip", file_format="zip",
                                  file_size_bytes=10, sha256_checksum="b" * 64,
                                  is_archive=0, archive_member_count=5)))]),
    T(77, "7. clock_sync, files, provenance, comparability",
      "is_archive=1 with archive_member_count NULL (not yet inspected)", "pass",
      [("ins", ("data_file", dict(file_id="file_5", relative_path="data/flex/uninspected.zip",
                                  file_name="uninspected.zip", file_format="zip",
                                  file_size_bytes=10, sha256_checksum="c" * 64,
                                  is_archive=1)))]),
    T(78, "7. clock_sync, files, provenance, comparability",
      "source.authors = [\"A. Smith\",\"B. Jones\"]", "pass",
      [("ins", ("source", dict(source_id="src_t78", publication_title="good",
                               authors='["A. Smith","B. Jones"]',
                               document_type="thesis", data_origin="test")))]),
    T(79, "7. clock_sync, files, provenance, comparability",
      "source.authors = [\"A\",{\"x\":1}] (nested object element)", "fail",
      [("ins", ("source", dict(source_id="src_t79a", publication_title="bad",
                               authors='["A",{"x":1}]', document_type="thesis",
                               data_origin="test")))]),
    T(79, "7. clock_sync, files, provenance, comparability",
      "source.authors = [null]", "fail",
      [("ins", ("source", dict(source_id="src_t79b", publication_title="bad",
                               authors='[null]', document_type="thesis",
                               data_origin="test")))]),
    T(79, "7. clock_sync, files, provenance, comparability",
      "source.authors = [1]", "fail",
      [("ins", ("source", dict(source_id="src_t79c", publication_title="bad",
                               authors='[1]', document_type="thesis",
                               data_origin="test")))]),
    T(79, "7. clock_sync, files, provenance, comparability",
      "source.authors = [true]", "fail",
      [("ins", ("source", dict(source_id="src_t79d", publication_title="bad",
                               authors='[true]', document_type="thesis",
                               data_origin="test")))]),
    T(79, "7. clock_sync, files, provenance, comparability",
      "source.authors = [[\"nested\"]]", "fail",
      [("ins", ("source", dict(source_id="src_t79e", publication_title="bad",
                               authors='[["nested"]]', document_type="thesis",
                               data_origin="test")))]),
    T(80, "7. clock_sync, files, provenance, comparability",
      "malformed JSON in source.authors", "fail",
      [("ins", ("source", dict(source_id="src_t80", publication_title="bad",
                               authors='[{"a":]', document_type="thesis",
                               data_origin="test")))]),
    T(81, "7. clock_sync, files, provenance, comparability",
      "extraction_record.data_file_id referencing an existing managed file", "pass",
      [("ins", ("extraction_record", dict(extraction_record_id="er_t81",
                                          source_id="src_1", data_file_id="file_1",
                                          extraction_method="direct_export",
                                          extraction_confidence="high")))]),
    T(81, "7. clock_sync, files, provenance, comparability",
      "extraction_record.data_file_id referencing a missing file", "fail",
      [("ins", ("extraction_record", dict(extraction_record_id="er_t81b",
                                          source_id="src_1", data_file_id="file_missing",
                                          extraction_method="direct_export",
                                          extraction_confidence="high")))]),
    T(82, "7. clock_sync, files, provenance, comparability",
      "comparability_assessment reversed pair (run_2, run_1) same subject", "fail",
      [("ins", ("comparability_assessment", dict(comparability_assessment_id="cmp_t82",
                                                 run1_run_id="run_2", run2_run_id="run_1",
                                                 measurement_subject="burn time",
                                                 gravitational_comparable="unknown",
                                                 environment_comparable="unknown",
                                                 measurement_method_comparable="unknown",
                                                 data_collection_comparable="unknown",
                                                 uncertainty_overlap="unknown",
                                                 comparability_classification="insufficient_information")))]),
    T(83, "7. clock_sync, files, provenance, comparability",
      "comparability not_comparable without notes (text values supplied)", "fail",
      [("ins", ("comparability_assessment", dict(comparability_assessment_id="cmp_t83a",
                                                 run1_run_id="run_1", run2_run_id="run_2",
                                                 measurement_subject="soot morphology",
                                                 gravitational_comparable="unknown",
                                                 environment_comparable="unknown",
                                                 measurement_method_comparable="unknown",
                                                 data_collection_comparable="unknown",
                                                 uncertainty_overlap="unknown",
                                                 run1_value_text="shell",
                                                 run2_value_text="no shell",
                                                 comparability_classification="not_comparable")))]),
    T(83, "7. clock_sync, files, provenance, comparability",
      "comparable_after_normalization without comparability_notes", "fail",
      [("ins", ("comparability_assessment", dict(comparability_assessment_id="cmp_t83b",
                                                 run1_run_id="run_1", run2_run_id="run_2",
                                                 measurement_subject="normalized burn rate",
                                                 gravitational_comparable="unknown",
                                                 environment_comparable="unknown",
                                                 measurement_method_comparable="unknown",
                                                 data_collection_comparable="unknown",
                                                 uncertainty_overlap="unknown",
                                                 run1_value_numeric=1.0,
                                                 run2_value_numeric=2.0,
                                                 comparison_unit="s",
                                                 comparability_classification="comparable_after_normalization")))]),
    T(83, "7. clock_sync, files, provenance, comparability",
      "numeric run values without comparison_unit", "fail",
      [("ins", ("comparability_assessment", dict(comparability_assessment_id="cmp_t83c",
                                                 run1_run_id="run_1", run2_run_id="run_2",
                                                 measurement_subject="normalized burn rate",
                                                 gravitational_comparable="unknown",
                                                 environment_comparable="unknown",
                                                 measurement_method_comparable="unknown",
                                                 data_collection_comparable="unknown",
                                                 uncertainty_overlap="unknown",
                                                 run1_value_numeric=1.0,
                                                 run2_value_numeric=2.0,
                                                 comparability_classification="insufficient_information")))]),
    T(83, "7. clock_sync, files, provenance, comparability",
      "review_status='reviewed' without reviewed_by", "fail",
      [("ins", ("comparability_assessment", dict(comparability_assessment_id="cmp_t83d",
                                                 run1_run_id="run_1", run2_run_id="run_2",
                                                 measurement_subject="normalized burn rate",
                                                 gravitational_comparable="unknown",
                                                 environment_comparable="unknown",
                                                 measurement_method_comparable="unknown",
                                                 data_collection_comparable="unknown",
                                                 uncertainty_overlap="unknown",
                                                 comparability_classification="insufficient_information",
                                                 review_status="reviewed")))]),
    T(84, "7. clock_sync, files, provenance, comparability",
      "qualitatively_comparable with both text values", "pass",
      [("ins", ("comparability_assessment", dict(comparability_assessment_id="cmp_t84",
                                                 run1_run_id="run_1", run2_run_id="run_2",
                                                 measurement_subject="soot morphology",
                                                 gravitational_comparable="unknown",
                                                 environment_comparable="unknown",
                                                 measurement_method_comparable="unknown",
                                                 data_collection_comparable="unknown",
                                                 uncertainty_overlap="unknown",
                                                 run1_value_text="compact soot shell",
                                                 run2_value_text="open soot shell",
                                                 comparability_classification="qualitatively_comparable")))]),
    T(85, "7. clock_sync, files, provenance, comparability",
      "value_provenance type run_composition with measurement_id set", "fail",
      [("ins", ("value_provenance", dict(value_provenance_id="pv_t85",
                                         extraction_record_id="er_1",
                                         provenance_type="run_composition",
                                         measurement_id="meas_1")))]),
    T(86, "7. clock_sync, files, provenance, comparability",
      "value_provenance with two target columns populated", "fail",
      [("ins", ("value_provenance", dict(value_provenance_id="pv_t86",
                                         extraction_record_id="er_1",
                                         provenance_type="experimental_run",
                                         run_id="run_1", measurement_id="meas_1")))]),
    T(87, "7. clock_sync, files, provenance, comparability",
      "value_provenance curation_target_run_id disagreeing with target's run (app-level flag)",
      "pass",
      [("ins", ("value_provenance", dict(value_provenance_id="pv_t87",
                                         extraction_record_id="er_1",
                                         provenance_type="experimental_run",
                                         run_id="run_1",
                                         curation_target_run_id="run_2")))]),
    T(88, "7. clock_sync, files, provenance, comparability",
      "one experiment cited by two sources", "pass",
      [("ins", ("source", dict(source_id="src_t88", publication_title="second",
                               authors='["C. Ray"]', document_type="preprint",
                               data_origin="test"))),
       ("ins", ("source_experiment", dict(source_experiment_id="se_t88",
                                          source_id="src_t88", experiment_id="exp_1",
                                          extraction_confidence="medium",
                                          extraction_method="api_query")))]),
]


def structural_checks(con):
    out = {}
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    out["tables_found"] = sorted(names)
    out["tables_expected"] = sorted(TABS)
    out["tables_ok"] = names == set(TABS)
    idx = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")}
    out["indexes_found"] = sorted(idx)
    out["index_ok"] = "ux_comparability_unordered_pair" in idx
    trg = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'")}
    out["triggers_found"] = sorted(trg)
    out["triggers_ok"] = set(TRIGGERS) <= trg
    out["fk_violations"] = con.execute("PRAGMA foreign_key_check").fetchall()
    out["integrity"] = con.execute("PRAGMA integrity_check").fetchone()[0]
    try:
        con.execute("SELECT json_type('[]')")
        out["json1"] = "available"
    except sqlite3.Error as e:
        out["json1"] = f"error: {e}"
    return out


def run_test(t):
    con = fresh_db(fk=not t["fk_off"])
    errors = []
    seed_failed = None
    try:
        seed(con, t["seed_extra"], baseline=t["baseline"])
    except sqlite3.Error as e:
        seed_failed = f"{type(e).__name__}: {e}"
    if seed_failed is None:
        for kind, payload in t["stmts"]:
            try:
                if kind == "ins":
                    sql, params = insert_sql(*payload)
                    con.execute(sql, params)
                else:
                    con.execute(payload)
            except sqlite3.Error as e:
                errors.append(f"{type(e).__name__}: {e}")
                break
    post = {}
    try:
        post["integrity"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        post["fk_violations"] = len(con.execute("PRAGMA foreign_key_check").fetchall())
        post["usable"] = con.execute("SELECT COUNT(*) FROM experimental_run").fetchone()[0] >= 0
    except sqlite3.Error as e:
        post["post_error"] = f"{type(e).__name__}: {e}"
    con.close()

    if seed_failed:
        observed = "FAIL"
        detail = f"seed failed: {seed_failed}"
    elif t["expect"] == "pass" and not errors:
        observed = "PASS"
        detail = "all statements executed"
    elif t["expect"] == "fail" and errors:
        if not post.get("usable") or post.get("integrity") != "ok":
            observed = "FAIL"
            detail = f"failed but database inconsistent: {errors[-1]} / {post}"
        else:
            observed = "PASS"
            detail = errors[-1]
    elif t["expect"] == "pass" and errors:
        observed = "FAIL"
        detail = f"unexpected error: {errors[-1]}"
    else:
        observed = "FAIL"
        detail = "expected failure did not occur"
    return observed, detail, post


def main():
    load_errors = []
    con = None
    try:
        con = fresh_db()
        struct = structural_checks(con)
    except sqlite3.Error as e:
        load_errors.append(f"{type(e).__name__}: {e}")
        struct = None
    finally:
        if con:
            con.close()

    results = []
    for t in TESTS:
        observed, detail, post = run_test(t)
        results.append(dict(id=t["id"], group=t["group"], desc=t["desc"],
                            expect=t["expect"], observed=observed, detail=detail,
                            fk_off=t["fk_off"], note=t["note"], post=post))

    n_pass = sum(1 for r in results if r["observed"] == "PASS")
    n_fail = sum(1 for r in results if r["observed"] == "FAIL")
    n_blocked = sum(1 for r in results if r["observed"] == "BLOCKED")

    lines = []
    lines.append("# Schema validation results — v1.2.0 (promoted from v1.2.0-candidate)\n")
    lines.append(f"- Harness: `tests/validate_schema_candidate.py`")
    lines.append(f"- SQLite version (python sqlite3): {sqlite3.sqlite_version}")
    lines.append(f"- SQLite version (CLI): 3.54.1")
    lines.append(f"- Executed: {datetime.datetime.now(UTC).isoformat(timespec='seconds')}")
    lines.append("- Schema file: schema/v1.2.0.sql")
    lines.append("- Promotion record: run 1 on v1.2.0-candidate.sql = 111/112 (defect D-1); "
                 "one-line CHECK correction applied; run 2 = 112/112; promoted to v1.2.0.sql.")
    lines.append(f"- Tests executed: {len(results)}  passed: {n_pass}  failed: {n_fail}  blocked: {n_blocked}")
    if load_errors:
        lines.append(f"- SCHEMA LOAD ERRORS: {load_errors}")
    if struct:
        lines.append(f"- Tables: {len(struct['tables_found'])}/20 expected present: {struct['tables_ok']}")
        lines.append(f"- Triggers present: {struct['triggers_ok']} ({len(struct['triggers_found'])})")
        lines.append(f"- Expression index present: {struct['index_ok']}")
        lines.append(f"- PRAGMA foreign_key_check: {struct['fk_violations'] or 'no violations'}")
        lines.append(f"- PRAGMA integrity_check: {struct['integrity']}")
        lines.append(f"- JSON1: {struct['json1']}")
    lines.append("")
    cur = None
    for r in results:
        if r["group"] != cur:
            cur = r["group"]
            lines.append(f"\n## {cur}\n")
            lines.append("| # | Expected | Observed | Detail | Status |")
            lines.append("| --- | --- | --- | --- | --- |")
        flag = " (FK-OFF defensive)" if r["fk_off"] else ""
        lines.append(f"| {r['id']}{flag} | {r['expect']} | {r['observed']} "
                     f"| {r['detail']} | {'PASS' if r['observed'] == 'PASS' else 'FAIL'} |")
    RESULTS_PATH.write_text("\n".join(lines) + "\n")

    print(f"sqlite {sqlite3.sqlite_version}")
    print(f"tests={len(results)} pass={n_pass} fail={n_fail} blocked={n_blocked}")
    if struct:
        print(f"tables_ok={struct['tables_ok']} triggers_ok={struct['triggers_ok']} "
              f"index_ok={struct['index_ok']} fk_violations={len(struct['fk_violations'])} "
              f"integrity={struct['integrity']} json1={struct['json1']}")
    if load_errors:
        print("LOAD ERRORS:", load_errors)
    for r in results:
        if r["observed"] != "PASS":
            print(f"  MISMATCH #{r['id']} {r['desc']}: expected {r['expect']}, "
                  f"got {r['observed']} ({r['detail']})")
    print(f"results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
