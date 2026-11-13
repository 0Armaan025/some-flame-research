"""Phase 3.5 evidence-resolution test suite.

Run from the repository root:
    notebooks/.venv/bin/python -m pytest analysis/evidence_resolution/tests/ -v

Verifies preservation of all prior phases, the traceability of every evidence
citation, valid classifications, no forbidden inferences (unit assignment,
imputation, modelling), reproducibility of the pipeline outputs, and the
specific forensic results (zero-mm split, clock facts, archive census,
duplicate sensitivity).
"""

import csv
import hashlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(ER))

RAW_CSV = "data/raw/flex/PSI-69_Experimental table_FLEX.csv"
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"

# Every protected artifact from all prior phases: raw, schema, src, tests,
# Phase 1 (7), Phase 2 (25), Phase 3 (12).
PROTECTED = sorted(
    ["data/raw/flex/PSI-69_Experimental table_FLEX.csv",
     "data/raw/flex/s_PSI-69.txt",
     "schema/v1.2.0.sql",
     "src/prediction/predictor.py",
     "tests/validate_schema_candidate.py"]
    + [os.path.relpath(os.path.join(d, f), ROOT)
       for base in ("audit", "exploratory", "validation")
       for d, _, fs in sorted(os.walk(os.path.join(ROOT, "analysis", base)))
       for f in sorted(fs)
       if "__pycache__" not in d and not f.startswith(".")]
)

# Frozen SHA-256 fingerprints of every hashable protected file, taken when Phase
# 3.5 was authored (Phases 1-2 inherited from the Phase 3 freeze; Phase 3
# re-taken after its review cycle). The only comparison that is not a plain
# digest is analysis/validation/run_manifest.json below: Phase 3's own suite
# regenerates its executed_utc, so that field is normalised out.
PROTECTED_SHA256 = {
    "analysis/audit/_audit_context.json": "0988ad044c62c5277d0ad6dd4d16dc1c57fa3bdb0a926c40e9d3e93446b6ff02",
    "analysis/audit/audit_flex_psi69.py": "915be6b8d8fd07dab0c8c3f5d085070811cbaa5e30acb6988662e1e3f603dd8d",
    "analysis/audit/condition_coverage.csv": "5f0d1f6982b3c048f1d4a91bd1b8b6aea8a98f6468d218b391635a5671cf424c",
    "analysis/audit/data_quality_report.md": "9231adf81ded65c281f40694ae3fd52f970b0697fd2359daaaefd03f2482293b",
    "analysis/audit/dataset_inventory.md": "608e3ee4fb7913527f81009533d2945546e9150dad1b2a1aac5f6283756061a8",
    "analysis/audit/fuel_comparison_inventory.csv": "e606cd2e816455c1fab1a0e8ab068cb332f6e2febf2e031f3ff1edb501ebfb8f",
    "analysis/audit/missing_data_report.csv": "5057647eebaee44f0ecb13da3c7a9852a4faf0ee4c94c67cbf0aeb82d7ddbee2",
    "analysis/exploratory/README.md": "38d972d9d50d6b9c43c97c3bc55c40909f456c3824baac679a73e8c080d8e8fc",
    "analysis/exploratory/burning_rate_analysis.csv": "c456223f145678cc2a6ceee718df672b91e684f4183ac0e5bb85d3d69651a6cb",
    "analysis/exploratory/condition_analysis.csv": "c14aef5e991b310e0964b3f514b1523f8b17010dce8f9c5fc9b22b9f6c718437",
    "analysis/exploratory/descriptive_statistics.csv": "741557f35b874ab98d016ba1c8dd4ae4277d5b6cb23c1c0d1b853fa6fafbe81b",
    "analysis/exploratory/diameter_analysis.csv": "6e8396a09dded79335006431fdaa903f67b3945537110248dcd2d9de97a64906",
    "analysis/exploratory/duration_analysis.csv": "402755b6fdcb16f7410f716cf0afba7d2d571a788b12f5a70eb87f3cd98c3256",
    "analysis/exploratory/figures/fig01_initial_diameter_by_fuel.png": "335a314bad1d007c99100aec74e3d2700f9b6ac4321de74dc219b67e5f8e7787",
    "analysis/exploratory/figures/fig02_diameter_box_by_fuel.png": "dab1148e90f31cf31972944a533e0b8d58db2ade0403ba9150faf135f081ffc3",
    "analysis/exploratory/figures/fig03_burn_duration_by_fuel.png": "61f59530600c0c0e93656c6943fc20cf4465c791bed76d7b6daa0afc6611df1f",
    "analysis/exploratory/figures/fig04_outcome_distribution.png": "ac913d049419f06774f2857f56fd456f567315e81f18487a48d700580770a0e7",
    "analysis/exploratory/figures/fig05_condition_coverage.png": "2eac5fa42b531b542d66d5ce64cd2efafa4b7ac4c37367be37e58e1a6882743b",
    "analysis/exploratory/figures/fig06_missingness_by_variable.png": "e6abb774280d3ae71510533e0e2c030b35227fce193134ade295749a9714f0a2",
    "analysis/exploratory/figures/fig07_extinction_diameter_by_outcome.png": "32eb56911a4d32dfe25f9096917165271ff86973f420b919d699a75cb15de544",
    "analysis/exploratory/flex_core.py": "e140324da88f192bad62661ff48b3c5758943d2f1261365423c914739f939d87",
    "analysis/exploratory/outcome_analysis.csv": "8157494d2bea9ed65c7460d9a9553466cc869b0a836b6032149e1be0140f1295",
    "analysis/exploratory/run_analysis.py": "001ed9b123602e730a6719d3b7a958bd236717b32d99365fd37bf7fb14310449",
    "analysis/exploratory/run_manifest.json": "efde14f72303aab11966dc435e3fb3b45efa1cbb004865b5cf3a1603833508d7",
    "analysis/exploratory/tests/test_exploratory.py": "3a99bba7435ab4bec117b82a73da87846b67cc8fbde42eaa60fa90bc98485604",
    "data/raw/flex/PSI-69_Experimental table_FLEX.csv": "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96",
    "data/raw/flex/s_PSI-69.txt": "cb9374159b9b01a83bfe53a0b8ba1a602793df86f298e0ad222615c55d200135",
    "schema/v1.2.0.sql": "d03e0b1605a393d9f1f7273eae90a785a2c4f32c9eb9b79615312afe87965c35",
    "src/prediction/predictor.py": "7c0c8f5412e087a0720c7faf447027126edb0aadb2e6ee617d8d72efb479bc1f",
    "tests/validate_schema_candidate.py": "fdb23d8cc28c65de62822055a328b85c24669942901616faf1e02d599567bf90",
    "analysis/validation/README.md": "a7aa7d986c9d18098077f4383cb72bb9f26acde9f908aee50c0900e9692a9d31",
    "analysis/validation/condition_comparability.md": "8b293da6f4a5722504b14002cd8ebc342048eaaeffb29501aa7d56e809776823",
    "analysis/validation/evidence_register.csv": "10ab33b3cd7a9021302d96afbf592b62aa5bcfdf21301943c4014130cfcf09bb",
    "analysis/validation/experimental_independence.md": "8c8bf2f53f56cf8cd6faf205ea0e023738eea708591a015edc740659cbb32209",
    "analysis/validation/measurement_provenance.md": "48b40e339865c86e25491787a5bd01abae0423d4722a4977d5ab5e0ff386143c",
    "analysis/validation/run_validation.py": "7d99cbd503e76e031e429520ae1caa021a521d44f7901fa38d09b158a093701d",
    "analysis/validation/telemetry_assessment.md": "2bdb71d460ebe422bbf6df02064eb431e4abdd7b84ad26dbd8bc5a99473979b9",
    "analysis/validation/tests/test_validation.py": "ac6a57ab60d86caa2ee0297568627b9d35639006f6b4931d9f86a613fae429cb",
    "analysis/validation/uncertainty_assessment.md": "289ae5a6d7adb7aeead1823f01d876f7f778551d759a4604740f19d9ef99639f",
    "analysis/validation/validation_checks.csv": "65f868ba6daa12552ee8ab3325b4f1a40236fe00cdf330b861a0d5fe623ffec3",
    "analysis/validation/validation_matrix.csv": "5f261698ea069c1537feefacde8ccf2508810baf112c21b100669742e09bccad",
}

PHASE3_MANIFEST_NORMALISED_SHA256 = "9141447b731fa7ed95fd83aedb0f7b75740ea0ea326847da3ecd16961412e23d"

def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture(scope="module")
def ran():
    """Run the pipeline once (regenerates this phase's outputs) and return them."""
    subprocess.run([sys.executable, os.path.join(ER, "run_resolution.py")],
                   check=True, capture_output=True, cwd=ROOT)
    out = {}
    for name in ("resolution_checks.csv", "evidence_resolution_register.csv",
                 "source_document_register.csv", "correction_register.csv",
                 "run_manifest.json"):
        with open(os.path.join(ER, name)) as fh:
            out[name.rsplit(".", 1)[0]] = list(csv.DictReader(fh)) if name.endswith(".csv") \
                else json.load(fh)
    return out


# --- preservation --------------------------------------------------------------
def test_raw_dataset_unchanged():
    assert sha256_of(RAW_CSV) == RAW_SHA256


def test_all_prior_phase_files_exist_and_unchanged():
    checked = 0
    for rel in PROTECTED:
        assert os.path.exists(os.path.join(ROOT, rel)), rel
        if rel in PROTECTED_SHA256:
            assert sha256_of(rel) == PROTECTED_SHA256[rel], f"changed: {rel}"
            checked += 1
    assert len(PROTECTED) >= 42
    assert checked >= 41


def test_phase3_manifest_verified_with_timestamp_normalised():
    rel = "analysis/validation/run_manifest.json"
    assert rel in PROTECTED
    man = json.load(open(os.path.join(ROOT, rel)))
    man.pop("executed_utc", None)
    canon = json.dumps(man, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canon.encode()).hexdigest()
    assert digest == PHASE3_MANIFEST_NORMALISED_SHA256
    # audit + exploratory + validation contents are all covered
    for p in ("audit", "exploratory", "validation"):
        n = sum(1 for r in PROTECTED if r.startswith(os.path.join("analysis", p)))
        assert n >= 7, p


def test_pipeline_run_does_not_modify_anything_protected():
    before = {rel: sha256_of(rel) for rel in PROTECTED}
    subprocess.run([sys.executable, os.path.join(ER, "run_resolution.py")],
                   check=True, capture_output=True, cwd=ROOT)
    for rel, digest in before.items():
        assert sha256_of(rel) == digest, f"pipeline modified {rel}"


def test_no_git_repository_created():
    import glob
    hits = [p for p in glob.glob(os.path.join(ROOT, ".git"))
            + glob.glob(os.path.join(ROOT, "analysis", "*", ".git"))]
    assert not hits, hits


def test_no_archive_extracted():
    """Phase 3.5 must not have left extraction artifacts anywhere in the project."""
    import glob
    leaked = (glob.glob(os.path.join(ROOT, "**", "*.tif"), recursive=True)
              + glob.glob(os.path.join(ROOT, "**", "*_00000.bmp"), recursive=True))
    assert not leaked, leaked[:5]


# --- evidence register integrity ------------------------------------------------
def test_evidence_statuses_and_levels_valid(ran):
    statuses = {"RESOLVED", "PARTIALLY_RESOLVED", "DOCUMENTED_UNCONFIRMED",
                "UNVERIFIED", "BLOCKED", "ORIGINATOR_CONFIRMATION_REQUIRED"}
    rows = ran["evidence_resolution_register"]
    assert len(rows) >= 15
    ids = [r["evidence_id"] for r in rows]
    assert len(set(ids)) == len(ids)
    for r in rows:
        assert r["status"] in statuses, r["evidence_id"]
        assert r["evidence_level"][:2] in ("L1", "L2", "L3", "L4"), r["evidence_id"]
        assert r["source_document"].strip()
        assert r["section"].strip()
        assert r["supporting_evidence"].strip()
        assert r["resolution"].strip()


def test_evidence_citations_reference_existing_documents(ran):
    import glob as _glob
    for r in ran["evidence_resolution_register"]:
        for token in _doc_tokens(r["source_document"]):
            if "*" in token:
                hits = _glob.glob(os.path.join(ROOT, token))
                assert hits, token
            else:
                assert os.path.exists(os.path.join(ROOT, token)), token


def _doc_tokens(text):
    import re
    out = []
    for pat in (r"docs/flex/[\w .-]+\.(?:pdf|docx|txt)",
                r"data/raw/flex/[\w .\-/*]+?\.(?:csv|txt)",
                r"notebooks/\S*", r"data/interim/flex/\S*"):
        out += re.findall(pat, text)
    return [t.rstrip(".,;") for t in out]


def test_burning_rate_row_blocked(ran):
    rows = ran["evidence_resolution_register"]
    br = [r for r in rows if r["requirement_id"] == "R1"]
    assert br
    assert any(r["status"] == "BLOCKED" for r in br)
    assert any("UNIT UNVERIFIED" in r["resolution"] for r in br)


def test_disruption_row_unverified(ran):
    rows = ran["evidence_resolution_register"]
    d = [r for r in rows if r["requirement_id"] == "R2"]
    assert d and all(r["status"] == "UNVERIFIED" for r in d)


def test_source_register_hashes_correct(ran):
    for r in ran["source_document_register"]:
        if r["sha256"]:
            assert sha256_of(r["path"]) == r["sha256"], r["path"]
        if r["present"] == "yes":
            assert os.path.exists(os.path.join(ROOT, r["path"]))


# --- no forbidden inferences -----------------------------------------------------
DOCS = ["README.md", "burning_rate_investigation.md", "outcome_semantics.md",
        "anomaly_resolution.md", "identifier_reconciliation.md",
        "calibration_assessment.md", "image_archive_pilot.md",
        "clock_reconciliation.md", "metadata_recovery.md", "phase4_readiness.md",
        "run_resolution.py", "evidence_resolution_register.csv",
        "validation_placeholder"]


def _texts():
    out = {}
    for f in DOCS[:-1]:
        out[f] = open(os.path.join(ER, f)).read()
    return out


def test_no_unit_assigned_to_burning_rate():
    for f, text in _texts().items():
        for para in text.split("\n\n"):
            if re.search(r"mm\s*[²2]\s*/s|mm/s", para.lower()):
                assert any(k in para.lower() for k in (
                    "eird", "requirements", "literature", "adjacent", "blocked",
                    "unverified", "does not", "not verify", "prohibited",
                    "context", "documented", "hypothesis", "contradicted",
                    "candidate", "d2", "nominal", "convention", "reference",
                    "assumed", "would")), (f, para[:100])


import re  # noqa: E402  (used above)


def test_no_imputation_or_renormalisation():
    for f, text in _texts().items():
        for para in text.split("\n\n"):
            low = " ".join(para.lower().split())
            if "imput" in low:
                assert any(k in low for k in ("never", "not ", "no ", "none",
                                              "without", "nothing")), (f, para[:100])
            if re.search(r"renormalis|renormaliz", low):
                assert any(k in low for k in ("never", "not ", "nothing")), (f, para[:100])


def test_no_modelling_code():
    src = open(os.path.join(ER, "run_resolution.py")).read()
    for banned in ("sklearn", "LinearRegression", "LogisticRegression",
                   "curve_fit", "polyfit"):
        assert banned not in src
    neg = ("not", "prohibit", "never", "no ", "none")
    for f, text in _texts().items():
        paras = [" ".join(p.lower().split()) for p in text.split("\n\n")]
        for i, para in enumerate(paras):
            if re.search(r"d\s*[²2]\s*-law", para) and "fit" in para:
                ctx = para + " " + (paras[i - 1] if i else "")
                assert any(k in ctx for k in neg), (f, para[:100])


def test_classifications_follow_the_mandated_scheme():
    """Each critical question must be classified resolved / partially resolved /
    locally unrecoverable / originator confirmation required."""
    readme = open(os.path.join(ER, "README.md")).read()
    for cls in ("Locally unrecoverable", "Partially resolved", "Resolved"):
        assert cls in readme
    pf = open(os.path.join(ER, "phase4_readiness.md")).read()
    for st in ("RESOLVED", "PARTIALLY RESOLVED", "UNRESOLVED", "BLOCKED"):
        assert st in pf


# --- forensic results -------------------------------------------------------------
def test_checks_match_raw_data(ran):
    checks = {r["quantity"]: r["value"] for r in ran["resolution_checks"]}
    assert checks["n_records"] == "274"
    assert checks["n_methanol"] == "157"
    assert checks["n_heptane"] == "117"
    assert checks["duplicate_datetime_pairs"] == "2"
    assert json.loads(checks["zero_extinction_fuel_split"]) == {"Heptane": 8}
    assert json.loads(checks["zero_extinction_outcome_split"]) == {"Disruption": 4,
                                                                  "Completion": 4}
    assert json.loads(checks["d_ext_gt_d0_records"])[0]["excess_mm"] == 0.01
    coll = json.loads(checks["collision_193F001"])
    assert coll[0]["gmt"] == "7:25:43" and coll[0]["d0"] == "4.67"
    assert coll[1]["rate"] == "0.56" and coll[1]["d0"] == "4.64"
    assert json.loads(checks["pressure_zero_series_median"]) == 534.6
    assert checks["study_doi"] == "10.60555/mbq8-0451"
    assert checks["study_identifier"] == "PSI-69"


def test_duplicate_sensitivity_matches_validated_values(ran):
    checks = {r["quantity"]: r["value"] for r in ran["resolution_checks"]}
    allv = json.loads(checks["d0_contrast_all"])
    assert allv["U"] == 7190.0 and abs(allv["p"] - 0.06229) < 1e-9
    ex = json.loads(checks["d0_contrast_excluding_collision_1"])
    assert ex["U"] == 7036.0 and abs(ex["p"] - 0.04498) < 1e-9
    assert isinstance(checks["d0_contrast_excluding_collision_2"], str)


def test_clock_facts_present(ran):
    checks = {r["quantity"]: r["value"] for r in ran["resolution_checks"]}
    clocks = json.loads(checks["clock_offsets"])
    assert len(clocks) == 8
    meds = [c["pip_minus_main_median_s"] for c in clocks]
    assert min(meds) > 1.0 and max(meds) < 2.0  # offsets, not synchronised
    assert all(c["net_drift_s_per_1000_samples"] != 0 for c in clocks)
    cross = json.loads(checks["chamber_pressure_crosscheck"])
    assert len(cross) == 8
    assert all(c["abs_diff_mmHg"] < 1.3 for c in cross)  # 0.06-1.24 mmHg
    snaps = [c for c in cross if c["chamber_rows"] == 1]
    assert len(snaps) == 3


def test_archive_census(ran):
    checks = {r["quantity"]: r["value"] for r in ran["resolution_checks"]}
    arch = json.loads(checks["image_archives"])
    assert len(arch) == 23
    assert all(a["format"] in ("TIFF", "BMP") for a in arch)
    assert sum(a["images"] for a in arch) == 24258
    by_seg = {}
    for a in arch:
        by_seg.setdefault(a["archive"][7], []).append(a)
    assert {seg: len(v) for seg, v in by_seg.items()} == {"A": 7, "B": 8, "D": 8}
    tiff = next(a for a in arch if a["format"] == "TIFF")
    bmp = next(a for a in arch if a["format"] == "BMP")
    assert tiff["dimensions"] == {"width": 512, "height": 512, "bits": 16,
                                 "compression": 1}
    assert bmp["dimensions"] == {"width": 640, "height": 480, "bpp": 24}


def test_burning_rate_hypothesis_recorded(ran):
    checks = {r["quantity"]: r["value"] for r in ran["resolution_checks"]}
    allh = json.loads(checks["burnrate_hypothesis_All"])
    assert allh["n"] == 257
    assert abs(allh["spearman_rate_vs_d2_over_t"]) < 0.1
    hep = json.loads(checks["burnrate_hypothesis_Heptane"])
    assert hep["spearman_rate_vs_d2_over_t"] < -0.3


# --- manifest ---------------------------------------------------------------------
def test_manifest_records_everything(ran):
    man = ran["run_manifest"]
    assert man["inputs"][0]["sha256"] == RAW_SHA256
    assert man["inputs"][0]["records"] == 274
    assert "executed_utc" in man
    assert len(man["documents_inspected"]) >= 15
    assert man["archive_metadata_inspected"]["archives"] == 23
    assert man["restrictions"]["modelling"].startswith("none")
    for name, entry in man["outputs"].items():
        assert sha256_of(os.path.join("analysis", "evidence_resolution", name)) == entry["sha256"]


def test_phase4_readiness_lists_blockers():
    text = open(os.path.join(ER, "phase4_readiness.md")).read()
    assert "P4-1" in text and "P4-7" in text
    assert "prohibited" in text.lower()


def test_readme_has_clarification_package():
    text = open(os.path.join(ER, "README.md")).read()
    for q in ("OQ-1", "OQ-2", "OQ-3", "OQ-4", "OQ-5", "OQ-6", "OQ-7", "OQ-8"):
        assert q in text, q
    assert "NOT sent" in text or "not sent" in text.lower()


def test_correction_register_documents_frozen_phase_defects():
    rows = list(csv.DictReader(open(os.path.join(ER, "correction_register.csv"))))
    assert len(rows) >= 4
    c1 = [r for r in rows if r["correction_id"] == "COR-01"]
    assert c1 and "Disruption x4" in c1[0]["corrected_statement"]
    for r in rows:
        assert r["action"].startswith(("documented, not modified",
                                          "corrected in place"))
