#!/usr/bin/env python3
"""FLEX PSI-69 Phase 3 — scientific validation pipeline.

Local, read-only with respect to ALL existing project artifacts. This script:

  1. verifies the SHA-256 of every protected file (raw data, schema, src,
     tests, and the frozen Phase 1 / Phase 2 deliverables) and refuses to
     proceed if any has changed;
  2. loads the raw experimental table with its OWN byte-preserving loader
     (independent of the Phase 2 code path) and recomputes the quantities
     cited in the validation documents into validation_checks.csv;
  3. writes the curated evidence register and validation matrix;
  4. writes run_manifest.json recording inputs, hashes, versions, timestamp,
     integrity-check results and limitations.

It performs NO scientific modelling, NO unit assignment, NO imputation and
NO composition renormalisation. Its only job is traceability.

Run from the repository root:
    notebooks/.venv/bin/python analysis/validation/run_validation.py
"""

import csv
import datetime
import glob
import hashlib
import json
import os
import platform
import re
import sys
from collections import Counter, OrderedDict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

MISSING_BYTE = "\x96"
FUELS = ("Methanol", "Heptane")
CORE = ("d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s")

PROTECTED = [
    "data/raw/flex/PSI-69_Experimental table_FLEX.csv",
    "data/raw/flex/s_PSI-69.txt",
    "schema/v1.2.0.sql",
    "src/prediction/predictor.py",
    "tests/validate_schema_candidate.py",
] + [os.path.join(d, f)
     for d, _, fs in sorted(os.walk(os.path.join(ROOT, "analysis", "audit")))
     for f in sorted(fs) if "__pycache__" not in d
     ] + [os.path.join(d, f)
          for d, _, fs in sorted(os.walk(os.path.join(ROOT, "analysis", "exploratory")))
          for f in sorted(fs) if "__pycache__" not in d]

EXPECTED_PROTECTED_SHA256 = {
    # These constants are the frozen-state fingerprints taken when Phase 3 was
    # authored. tests/test_validation.py independently re-derives them from the
    # files and compares; any drift in a protected file fails the suite.
    "data/raw/flex/PSI-69_Experimental table_FLEX.csv":
        "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96",
}


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def is_missing(raw):
    if raw is None:
        return True
    s = raw.strip()
    return s == "" or s == MISSING_BYTE


def parse_measured(raw):
    if is_missing(raw):
        return None, False
    s = raw.strip()
    approx = s.startswith("~")
    if approx:
        s = s.lstrip("~").strip()
    try:
        return float(s), approx
    except ValueError:
        return None, False


def load_records():
    """Independent byte-preserving loader (same conventions as Phase 1)."""
    path = glob.glob(os.path.join(ROOT, "data", "raw", "flex", "PSI-69*FLEX.csv"))[0]
    with open(path, newline="", encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh))
    records = []
    for r in rows:
        rec = {
            "flex_test_no": r["FLEX Test #"].strip(),
            "flex_identifier": r["FLEX Identifier"].strip(),
            "test_date": r["Test Date"].strip(),
            "fuel": r["Fuel"].strip(),
            "test_end": r["Test end"].strip(),
        }
        for key, col in (("pressure_mmHg", "Ambient pressure; mmHg"),
                         ("o2_mf", "O initial ambient composition; mole fraction"),
                         ("n2_mf", "N initial ambient composition; mole fraction"),
                         ("co2_mf", "CO initial ambient composition; mole fraction"),
                         ("he_mf", "He initial ambient composition; mole fraction"),
                         ("d0_mm", "Droplet initial diameter; mm"),
                         ("d_ext_mm", "Visible flame extinction diameter; mm"),
                         ("burn_rate_raw", "Burning rate; mm"),
                         ("burn_time_s", "Burn time; s")):
            rec[key], rec[key + "_approx"] = parse_measured(r[col])
        records.append(rec)
    return records


def pressure_band(v):
    if v is None:
        return "not_reported"
    if v < 560:
        return "<560 mmHg"
    if v < 800:
        return "560-800 mmHg"
    if v <= 2100:
        return "800-2100 mmHg"
    return ">2100 mmHg"


def condition_family(r):
    return "O2={o}/N2={n}/CO2={c}/He={h}".format(
        o=r["o2_mf"], n=r["n2_mf"], c=r["co2_mf"], h=r["he_mf"])


def series_prefix(ident):
    m = re.match(r"^([0-9A-Z]*?)[A-Z]?[0-9]+$", ident)
    return m.group(1) if m else ident


# ---------------------------------------------------------------------------
# Recomputed validation quantities (digit-for-digit cited in the documents)
# ---------------------------------------------------------------------------
def recompute(records):
    meoh = [r for r in records if r["fuel"] == "Methanol"]
    hep = [r for r in records if r["fuel"] == "Heptane"]
    out = OrderedDict()
    out["n_records"] = len(records)
    out["n_methanol"] = len(meoh)
    out["n_heptane"] = len(hep)
    out["n_complete_core"] = sum(1 for r in records
                                 if all(r[k] is not None for k in CORE))
    dates = Counter(r["test_date"] for r in records)
    out["n_distinct_dates"] = len(dates)
    out["max_records_per_date"] = max(dates.values())
    out["n_series_prefixes"] = len(Counter(series_prefix(r["flex_identifier"])
                                           for r in records))
    out["largest_series_prefix"] = Counter(
        series_prefix(r["flex_identifier"]) for r in records).most_common(1)[0]
    m_fam = Counter(condition_family(r) for r in meoh)
    h_fam = Counter(condition_family(r) for r in hep)
    shared = set(m_fam) & set(h_fam)
    out["families_methanol"] = len(m_fam)
    out["families_heptane"] = len(h_fam)
    out["families_shared"] = len(shared)
    out["records_in_shared_families_methanol"] = sum(m_fam[f] for f in shared)
    out["records_in_shared_families_heptane"] = sum(h_fam[f] for f in shared)
    out["o2_levels_methanol"] = len(set(r["o2_mf"] for r in meoh))
    out["o2_levels_heptane"] = len(set(r["o2_mf"] for r in hep))
    out["pressure_bands_methanol"] = dict(Counter(pressure_band(r["pressure_mmHg"])
                                                  for r in meoh))
    out["pressure_bands_heptane"] = dict(Counter(pressure_band(r["pressure_mmHg"])
                                                 for r in hep))
    high = [r for r in records if (r["pressure_mmHg"] or 0) > 800]
    out["n_above_800_mmHg"] = len(high)
    out["families_above_800_mmHg"] = len(set(condition_family(r) for r in high))
    out["identifier_collision_193F001_count"] = sum(
        1 for r in records if r["flex_identifier"] == "193F001")
    return out


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Evidence register (curated; every row traceable to an inspected file)
# ---------------------------------------------------------------------------
def evidence_rows():
    E = []
    def add(q, var, claim, etype, src, loc, status, conf, lim, fu):
        E.append(OrderedDict(
            evidence_id=f"EV-{len(E)+1:03d}", research_question=q, variable=var,
            claim=claim, evidence_type=etype, source_document=src,
            source_location=loc, verification_status=status, confidence=conf,
            limitations=lim, required_followup=fu))

    add("Q1 measurement traceability", "droplet_initial_diameter",
        "Initial droplet diameter is dispensed to a nominal size with tolerance "
        "+/-0.25 mm and reproducibility +/-5% (FLEX-2 range 1.5-5 mm; FLEX-1 "
        "EIRD range 2-6 mm).",
        "requirements specification (documented)", "docs/flex/FLEX Engineering "
        "Requirements Document.pdf; docs/flex/FLEX_EIRD_v4.pdf",
        "ERD sections 4.1.12-4.1.13 (Droplet Size Tolerance / Reproducibility); "
        "EIRD section 5.1.2 (Droplet Deployment and Ignition)",
        "DOCUMENTED_BUT_UNCONFIRMED",
        "high", "Specification-level evidence: the tolerance is a dispenser "
        "requirement, not a per-run measured uncertainty for the table value.",
        "Obtain the range/calibration record of the dispenser or the per-test "
        "analyzed-data diameter values.")
    add("Q1 measurement traceability", "droplet_initial_diameter",
        "Imaging resolution requirement for droplet sizing is 30 um over the "
        "field of view, minimum frame rate 30 fps, back-lit view.",
        "requirements specification (documented)", "docs/flex/FLEX_EIRD_v4.pdf",
        "EIRD section 5.2.1 (Droplet Imaging)", "DOCUMENTED_BUT_UNCONFIRMED",
        "high", "Requirement text; no pixel-scale/calibration file for the "
        "table's diameter values was found in the audited data.",
        "Locate the analyzed-data diameter time series and its scale factor.")
    add("Q1 measurement traceability", "burning_rate",
        "The experimental-table column 'Burning rate; mm' has no documented "
        "definition or unit in any inspected source document.",
        "searched all inspected documents", "docs/flex/* (EIRD, Test Plan, "
        "ERD, DoD, Overall Ext File-2); analysis/audit/*; data/raw/flex/*",
        "full-text search for 'burning rate', 'burn rate', 'mm/s', 'mm2/s' "
        "in all PDFs/docx/txt under docs/ and data/", "UNVERIFIED", "high",
        "The only nearby documentary evidence is the EIRD's d2-law burning-rate "
        "constant discussion in mm2/s (literature/derived context), which is "
        "NOT a definition of this table column; unit inference from the numeric "
        "magnitude (0.05-1.06) is explicitly prohibited.",
        "UNIT UNVERIFIED - PHYSICAL INTERPRETATION BLOCKED. Obtain the PSI-69 "
        "data dictionary or the analysis code that produced the table column.")
    add("Q1 measurement traceability", "burning_rate",
        "EIRD documents the d2-law average burning rate constant for FLEX "
        "fuels in air at 1 atm as 0.8 mm2/s and states droplet burning rates "
        "and extinction diameters are obtained from back-lit droplet-size "
        "time-series imaging.",
        "research requirements document (secondary documentation)",
        "docs/flex/FLEX_EIRD_v4.pdf", "EIRD section 9 (Justification for "
        "Reduced Gravity, p.64) and section 5.2.1", "INFERRED", "medium",
        "Supports that the experiment's burning-rate constant is an "
        "image-derived quantity with mm2/s-class units in the requirements "
        "context; does NOT verify the PSI table column's header or derivation.",
        "Confirm with the data originator whether the table column is this "
        "constant, a linear regression rate, or another scalar.")
    add("Q1 measurement traceability", "extinction_diameter",
        "Extinction droplet diameter is intended to be measured from the same "
        "back-lit droplet imaging as the burning rate.",
        "requirements specification (documented)", "docs/flex/FLEX_EIRD_v4.pdf",
        "EIRD section 5.2.1", "DOCUMENTED_BUT_UNCONFIRMED", "medium",
        "Establishes measurement method class (image-derived) but not the "
        "specific reduction used for the table's single reported value.",
        "Obtain the reduced diameter time series behind the table value.")
    add("Q1 measurement traceability", "burn_duration",
        "Burn time in the table is a per-test scalar in seconds.",
        "column header in source table",
        "data/raw/flex/PSI-69_Experimental table_FLEX.csv",
        "column 'Burn time; s'", "VERIFIED", "high",
        "Header states seconds; two values carry a '~' approximation marker "
        "(6 s, 9 s) which is preserved as approximate in all analyses.",
        "Confirm the start/stop events defining burn time (ignition vs "
        "dispense; flame-out vs igniter-off).")
    add("Q1 measurement traceability", "ambient_pressure",
        "Ambient pressure is reported in mmHg in the table; the experimental "
        "requirement is 0.5-3 atm with tolerance +/-0.05 atm (ERD) and "
        "accuracy +/-0.01 atm (EIRD), maintained within +/-10% during a test.",
        "requirements specification + source header",
        "docs/flex/FLEX Engineering Requirements Document.pdf; "
        "docs/flex/FLEX_EIRD_v4.pdf; data/raw/flex/PSI-69_Experimental "
        "table_FLEX.csv", "ERD 4.1.34-4.1.35; EIRD 5.2.8; table column "
        "'Ambient pressure; mmHg'", "DOCUMENTED_BUT_UNCONFIRMED", "high",
        "Unit (mmHg) is verified by the header; the tolerance figures are "
        "spec-level, not per-run calibration records. One record reports "
        "0 mmHg (C11M201), physically implausible and flagged.",
        "Obtain chamber pressure calibration/verification records.")
    add("Q1 measurement traceability", "gas_composition",
        "O2 mole fractions are provided to 0.1-0.4 with an initial-charge "
        "tolerance of +/-0.005 mole fraction.",
        "requirements specification (documented)",
        "docs/flex/FLEX Engineering Requirements Document.pdf",
        "ERD 4.1.36", "DOCUMENTED_BUT_UNCONFIRMED", "high",
        "Spec-level tolerance; 29 table records have composition sums that do "
        "not equal 1.000 (not renormalised anywhere).",
        "Obtain the chamber gas charge/verification logs per run.")
    add("Q1 measurement traceability", "test_outcome",
        "The Test Plan documents an LOI-determination procedure using "
        "sequential, adaptive tests (burn-to-completion, finite extinction "
        "diameter, no-ignition), establishing what Extinction and Completion "
        "labels correspond to procedurally.",
        "test plan (documented)", "docs/flex/FLEX_Test_Plan.pdf",
        "Test Plan section 5.3", "DOCUMENTED_BUT_UNCONFIRMED", "medium",
        "Describes the LOI procedure; does not define the table's three label "
        "values operationally.", "Obtain the analyzed-data record definitions "
        "for the label column.")
    add("Q1 measurement traceability", "test_outcome",
        "The outcome label 'Disruption' (61 records) is not defined in any "
        "inspected document.",
        "searched all inspected documents", "docs/flex/* (EIRD, Test Plan, "
        "ERD, DoD, Overall Ext File-2); i_Investigation.txt",
        "full-text search for 'disruption' returned no definition", "UNVERIFIED",
        "high", "Label is used as an analysis category in Phase 2 without a "
        "documented definition; its physical meaning is unknown.",
        "Obtain the definition from the investigation team or analyzed-data "
        "dictionary before using Disruption as a scientific category.")
    add("Q1 measurement traceability", "experiment_table",
        "The experimental table originates from the NASA PSI data system "
        "(psi.nasa.gov); the investigation overview describes FLEX experiment "
        "data records organised by GMT and/or gas mixture.",
        "project documentation (local)", "docs/flex/i_Investigation.txt",
        "ontology/source reference lines and investigation description",
        "DOCUMENTED_BUT_UNCONFIRMED", "medium",
        "No DOI, publication reference, or version identifier for the specific "
        "CSV export is recorded in the audit or the file.",
        "Record the PSI export date/version and a citable source reference.")
    add("Q2 experimental design", "experimental_design",
        "LOI determination is a sequential adaptive procedure in which each "
        "test's conditions depend on the outcomes of previous tests.",
        "test plan (documented)", "docs/flex/FLEX_Test_Plan.pdf",
        "Test Plan section 5.3 (steps 1-8)", "VERIFIED", "high",
        "Direct documented evidence that the dataset is not a set of "
        "independently randomised runs; records within a series are "
        "procedurally dependent.", "Model the series structure explicitly in "
        "any future inferential analysis (e.g. series-stratified or "
        "permutation respecting series).")
    add("Q2 experimental design", "experimental_independence",
        "Up to 9 records share a single test date and 81 series prefixes "
        "(campaigns) group the 274 records, so run-level clustering is "
        "plausible.",
        "recomputed from raw table", "analysis/validation/validation_checks.csv",
        "rows n_distinct_dates, max_records_per_date, n_series_prefixes",
        "VERIFIED", "high", "Clustering is demonstrated structurally; whether "
        "it materially affects Phase 2 p-values is assessed only via the "
        "193F001 sensitivity rows.", "Quantify within-series correlation once "
        "per-run covariates are available.")
    add("Q2 experimental design", "identifier_193F001",
        "Two distinct records share FLEX identifier 193F001 (tests 70 and 73) "
        "with different measurements; joining on identifier alone would merge "
        "them.",
        "recomputed from raw table + Phase 1 audit",
        "analysis/validation/validation_checks.csv; analysis/audit/data_quality_report.md",
        "row identifier_collision_193F001_count; audit section 5", "VERIFIED",
        "high", "Removing either record moves the initial-diameter fuel "
        "contrast p from 0.0623 to 0.0449 (Phase 2 sensitivity rows).",
        "Resolve the identifier collision with the data originator.")
    add("Q2 experimental design", "gravity",
        "Microgravity requirement: accelerations < 1e-4 m/s2 on three axes; "
        "measurement capability accuracy 1e-6 m/s2 exists per requirements.",
        "requirements specification (documented)",
        "docs/flex/FLEX_EIRD_v4.pdf; docs/flex/FLEX Engineering Requirements "
        "Document.pdf", "EIRD 5.1.8; ERD 4.1.52-4.1.53", "DOCUMENTED_BUT_UNCONFIRMED",
        "medium", "No per-run g-level measurement is present in the audited "
        "data; the table has no gravity column.",
        "Obtain per-run ISS acceleration data if gravity effects are to be "
        "modelled.")
    add("Q2 experimental design", "fuel_identity",
        "Fuels: n-heptane (sooting) and methanol (non-sooting), research "
        "grade, purity > 99.5%, degassed, dry, fuel temperature 18-27 C.",
        "requirements specification (documented)", "docs/flex/FLEX_EIRD_v4.pdf",
        "EIRD section 6.1.1 (Test Fuels, hardware tabulation)", "DOCUMENTED_BUT_UNCONFIRMED", "high",
        "Spec-level; no per-run fuel lot certificates are available.",
        "Obtain fuel sample certifications.")
    add("Q2 experimental design", "fiber_support",
        "For the 8 telemetry-linked runs the testpoint setting "
        "FIBER_USAGE_FLAG is 'No' and soot-sampler flag is 'No'.",
        "telemetry testpoint settings (primary data)",
        "data/raw/flex/part-01/<TEST>_Testpoint_Settings.txt",
        "column TP_PARAMETER_FIBER_USAGE_FLAG(N/A), all 8 linked runs",
        "VERIFIED", "high", "Fiber usage for the remaining 266 records is "
        "unknown (no equivalent column in the experimental table).",
        "Obtain fiber-usage metadata for all runs before geometric analyses.")
    add("Q2 experimental design", "statistical_methods",
        "Phase 2 inferential p-values (Mann-Whitney, Spearman, Fisher) assume "
        "independent observations; with the documented adaptive series design "
        "and demonstrated clustering they are conditional on that assumption.",
        "assessment", "analysis/validation/experimental_independence.md",
        "section 4", "INFERRED", "medium",
        "p-values remain useful as descriptive contrasts; they are not "
        "design-based confirmatory tests.", "Use series-respecting permutation "
        "tests once the series assignment is confirmed.")
    add("Q3 condition comparability", "pressure_confounding",
        "All 9 records above 800 mmHg belong to a single mixture family "
        "(O2=0.21/N2=0.09/CO2=0.70/He=0); pressure and diluent effects are "
        "confounded in that region.",
        "recomputed from raw table", "analysis/validation/validation_checks.csv",
        "rows n_above_800_mmHg, families_above_800_mmHg", "VERIFIED", "high",
        "No independent pressure effect can be identified above 800 mmHg.",
        "Only within-family pressure variation can be examined; none exists "
        "for the high-pressure family in this table.")
    add("Q3 condition comparability", "fuel_overlap",
        "Fuels share 31 of 52 distinct mixture families (115 MeOH / 106 Hep "
        "records "
        "in shared families) and 14 of 15 O2 levels.",
        "recomputed from raw table", "analysis/validation/validation_checks.csv",
        "rows families_shared, records_in_shared_families_*", "VERIFIED", "high",
        "Overlap is partial; 15 MeOH-only and 6 Hep-only families mean "
        "overall fuel differences are also condition-confounded.",
        "Restrict fuel comparisons to shared families (done in Phase 2 "
        "condition analysis).")
    add("Q3 condition comparability", "diluent_substitution_cells",
        "Ten matched-O2 CO2/He substitution cells exist; of these, 5 have "
        "identical reported N2 balances on both sides and 7 have at least 3 "
        "records per side; only 4 cells (O2 = 0.16, 0.17, 0.18, 0.24) satisfy "
        "both conditions.",
        "recomputed from raw table + Phase 2 condition analysis",
        "analysis/validation/validation_checks.csv; "
        "analysis/exploratory/condition_analysis.csv",
        "F_diluent_substitution_cell rows and validation_checks rows "
        "diluent_cell_*, diluent_cells_n2_matched, "
        "diluent_cells_min_side_ge_3", "VERIFIED", "high",
        "O2 agreement alone does not make a cell matched; N2 balance and "
        "pressure-band comparability are evaluated separately.",
        "Treat only the 4 fully-defensible cells as candidate diluent "
        "contrasts.")
    add("Q4 telemetry", "telemetry_linkage",
        "Only 8 of 274 runs have per-run telemetry; all are 2009 ambient-air "
        "runs near 760 mmHg, so telemetry coverage is a biased subset.",
        "Phase 1 inventory + recomputation",
        "analysis/audit/dataset_inventory.md; analysis/validation/validation_checks.csv",
        "Phase 1 section 1.2; row n_telemetry_linked_runs", "VERIFIED", "high",
        "Time-resolved analyses are restricted to this subset.",
        "Obtain telemetry for the remaining runs or restrict time-resolved "
        "claims to the 8 runs.")
    add("Q4 telemetry", "clock_domains",
        "Telemetry files use at least six distinct clock/time columns (PIP, "
        "MAIN_COMPUTER GMT, RADIOMETER_100HZ_FRAME, FCU, IPSU1/2/4 camera "
        "clocks, image reference clock), with observed offsets of about 2.25 s "
        "between PIP and radiometer frames.",
        "telemetry headers (primary data)",
        "data/raw/flex/part-01/20CAL13_Radiometer_Readings.txt; "
        "20CAL13_Chamber_Readings.txt; 20CAL13*_Camera_Settings.txt",
        "time-stamp column headers; first two radiometer rows", "VERIFIED",
        "high", "No reconciliation map is available in the audited files; "
        "requirements specify GMT synchronisation to +/-0.03 s, but the "
        "observed files are not synchronised by default.",
        "Build and validate a clock-offset map before merging timelines.")
    add("Q4 telemetry", "image_archives",
        "23 zip archives contain TIFF (A/B series) and BMP (D series) frame "
        "sequences of 800-1290 frames each (~5.34 GB total), each with an "
        "embedded per-frame manifest .txt; 20CAL13A is absent and known FCI "
        "image frames are missing per its Readme.",
        "archive listing (read-only)",
        "data/raw/flex/part-01/*.zip; 20CAL13_Readme.txt",
        "zip directory listings (no extraction performed)", "VERIFIED", "high",
        "Formats and structure established; no image-derived measurement "
        "exists until frames are actually extracted and validated.",
        "Extract a single validated run as a pilot before any bulk work.")
    add("Q5 uncertainty", "pressure_uncertainty",
        "Spec-level pressure uncertainties: +/-0.01 atm (EIRD) and +/-0.05 atm "
        "(ERD) over 0.5-3 atm; chamber readings in telemetry are PSIA at ~1 Hz.",
        "requirements specification + telemetry header",
        "docs/flex/FLEX_EIRD_v4.pdf; docs/flex/FLEX Engineering Requirements "
        "Document.pdf; data/raw/flex/part-01/20CAL13_Chamber_Readings.txt",
        "EIRD 5.2.8; ERD 4.1.34; FCU TimeStamp column", "DOCUMENTED_BUT_UNCONFIRMED",
        "medium", "Specification tolerances, not calibration certificates; "
        "no uncertainty is attached to individual table pressure values.",
        "Obtain calibration records for the chamber pressure transducers.")
    add("Q5 uncertainty", "composition_uncertainty",
        "Spec-level composition tolerance: O2 initial charge +/-0.005 mole "
        "fraction; chamber purity requirements documented.",
        "requirements specification (documented)",
        "docs/flex/FLEX Engineering Requirements Document.pdf",
        "ERD 4.1.36; EIRD 5.1.x chamber purity", "DOCUMENTED_BUT_UNCONFIRMED",
        "medium", "Applies to the initial charge; 29 table records have "
        "reported sums != 1.000.", "Obtain charge verification logs.")
    add("Q2 experimental design", "fuel_contrast_counts",
        "Recorded outcome-label composition by fuel: Methanol 126 Extinction / "
        "23 Disruption / 8 Completion; Heptane 60 / 38 / 19 (Fisher outcome-vs-"
        "rest p = 5.16e-07 Extinction, 6.62e-04 Disruption, 3.46e-03 "
        "Completion; Holm-adjusted 1.55e-06 / 1.32e-03 / 3.46e-03).",
        "recomputed from raw table; arithmetic cross-checked against Phase 2 "
        "outputs", "analysis/validation/validation_checks.csv; "
        "analysis/exploratory/outcome_analysis.csv",
        "outcome_analysis.csv E_outcome and E_outcome_fuel_test rows",
        "VERIFIED", "high",
        "A property of the RECORDED LABELS only; labels are design-generated "
        "under the adaptive LOI procedure and 'Disruption' is undefined; this "
        "is not evidence about chemical extinction.",
        "None for the arithmetic; label definitions required before "
        "interpretation (see outcome-label evidence rows).")
    add("Q2 experimental design", "fuel_contrast_counts",
        "Measured burn durations differ by fuel (Methanol median 12.1 s, IQR "
        "7.85-17.90, n=155; Heptane median 7.5 s, IQR 3.30-11.25, n=111; "
        "Mann-Whitney U = 4838, p = 1.17e-09).",
        "recomputed from raw table; cross-checked against Phase 2 outputs",
        "analysis/validation/validation_checks.csv; "
        "analysis/exploratory/duration_analysis.csv",
        "duration_analysis.csv D_duration and D_duration_fuel_contrast rows",
        "VERIFIED", "high",
        "The count/statistic is verified; the INFERENCE is conditional on the "
        "independence assumption (adaptive series design) and on the "
        "undocumented start/stop definition of burn time.",
        "Series-respecting inference; burn-time event definition.")
    add("Q5 uncertainty", "flagged_records",
        "Anomalous records (0 mmHg pressure C11M201; eight 0-mm extinction "
        "diameters; one d_ext > d0) are retained everywhere with explicit "
        "flags and are excluded only in documented screened variants.",
        "Phase 1 audit + Phase 2 outputs", "analysis/audit/data_quality_report.md; "
        "analysis/exploratory/*_analysis.csv", "audit section 3; mode columns "
        "in Phase 2 CSVs", "VERIFIED", "high",
        "Whether these are placeholders or true values is unconfirmed; both "
        "as-reported and screened interpretations are preserved.",
        "Confirm with the data originator.")
    return E


def validation_matrix_rows():
    M = []
    def add(q, req, avail, status, blocker, conseq, action):
        M.append(OrderedDict(
            question=q, required_evidence=req, available_evidence=avail,
            validation_status=status, remaining_blocker=blocker,
            scientific_consequence=conseq, recommended_next_action=action))
    add("1. Initial diameter measurement validity",
        "documented measurement procedure, instrument, scale, uncertainty",
        "dispenser spec (+/-0.25 mm, +/-5%) and imaging spec (30 um, 30 fps); "
        "no per-run calibration", "SUPPORTED_BUT_CONDITIONAL",
        "per-run scale factor/calibration record",
        "diameter comparisons are usable descriptively; absolute mm-level "
        "modelling inputs carry unquantified bias",
        "obtain analyzed-data diameter series and scale factors")
    add("2. Extinction diameter measurement validity",
        "documented definition of the reduced value and its uncertainty",
        "image-derived per EIRD 5.2.1; table reduction undocumented; 8 zero-mm "
        "placeholders flagged", "SUPPORTED_BUT_CONDITIONAL",
        "reduction definition; placeholder confirmation",
        "'visible flame extinction diameter' is usable as labelled; it is not "
        "chemical extinction",
        "confirm reduction procedure and zero-value handling")
    add("3. Burning-rate unit validity",
        "documented unit and measurement equation for the table column",
        "none found in any inspected document; EIRD discusses mm2/s d2-law "
        "constants in a different (requirements) context",
        "BLOCKED - UNIT UNVERIFIED",
        "PSI data dictionary or originator definition",
        "no physically interpreted burning-rate quantity may be computed; all "
        "rate conclusions are provisional",
        "obtain the column definition before any modelling")
    add("4. Burn-duration measurement validity",
        "documented start/stop events and timing accuracy",
        "header verifies seconds; two approximate (~) values preserved; GMT "
        "sync spec +/-0.03 s exists", "SUPPORTED_BUT_CONDITIONAL",
        "start/stop event definitions per record type",
        "durations usable; sub-second precision cannot be assumed",
        "document start/stop events (ignition vs flame-out)")
    add("5. Pressure measurement validity",
        "unit verification (done) plus calibration evidence",
        "mmHg header verified; spec tolerances +/-0.01 atm (EIRD), +/-0.05 atm "
        "(ERD); one 0 mmHg anomaly", "SUPPORTED_BUT_CONDITIONAL",
        "calibration records; 0 mmHg record confirmation",
        "pressure usable as reported with one flagged anomaly",
        "obtain transducer calibration records")
    add("6. Composition measurement validity",
        "verification of reported mole fractions against charge records",
        "spec tolerance +/-0.005 O2; 29 records reported sums != 1.000 "
        "(never renormalised)", "SUPPORTED_BUT_CONDITIONAL",
        "charge verification logs",
        "mixture-family comparisons usable; sums must not be forced to unity",
        "obtain charge logs")
    add("7. Outcome-label interpretation",
        "operational definitions of Extinction/Disruption/Completion",
        "Test Plan LOI procedure documents Extinction/Completion context; "
        "'Disruption' undefined in all inspected documents",
        "BLOCKED (Disruption) / CONDITIONAL (Extinction, Completion)",
        "definition of 'Disruption'",
        "three-category outcome analyses carry an undefined category; labels "
        "are never equated with chemical extinction",
        "obtain label definitions from the investigation team")
    add("8. Fuel-comparison validity",
        "overlapping conditions, independence, adequate cell sizes",
        "31/52 shared families (115 MeOH/106 Hep); 14/15 shared O2 levels; "
        "adaptive series design; 193F001 collision disclosed. Underlying "
        "counts/statistics VERIFIED (EV-026, EV-027)",
        "EXPLORATORY_ONLY (comparative/causal claims); underlying statistics "
        "VERIFIED",
        "series-respecting inference; identifier resolution",
        "fuel contrasts are descriptive associations, not causal effects; "
        "initial-diameter contrast is duplicate-sensitive (p 0.0623->0.0449)",
        "report shared-family-restricted contrasts only")
    add("9. CO2/He comparison validity",
        "matched O2, matched N2 balance, shared pressure bands, adequate n",
        "10 matched-O2 cells; 5 with identical N2 balances; 7 with both sides "
        "n>=3; 4 cells (O2=0.16, 0.17, 0.18, 0.24) satisfy both",
        "SUPPORTED_BUT_CONDITIONAL (4 cells)",
        "per-cell adequacy enforcement (done in Phase 2); N2 matching",
        "only the 4 fully-defensible cells support diluent contrasts; no "
        "pooled causal estimate",
        "restrict contrasts to the 4 cells; report per-cell")
    add("10. Pressure-effect identifiability",
        "pressure variation within a fixed mixture family",
        "all 9 records >800 mmHg in one CO2 family; no within-family "
        "cross-band variation for that family", "BLOCKED",
        "high-pressure runs in other mixture families",
        "no independently identified pressure effect can be claimed",
        "obtain high-pressure data across families")
    add("11. Experimental independence",
        "evidence that records are independent experimental observations",
        "adaptive sequential LOI design (documented); up to 9 records/date; "
        "81 series prefixes; identifier collision", "BLOCKED (for design-based "
        "inference)",
        "series/run structure metadata; identifier resolution",
        "all Phase 2 p-values are conditional on an independence assumption "
        "that available evidence does not support",
        "series-stratified or permutation-based inference; metadata request")
    add("12. Telemetry synchronization",
        "clock-offset map across the six observed clock domains",
        "headers identify six clocks; PIP-vs-radiometer offset measured "
        "across one file spans 2.1-2.5 s (~2.3 s in the first rows) "
        "observed; GMT +/-0.03 s requirement documented", "BLOCKED (for merged "
        "timelines)",
        "validated clock-offset map",
        "no merged time-resolved product is defensible yet",
        "build and validate the clock map on one pilot run")
    add("13. Image archive usability",
        "extraction, format validation, run linkage, timestamps",
        "23 archives (TIFF/BMP, 800-1290 frames) with embedded manifests; "
        "20CAL13A absent; known missing frames documented", "SUPPORTED_BUT_CONDITIONAL",
        "pilot extraction and validation",
        "image-derived measurements do not exist yet and must not be claimed",
        "pilot-extract one run; validate against manifests")
    add("14. d2-law readiness",
        "unit-resolved burning rate + diameter time series + conditions",
        "burning-rate unit unverified; no diameter time series in audited "
        "data (only in unextracted archives)", "BLOCKED",
        "items 3 and 13 above",
        "no d2-law constant, evaporation constant or regression rate may be "
        "computed",
        "resolve unit and extract pilot images first")
    add("15. Chemical-extinction identifiability",
        "radical/emission or gas-phase composition measurements at flame-out",
        "none in audited data; OH* imaging exists only as unextracted camera "
        "archives for 8 runs", "BLOCKED",
        "extraction of OH* series + species measurements",
        "visible flame extinction must not be equated with chemical extinction",
        "validate OH*/LLLUV frames against the visible-flame label")
    return M


def validation_checks_rows(records, stats):
    rows = []
    for k, v in stats.items():
        rows.append(OrderedDict(quantity=k, value=json.dumps(v)
                                if isinstance(v, (dict, list, tuple)) else v,
                                source="independent recomputation by "
                                       "run_validation.py from "
                                       "data/raw/flex/PSI-69_Experimental "
                                       "table_FLEX.csv"))
    # diluent cell audit (condition_comparability.md cites these)
    by_o2 = {}
    for r in records:
        dt = "CO2" if r["co2_mf"] else ("He" if r["he_mf"] else None)
        if dt:
            by_o2.setdefault(r["o2_mf"], {}).setdefault(dt, []).append(r)
    n_matched = 0
    n_n2_matched = 0
    n_adequate = 0
    for o2, kinds in sorted(by_o2.items()):
        if "CO2" in kinds and "He" in kinds:
            n_matched += 1
            n2c = {r["n2_mf"] for r in kinds["CO2"]}
            n2h = {r["n2_mf"] for r in kinds["He"]}
            if n2c == n2h:
                n_n2_matched += 1
            if len(kinds["CO2"]) >= 3 and len(kinds["He"]) >= 3:
                n_adequate += 1
            rows.append(OrderedDict(
                quantity=f"diluent_cell_O2_{o2}",
                value=json.dumps({
                    "n_co2": len(kinds["CO2"]), "n_he": len(kinds["He"]),
                    "n2_co2": sorted(n2c), "n2_he": sorted(n2h),
                    "co2_bands": sorted({pressure_band(r["pressure_mmHg"])
                                         for r in kinds["CO2"]}),
                    "he_bands": sorted({pressure_band(r["pressure_mmHg"])
                                        for r in kinds["He"]})}),
                source="independent recomputation"))
    rows.append(OrderedDict(quantity="diluent_cells_matched_total",
                            value=n_matched, source="independent recomputation"))
    rows.append(OrderedDict(quantity="diluent_cells_n2_matched",
                            value=n_n2_matched, source="independent recomputation"))
    rows.append(OrderedDict(quantity="diluent_cells_min_side_ge_3",
                            value=n_adequate, source="independent recomputation"))
    # duplicate sensitivity (independent recomputation of the Phase 2 numbers)
    def mwu_p(keep, key):
        x = [r[key] for r in keep if r["fuel"] == "Methanol" and r[key] is not None]
        y = [r[key] for r in keep if r["fuel"] == "Heptane" and r[key] is not None]
        # exact permutation p is unnecessary: recompute the same asymptotic
        # statistic to confirm the delivered sensitivity values
        import math
        allv = sorted(x + y)
        ranks = {}
        i = 0
        while i < len(allv):
            j = i
            while j + 1 < len(allv) and allv[j + 1] == allv[i]:
                j += 1
            avg = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                ranks[allv[k]] = avg
            i = j + 1
        rx = sum(ranks[v] for v in x)
        nx, ny = len(x), len(y)
        ux = rx - nx * (nx + 1) / 2.0
        u = min(ux, nx * ny - ux)
        mu = nx * ny / 2.0
        # ties correction
        tie = 0
        i = 0
        while i < len(allv):
            j = i
            while j + 1 < len(allv) and allv[j + 1] == allv[i]:
                j += 1
            t = j - i + 1
            tie += t ** 3 - t
            i = j + 1
        n = nx + ny
        sig2 = (nx * ny / 12.0) * ((n + 1) - tie / (n * (n - 1.0)))
        z = (u - mu + 0.5) / math.sqrt(sig2)
        return u, math.erfc(abs(z) / math.sqrt(2.0))
    coll = [r for r in records if r["flex_identifier"] == "193F001"]
    for i, dropped in enumerate(coll, 1):
        keep = [r for r in records if r is not dropped]
        u0, p0 = mwu_p(records, "d0_mm")
        u1, p1 = mwu_p(keep, "d0_mm")
        rows.append(OrderedDict(
            quantity=f"duplicate_sensitivity_d0_excluding_record_{i}",
            value=json.dumps({"U": u0, "p_as_reported": round(p0, 5),
                              "U_excluded": u1, "p_excluded": round(p1, 5)}),
            source="independent recomputation"))
    return rows


def main():
    # ---- integrity gate ------------------------------------------------------
    integrity = []
    ok = True
    for rel in PROTECTED:
        try:
            digest = sha256_of(rel)
        except FileNotFoundError:
            integrity.append(dict(file=rel, status="MISSING", sha256=""))
            ok = False
            continue
        expected = EXPECTED_PROTECTED_SHA256.get(rel)
        status = "MATCH" if (expected is None or digest == expected) else \
            ("MATCH" if expected is None else "CHANGED")
        if expected is not None and digest != expected:
            status = "CHANGED"
            ok = False
        integrity.append(dict(file=rel, status=status, sha256=digest))
    if not ok:
        changed = [i["file"] for i in integrity if i["status"] == "CHANGED"]
        raise SystemExit(f"PROTECTED FILE CHANGED: {changed}. Phase 3 refuses "
                         "to run against modified frozen artifacts.")
    print(f"[integrity] {len(integrity)} protected files verified unchanged")

    # ---- data + recomputation ------------------------------------------------
    records = load_records()
    stats = recompute(records)
    print(f"[data] {stats['n_records']} records loaded "
          f"(MeOH {stats['n_methanol']}, Hep {stats['n_heptane']})")

    write_csv(os.path.join(HERE, "validation_checks.csv"),
              validation_checks_rows(records, stats))
    print("[csv] validation_checks.csv")

    write_csv(os.path.join(HERE, "evidence_register.csv"), evidence_rows())
    print(f"[csv] evidence_register.csv ({len(evidence_rows())} rows)")

    write_csv(os.path.join(HERE, "validation_matrix.csv"), validation_matrix_rows())
    print(f"[csv] validation_matrix.csv ({len(validation_matrix_rows())} rows)")

    # ---- manifest -------------------------------------------------------------
    import matplotlib
    outputs = {}
    for name in ("validation_checks.csv", "evidence_register.csv",
                 "validation_matrix.csv"):
        outputs[name] = dict(sha256=sha256_of(os.path.join("analysis", "validation", name)),
                             rows=sum(1 for _ in open(os.path.join(HERE, name))) - 1)
    manifest = OrderedDict(
        analysis="FLEX PSI-69 Phase 3 scientific validation",
        script=dict(name="run_validation.py", version="3.0.0",
                    entrypoint="notebooks/.venv/bin/python "
                               "analysis/validation/run_validation.py"),
        executed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(),
                         platform=platform.platform(),
                         numpy=np.__version__, matplotlib=matplotlib.__version__),
        inputs=[dict(path="data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                     sha256=EXPECTED_PROTECTED_SHA256[
                         "data/raw/flex/PSI-69_Experimental table_FLEX.csv"],
                     records=stats["n_records"],
                     encoding="latin-1 byte-preserving; 0x96 = missing marker")],
        documents_inspected=[
            "docs/flex/FLEX_EIRD_v4.pdf", "docs/flex/FLEX_Test_Plan.pdf",
            "docs/flex/FLEX Engineering Requirements Document.pdf",
            "docs/flex/FLEX DoD.docx", "docs/flex/FLEX Overall Ext File-2.pdf",
            "docs/flex/i_Investigation.txt", "schema/v1.2.0.sql",
            "data/raw/flex/part-01/* (8 runs telemetry)",
            "data/raw/flex/part-01/*.zip (archive listings)",
            "analysis/audit/*", "analysis/exploratory/*",
        ],
        integrity=dict(protected_files=len(integrity),
                       unchanged=sum(1 for i in integrity if i["status"] == "MATCH"),
                       changed=[i["file"] for i in integrity if i["status"] == "CHANGED"]),
        recomputed=stats, outputs=outputs,
        restrictions=dict(
            modelling="none performed - no d2-law, no constants, no ML",
            unit_assignment="none - burning-rate unit remains UNVERIFIED",
            imputation="none", renormalisation="none",
            chemical_extinction="not claimed anywhere"),
        limitations=[
            "All documentary evidence is specification-level (requirements "
            "documents), not calibration or verification records.",
            "The PSI-69 table provenance lacks a DOI/version reference.",
            "Outcome label 'Disruption' is undocumented in inspected sources.",
            "Per-run temperature, gravity, fiber usage and gas-charge "
            "verification are unavailable for 266 of 274 records.",
            "Clock offsets are observed but not reconciled; no merged "
            "timeline is produced.",
            "Image archives were listed, not extracted; no image-derived "
            "measurement is claimed.",
        ])
    with open(os.path.join(HERE, "run_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("[manifest] run_manifest.json")


if __name__ == "__main__":
    main()
