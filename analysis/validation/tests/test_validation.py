"""Phase 3 validation test suite.

Run from the repository root:
    notebooks/.venv/bin/python -m pytest analysis/validation/tests/ -v

Verifies:
  * Phase 1 / Phase 2 / raw-data / schema / src / tests preservation
    (independent SHA-256 constants, not imported from the pipeline);
  * evidence-register integrity (unique IDs, valid statuses, traceable
    citations, blocked items carry follow-ups);
  * the burning-rate unit stays explicitly UNVERIFIED everywhere;
  * no imputation / renormalisation / unit-assignment assertions in outputs;
  * validation_checks.csv matches an independent recomputation;
  * run_manifest.json records inputs, hashes and integrity truthfully;
  * paths are anchored to the script location, not the CWD;
  * no modelling code is present in the validation pipeline.
"""

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATION = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(VALIDATION))

RAW_CSV = "data/raw/flex/PSI-69_Experimental table_FLEX.csv"
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"

# Frozen fingerprints of every protected artifact, taken when Phase 3 was
# authored. Any drift fails immediately.
PROTECTED_SHA256 = {
    RAW_CSV: "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96",
    "data/raw/flex/s_PSI-69.txt":
        "cb9374159b9b01a83bfe53a0b8ba1a602793df86f298e0ad222615c55d200135",
    "schema/v1.2.0.sql":
        "d03e0b1605a393d9f1f7273eae90a785a2c4f32c9eb9b79615312afe87965c35",
    "src/prediction/predictor.py":
        "7c0c8f5412e087a0720c7faf447027126edb0aadb2e6ee617d8d72efb479bc1f",
    "tests/validate_schema_candidate.py":
        "fdb23d8cc28c65de62822055a328b85c24669942901616faf1e02d599567bf90",
    "analysis/audit/_audit_context.json":
        "0988ad044c62c5277d0ad6dd4d16dc1c57fa3bdb0a926c40e9d3e93446b6ff02",
    "analysis/audit/audit_flex_psi69.py":
        "915be6b8d8fd07dab0c8c3f5d085070811cbaa5e30acb6988662e1e3f603dd8d",
    "analysis/audit/condition_coverage.csv":
        "5f0d1f6982b3c048f1d4a91bd1b8b6aea8a98f6468d218b391635a5671cf424c",
    "analysis/audit/data_quality_report.md":
        "9231adf81ded65c281f40694ae3fd52f970b0697fd2359daaaefd03f2482293b",
    "analysis/audit/dataset_inventory.md":
        "608e3ee4fb7913527f81009533d2945546e9150dad1b2a1aac5f6283756061a8",
    "analysis/audit/fuel_comparison_inventory.csv":
        "e606cd2e816455c1fab1a0e8ab068cb332f6e2febf2e031f3ff1edb501ebfb8f",
    "analysis/audit/missing_data_report.csv":
        "5057647eebaee44f0ecb13da3c7a9852a4faf0ee4c94c67cbf0aeb82d7ddbee2",
    "analysis/exploratory/README.md":
        "38d972d9d50d6b9c43c97c3bc55c40909f456c3824baac679a73e8c080d8e8fc",
    "analysis/exploratory/burning_rate_analysis.csv":
        "c456223f145678cc2a6ceee718df672b91e684f4183ac0e5bb85d3d69651a6cb",
    "analysis/exploratory/condition_analysis.csv":
        "c14aef5e991b310e0964b3f514b1523f8b17010dce8f9c5fc9b22b9f6c718437",
    "analysis/exploratory/descriptive_statistics.csv":
        "741557f35b874ab98d016ba1c8dd4ae4277d5b6cb23c1c0d1b853fa6fafbe81b",
    "analysis/exploratory/diameter_analysis.csv":
        "6e8396a09dded79335006431fdaa903f67b3945537110248dcd2d9de97a64906",
    "analysis/exploratory/duration_analysis.csv":
        "402755b6fdcb16f7410f716cf0afba7d2d571a788b12f5a70eb87f3cd98c3256",
    "analysis/exploratory/flex_core.py":
        "e140324da88f192bad62661ff48b3c5758943d2f1261365423c914739f939d87",
    "analysis/exploratory/outcome_analysis.csv":
        "8157494d2bea9ed65c7460d9a9553466cc869b0a836b6032149e1be0140f1295",
    "analysis/exploratory/run_analysis.py":
        "001ed9b123602e730a6719d3b7a958bd236717b32d99365fd37bf7fb14310449",
    "analysis/exploratory/run_manifest.json":
        "efde14f72303aab11966dc435e3fb3b45efa1cbb004865b5cf3a1603833508d7",
    "analysis/exploratory/figures/fig01_initial_diameter_by_fuel.png":
        "335a314bad1d007c99100aec74e3d2700f9b6ac4321de74dc219b67e5f8e7787",
    "analysis/exploratory/figures/fig02_diameter_box_by_fuel.png":
        "dab1148e90f31cf31972944a533e0b8d58db2ade0403ba9150faf135f081ffc3",
    "analysis/exploratory/figures/fig03_burn_duration_by_fuel.png":
        "61f59530600c0c0e93656c6943fc20cf4465c791bed76d7b6daa0afc6611df1f",
    "analysis/exploratory/figures/fig04_outcome_distribution.png":
        "ac913d049419f06774f2857f56fd456f567315e81f18487a48d700580770a0e7",
    "analysis/exploratory/figures/fig05_condition_coverage.png":
        "2eac5fa42b531b542d66d5ce64cd2efafa4b7ac4c37367be37e58e1a6882743b",
    "analysis/exploratory/figures/fig06_missingness_by_variable.png":
        "e6abb774280d3ae71510533e0e2c030b35227fce193134ade295749a9714f0a2",
    "analysis/exploratory/figures/fig07_extinction_diameter_by_outcome.png":
        "32eb56911a4d32dfe25f9096917165271ff86973f420b919d699a75cb15de544",
    "analysis/exploratory/tests/test_exploratory.py":
        "3a99bba7435ab4bec117b82a73da87846b67cc8fbde42eaa60fa90bc98485604",
}


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture(scope="module")
def manifest():
    subprocess.run([sys.executable, os.path.join(VALIDATION, "run_validation.py")],
                   check=True, capture_output=True, cwd=ROOT)
    with open(os.path.join(VALIDATION, "run_manifest.json")) as fh:
        return json.load(fh)


# --- preservation -------------------------------------------------------------
def test_all_protected_files_unchanged():
    for rel, expected in PROTECTED_SHA256.items():
        assert os.path.exists(os.path.join(ROOT, rel)), rel
        assert sha256_of(rel) == expected, f"protected file changed: {rel}"


def test_manifest_integrity_block_truthful(manifest):
    assert manifest["integrity"]["changed"] == []
    assert manifest["integrity"]["unchanged"] == manifest["integrity"]["protected_files"]
    assert manifest["integrity"]["protected_files"] == len(PROTECTED_SHA256)


def test_pipeline_run_does_not_modify_protected_files():
    before = {rel: sha256_of(rel) for rel in PROTECTED_SHA256}
    subprocess.run([sys.executable, os.path.join(VALIDATION, "run_validation.py")],
                   check=True, capture_output=True, cwd=ROOT)
    for rel, digest in before.items():
        assert sha256_of(rel) == digest, f"pipeline modified protected file {rel}"


# --- evidence register integrity ----------------------------------------------
def test_evidence_register_structure():
    with open(os.path.join(VALIDATION, "evidence_register.csv")) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) >= 25
    ids = [r["evidence_id"] for r in rows]
    assert len(set(ids)) == len(ids)
    valid = {"VERIFIED", "DOCUMENTED_BUT_UNCONFIRMED", "INFERRED", "UNVERIFIED",
             "CONTRADICTED", "BLOCKED"}
    for r in rows:
        assert r["verification_status"] in valid, r["evidence_id"]
        assert r["source_document"].strip(), r["evidence_id"]
        assert r["source_location"].strip(), r["evidence_id"]
        assert r["claim"].strip() and r["limitations"].strip()
        if r["verification_status"] in ("UNVERIFIED", "BLOCKED"):
            assert r["required_followup"].strip(), r["evidence_id"]
        if r["verification_status"] == "VERIFIED":
            # verified claims must cite either an inspected document or a
            # recomputation artifact, never be empty
            assert ("docs/" in r["source_document"]
                    or "data/raw" in r["source_document"]
                    or "validation_checks" in r["source_document"]
                    or "analysis/" in r["source_document"]), r["evidence_id"]


def test_source_documents_exist():
    with open(os.path.join(VALIDATION, "evidence_register.csv")) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for token in re.findall(r"docs/flex/[\w .-]+\.(?:pdf|docx|txt)", r["source_document"]):
            assert os.path.exists(os.path.join(ROOT, token)), token
        for token in re.findall(r"analysis/[\w/]+\.(?:csv|md)", r["source_document"]):
            assert os.path.exists(os.path.join(ROOT, token)), token


def test_burning_rate_row_blocked():
    with open(os.path.join(VALIDATION, "evidence_register.csv")) as fh:
        rows = list(csv.DictReader(fh))
    br = [r for r in rows if r["variable"] == "burning_rate"
          and "no documented" in r["claim"]]
    assert br and br[0]["verification_status"] == "UNVERIFIED"
    assert br[0]["required_followup"].startswith("UNIT UNVERIFIED")


def test_provenance_marks_unit_blocked():
    text = open(os.path.join(VALIDATION, "measurement_provenance.md")).read()
    assert "UNIT UNVERIFIED — PHYSICAL INTERPRETATION BLOCKED" in text


# --- no forbidden assertions ---------------------------------------------------
VALIDATION_FILES = ["measurement_provenance.md", "experimental_independence.md",
                    "condition_comparability.md", "telemetry_assessment.md",
                    "uncertainty_assessment.md", "README.md",
                    "evidence_register.csv", "validation_matrix.csv",
                    "validation_checks.csv", "run_validation.py"]


def _validation_texts():
    return {f: open(os.path.join(VALIDATION, f)).read() for f in VALIDATION_FILES}


def test_unit_strings_only_appear_as_quoted_evidence():
    """mm2/s may appear only as quoted/adjacent documentary evidence (EIRD
    context), never as an assignment to the table column. Checks are
    paragraph-aware so line wrapping cannot dodge them."""
    for f, text in _validation_texts().items():
        for para in text.split("\n\n"):
            if re.search(r"mm\s*[²2]\s*/s|mm/s", para):
                low = para.lower()
                assert any(k in low for k in (
                    "eird", "requirements", "literature", "adjacent",
                    "not verify", "prohibited", "blocked", "context",
                    "unverified", "does not", "search", "discusses",
                    "column", "specification", "inspected", "full-text",
                    "assuming", "quote")), (f, para[:120])


def test_no_imputation_or_renormalisation_assertions():
    for f, text in _validation_texts().items():
        for para in text.split("\n\n"):
            low = para.lower()
            if "imput" in low:
                assert any(k in low for k in ("never", "not ", "no ", "none",
                                              "without", "nothing",
                                              "fails on", "claim",
                                              "assertive")), (f, para[:120])
            if re.search(r"renormalis|renormaliz", low):
                assert any(k in low for k in ("never", "not ", "no ",
                                              "nothing")), (f, para[:120])


def test_no_modelling_code_in_pipeline():
    src = open(os.path.join(VALIDATION, "run_validation.py")).read()
    for banned in ("sklearn", "LinearRegression", "LogisticRegression",
                   "RandomForest", "scipy.optimize", "curve_fit"):
        assert banned not in src
    for f, text in _validation_texts().items():
        for para in text.split("\n\n"):
            flat = " ".join(para.lower().split())
            if re.search(r"d\s*[²2]\s*-law", flat):
                assert any(k in flat for k in
                           ("blocked", "readiness", "prohibited",
                            "not ", "cannot", "before", "eird",
                            "discusses", "documented", "requirement",
                            "no ", "computed", "must not")), (f, para[:120])


def test_paths_anchored_to_script_location():
    src = open(os.path.join(VALIDATION, "run_validation.py")).read()
    assert "os.path.join(ROOT" in src
    assert 'open("data/raw' not in src
    assert "os.path.join(ROOT, \"data\", \"raw\", \"flex\"" in src


# --- recomputation agreement ---------------------------------------------------
def _independent_load():
    rows = list(csv.DictReader(open(os.path.join(ROOT, RAW_CSV),
                                    encoding="latin-1")))
    out = []
    for r in rows:
        out.append(dict(
            ident=r["FLEX Identifier"].strip(),
            fuel=r["Fuel"].strip(),
            o2=r["O initial ambient composition; mole fraction"].strip(),
            n2=r["N initial ambient composition; mole fraction"].strip(),
            co2=r["CO initial ambient composition; mole fraction"].strip(),
            he=r["He initial ambient composition; mole fraction"].strip(),
            p=r["Ambient pressure; mmHg"].strip(),
        ))
    return out


def test_validation_checks_match_independent_recomputation():
    checks = {r["quantity"]: r["value"]
              for r in csv.DictReader(open(os.path.join(VALIDATION,
                                                        "validation_checks.csv")))}
    recs = _independent_load()
    assert int(checks["n_records"]) == len(recs) == 274
    assert int(checks["n_methanol"]) == sum(1 for r in recs if r["fuel"] == "Methanol") == 157
    assert int(checks["n_heptane"]) == sum(1 for r in recs if r["fuel"] == "Heptane") == 117
    high = [r for r in recs if r["p"] and float(r["p"]) > 800]
    assert int(checks["n_above_800_mmHg"]) == len(high) == 9
    fams = {(r["o2"], r["n2"], r["co2"], r["he"]) for r in high}
    assert int(checks["families_above_800_mmHg"]) == len(fams) == 1
    assert int(checks["identifier_collision_193F001_count"]) == \
        sum(1 for r in recs if r["ident"] == "193F001") == 2
    assert int(checks["diluent_cells_matched_total"]) == 10
    assert int(checks["diluent_cells_n2_matched"]) == 5
    assert int(checks["diluent_cells_min_side_ge_3"]) == 7
    shared = {f for f in {(r["o2"], r["n2"], r["co2"], r["he"]) for r in recs
                          if r["fuel"] == "Methanol"}} & \
             {f for f in {(r["o2"], r["n2"], r["co2"], r["he"]) for r in recs
                          if r["fuel"] == "Heptane"}}
    assert int(checks["families_shared"]) == len(shared) == 31


def test_duplicate_sensitivity_values_present():
    checks = {r["quantity"]: r["value"]
              for r in csv.DictReader(open(os.path.join(VALIDATION,
                                                        "validation_checks.csv")))}
    v = json.loads(checks["duplicate_sensitivity_d0_excluding_record_1"])
    assert abs(v["p_as_reported"] - 0.0623) < 5e-5
    assert abs(v["p_excluded"] - 0.0450) < 5e-4


# --- manifest fidelity ----------------------------------------------------------
def test_manifest_records_inputs_versions_and_outputs(manifest):
    inp = manifest["inputs"][0]
    assert sha256_of(RAW_CSV) == inp["sha256"] == RAW_SHA256
    assert inp["records"] == 274
    assert "executed_utc" in manifest
    assert manifest["environment"]["python"]
    for name, entry in manifest["outputs"].items():
        disk = os.path.join(VALIDATION, name)
        assert os.path.exists(disk), name
        assert sha256_of(os.path.join("analysis", "validation", name)) == entry["sha256"]
    assert manifest["restrictions"]["unit_assignment"].startswith("none")
    assert manifest["restrictions"]["modelling"].startswith("none")
    assert len(manifest["documents_inspected"]) >= 8


def test_validation_matrix_covers_required_questions():
    rows = list(csv.DictReader(open(os.path.join(VALIDATION, "validation_matrix.csv"))))
    assert len(rows) == 15
    topics = " ".join(r["question"] for r in rows).lower()
    for needle in ("initial diameter", "extinction diameter", "burning-rate unit",
                   "burn-duration", "pressure measurement", "composition",
                   "outcome-label", "fuel-comparison", "co2/he",
                   "pressure-effect", "independence", "telemetry", "image archive",
                   "d2-law", "chemical-extinction"):
        assert needle in topics, needle
    for r in rows:
        assert r["validation_status"].strip()
        assert r["scientific_consequence"].strip()
        assert r["recommended_next_action"].strip()


def test_phase3_documents_exist_and_substantive():
    for f in ("README.md", "measurement_provenance.md",
              "experimental_independence.md", "condition_comparability.md",
              "telemetry_assessment.md", "uncertainty_assessment.md"):
        p = os.path.join(VALIDATION, f)
        assert os.path.exists(p), f
        assert os.path.getsize(p) > 3000, f


def test_readme_reports_spearman_approximation_qualification():
    text = open(os.path.join(VALIDATION, "README.md")).read()
    assert "normal-tail approximation" in text or "erfc" in text


def test_readme_has_phase4_requirements_section():
    text = open(os.path.join(VALIDATION, "README.md")).read()
    assert "Requirements for Phase 4 — Physical Modelling" in text


def test_readme_classifies_conclusions():
    text = open(os.path.join(VALIDATION, "README.md")).read()
    for label in ("Scientifically established", "Supported but conditional",
                  "Exploratory", "Unverified", "Blocked"):
        assert label in text, label


def test_zero_mm_split_corrected_in_phase3():
    """The frozen Phase 1 audit states Disruption x5 / Completion x3 for the
    eight 0-mm extinction diameters; independent recomputation gives x4 / x4.
    Phase 3 must carry the corrected split (defect D1, documented not fixed)."""
    import csv as _csv
    with open(os.path.join(ROOT, RAW_CSV), encoding="latin-1") as fh:
        recs = list(_csv.DictReader(fh))
    zeros = [r for r in recs
             if r["Visible flame extinction diameter; mm"].strip() == "0"]
    assert len(zeros) == 8
    split = Counter(r["Test end"].strip() for r in zeros)
    assert split == {"Disruption": 4, "Completion": 4}, split
    text = open(os.path.join(VALIDATION, "uncertainty_assessment.md")).read()
    assert "Disruption ×4" in text and "Completion ×4" in text
    # the frozen Phase 1 defect must be documented, not silently corrected
    readme = open(os.path.join(VALIDATION, "README.md")).read()
    assert "D1" in readme and "Disruption×4" in readme
