"""Phase 4A comparative-analysis test suite.

Run from the repository root:
    notebooks/.venv/bin/python -m pytest analysis/phase4a/tests/ -v

Verifies: raw-data and frozen-phase integrity (per-file SHA-256), the headline
quantities (counts, denominators, statistics, effect sizes), collision
sensitivity, determinism (seeded permutation/bootstrap), condition-cell
classification, no imputation, no unit assignment to the unresolved
burning-rate column, no modelling, and reproduction of every output file.
"""

import csv
import hashlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
P4A = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(P4A))

RAW_CSV = "data/raw/flex/PSI-69_Experimental table_FLEX.csv"
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"

PROTECTED_SHA256 = {
    "analysis/audit/_audit_context.json": "0988ad044c62c5277d0ad6dd4d16dc1c57fa3bdb0a926c40e9d3e93446b6ff02",
    "analysis/audit/audit_flex_psi69.py": "915be6b8d8fd07dab0c8c3f5d085070811cbaa5e30acb6988662e1e3f603dd8d",
    "analysis/audit/condition_coverage.csv": "5f0d1f6982b3c048f1d4a91bd1b8b6aea8a98f6468d218b391635a5671cf424c",
    "analysis/audit/data_quality_report.md": "9231adf81ded65c281f40694ae3fd52f970b0697fd2359daaaefd03f2482293b",
    "analysis/audit/dataset_inventory.md": "608e3ee4fb7913527f81009533d2945546e9150dad1b2a1aac5f6283756061a8",
    "analysis/audit/fuel_comparison_inventory.csv": "e606cd2e816455c1fab1a0e8ab068cb332f6e2febf2e031f3ff1edb501ebfb8f",
    "analysis/audit/missing_data_report.csv": "5057647eebaee44f0ecb13da3c7a9852a4faf0ee4c94c67cbf0aeb82d7ddbee2",
    "analysis/evidence_resolution/README.md": "dfde28d66b8fb1b9fc70210a647059c8fac9f6730e99175c41980196a4902616",
    "analysis/evidence_resolution/anomaly_resolution.md": "f0a6c7c614ff3e123589417da07a8c28520a9ea7c5b5279b9a8da15dc3b249fa",
    "analysis/evidence_resolution/burning_rate_investigation.md": "a820e626001e7170031b7f225e7873b0b881ba0b010fe423e7ecd239ffa3e8cd",
    "analysis/evidence_resolution/calibration_assessment.md": "98da8563c37b2368af9761b20392e8928c4b6da1d4414300c39fb094e02e7d61",
    "analysis/evidence_resolution/clock_reconciliation.md": "927eff684f7ab53fe29cc897c595d5053d3606703f388d0ac213f6a2c0b408e4",
    "analysis/evidence_resolution/correction_register.csv": "7828897b6195ec15bb1453d8e1391820bff2fec3d59662281f60244288788a53",
    "analysis/evidence_resolution/evidence_resolution_register.csv": "2aca0f46f5c0d7b4396a91074bcc0e77a9e53b31cfd6e88fda7ef12cdb84c722",
    "analysis/evidence_resolution/identifier_reconciliation.md": "d83ad281dd23623a365a397cf16d63c91de4a21652b8f665b6030c4ec77c774a",
    "analysis/evidence_resolution/image_archive_pilot.md": "dbcf81d54a62c4eeece49062b0416b1f3fdb1306675b52ed939537e4e31a384d",
    "analysis/evidence_resolution/metadata_recovery.md": "7c650a3ba73e1f3b9130dac6e79117b3bb91730a632cb605777f4117211f3781",
    "analysis/evidence_resolution/outcome_semantics.md": "e8e92c8ac47ed0548d6cc34baa6b2f2a28fb2cb29650b5ecb9885ae3fda42475",
    "analysis/evidence_resolution/phase4_readiness.md": "08fffd04a50bce5d636dfdb496ce3539021686292261059a04daaf84566c8e58",
    "analysis/evidence_resolution/resolution_checks.csv": "c57e2a2fdd902784d06b074230c3b66efc9528cc2b03512ef2ff97ef09aeb57c",
    "analysis/evidence_resolution/run_manifest.json": "ba774ad8f2251f1451aeb2f217eadddd9dc171102f1fbaf4942a3da88b2a1b67",
    "analysis/evidence_resolution/run_resolution.py": "78c5c6ee05afab30c38a374e43382335839544f69a3c358c3bf76c2728e28f0e",
    "analysis/evidence_resolution/source_document_register.csv": "1873b6f3d41d92a328b3060209d05062ce5f52bf921a60a860915340f6372791",
    "analysis/evidence_resolution/tests/test_resolution.py": "6346cce557080bfea45c00fac06e6030e392a182fdf0ca1acd9436c30c7b07be",
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
    "analysis/validation/README.md": "a7aa7d986c9d18098077f4383cb72bb9f26acde9f908aee50c0900e9692a9d31",
    "analysis/validation/condition_comparability.md": "8b293da6f4a5722504b14002cd8ebc342048eaaeffb29501aa7d56e809776823",
    "analysis/validation/evidence_register.csv": "10ab33b3cd7a9021302d96afbf592b62aa5bcfdf21301943c4014130cfcf09bb",
    "analysis/validation/experimental_independence.md": "8c8bf2f53f56cf8cd6faf205ea0e023738eea708591a015edc740659cbb32209",
    "analysis/validation/measurement_provenance.md": "48b40e339865c86e25491787a5bd01abae0423d4722a4977d5ab5e0ff386143c",
    "analysis/validation/run_manifest.json": "27cd6b8f5d9f30d84de05d226ea2cf82d3b05cbfdbd07057445b90917bdd86c0",
    "analysis/validation/run_validation.py": "7d99cbd503e76e031e429520ae1caa021a521d44f7901fa38d09b158a093701d",
    "analysis/validation/telemetry_assessment.md": "2bdb71d460ebe422bbf6df02064eb431e4abdd7b84ad26dbd8bc5a99473979b9",
    "analysis/validation/tests/test_validation.py": "ac6a57ab60d86caa2ee0297568627b9d35639006f6b4931d9f86a613fae429cb",
    "analysis/validation/uncertainty_assessment.md": "289ae5a6d7adb7aeead1823f01d876f7f778551d759a4604740f19d9ef99639f",
    "analysis/validation/validation_checks.csv": "65f868ba6daa12552ee8ab3325b4f1a40236fe00cdf330b861a0d5fe623ffec3",
    "analysis/validation/validation_matrix.csv": "5f261698ea069c1537feefacde8ccf2508810baf112c21b100669742e09bccad",
    "data/raw/flex/PSI-69_Experimental table_FLEX.csv": "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96",
    "data/raw/flex/s_PSI-69.txt": "cb9374159b9b01a83bfe53a0b8ba1a602793df86f298e0ad222615c55d200135",
    "schema/v1.2.0.sql": "d03e0b1605a393d9f1f7273eae90a785a2c4f32c9eb9b79615312afe87965c35",
    "src/prediction/predictor.py": "7c0c8f5412e087a0720c7faf447027126edb0aadb2e6ee617d8d72efb479bc1f",
    "tests/validate_schema_candidate.py": "fdb23d8cc28c65de62822055a328b85c24669942901616faf1e02d599567bf90",
}


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture(scope="module")
def ran():
    subprocess.run([sys.executable, os.path.join(P4A, "run_analysis.py")],
                   check=True, capture_output=True, cwd=ROOT)
    out = {}
    for name in ("results_summary.csv", "outcome_comparison.csv",
                 "duration_comparison.csv", "diameter_comparison.csv",
                 "extinction_diameter_assessment.csv", "condition_comparison.csv",
                 "sensitivity_analysis.csv", "limitations_register.csv"):
        with open(os.path.join(P4A, name)) as fh:
            out[name[:-4]] = list(csv.DictReader(fh))
    out["_manifest"] = json.load(open(os.path.join(P4A, "run_manifest.json")))
    return out


# --- integrity ---------------------------------------------------------------
def test_raw_dataset_unchanged():
    assert sha256_of(RAW_CSV) == RAW_SHA256


def test_all_frozen_files_unchanged():
    assert len(PROTECTED_SHA256) >= 55
    for rel, expected in PROTECTED_SHA256.items():
        assert os.path.exists(os.path.join(ROOT, rel)), rel
        assert sha256_of(rel) == expected, f"changed: {rel}"


def test_pipeline_does_not_modify_anything():
    before = {rel: sha256_of(rel) for rel in PROTECTED_SHA256}
    subprocess.run([sys.executable, os.path.join(P4A, "run_analysis.py")],
                   check=True, capture_output=True, cwd=ROOT)
    for rel, digest in before.items():
        assert sha256_of(rel) == digest, f"pipeline modified {rel}"


# --- headline quantities -------------------------------------------------------
def test_outcome_counts_and_denominators(ran):
    rows = [r for r in ran["outcome_comparison"] if r["analysis"] == "A_outcome"]
    counts = {}
    for r in rows:
        counts[(r["group"], r["outcome"])] = (int(r["count"]), int(r["n_fuel"]))
    assert counts[("fuel=Methanol", "Extinction")] == (126, 157)
    assert counts[("fuel=Methanol", "Disruption")] == (23, 157)
    assert counts[("fuel=Methanol", "Completion")] == (8, 157)
    assert counts[("fuel=Heptane", "Extinction")] == (60, 117)
    assert counts[("fuel=Heptane", "Disruption")] == (38, 117)
    assert counts[("fuel=Heptane", "Completion")] == (19, 117)


def test_outcome_tests_and_effect_size(ran):
    t = [r for r in ran["outcome_comparison"] if r["analysis"] == "A_outcome_table"][0]
    assert "FH p=1.75e-06" in t["proportion"]
    assert "Cramers V=0.3099" in t["proportion"]
    holm = {r["outcome"]: r["proportion"] for r in ran["outcome_comparison"]
            if r["analysis"] == "A_outcome_fisher_holm"}
    assert holm["Extinction"] == "1.55e-06"
    assert holm["Completion"] == "0.00346"
    fish = [r for r in ran["outcome_comparison"]
            if r["analysis"] == "A_outcome_fisher" and r["outcome"] == "Extinction"][0]
    assert "a=126,b=31,c=60,d=57" in fish["count"]


def test_duration_contrast_and_ci(ran):
    d = [r for r in ran["duration_comparison"]
         if r["analysis"] == "B_duration" and r["metric"] == "burn_time_s_contrast"][0]
    assert d["test_statistic"] == "MWU U=4838.0"
    assert float(d["p_value"]) == pytest.approx(1.174e-9, rel=1e-2)
    assert d["effect_size"] == "rank-biserial r=0.4376"
    for fuel, med in (("fuel=Methanol", "12.1000"), ("fuel=Heptane", "7.5000")):
        row = [r for r in ran["duration_comparison"]
               if r["group"] == fuel and r["metric"] == "burn_time_s_descriptive"][0]
        assert row["median"] == med, fuel


def test_diameter_contrast_and_collision(ran):
    d = [r for r in ran["diameter_comparison"]
         if r["analysis"] == "C_diameter" and r["metric"] == "d0_mm_contrast"][0]
    assert d["test_statistic"] == "MWU U=7190.0"
    assert float(d["p_value"]) == pytest.approx(0.0623, abs=1e-4)
    sens = {r["variant"]: r for r in ran["sensitivity_analysis"]
            if r["analysis"] == "S_diameter"}
    assert sens["as_reported"]["p_value"] == "0.0623"
    assert sens["excluding_193F001_record_1"]["p_value"] == "0.045"
    assert sens["excluding_193F001_record_2"]["p_value"] == "0.045"
    assert sens["excluding_193F001_record_1"]["n_meoh"] == "154"
    assert sens["excluding_193F001_record_1"]["n_hep"] == "107"
    assert float(sens["screened_flagged_anomalies_excluded"]["p_value"]) == pytest.approx(0.123, abs=1e-3)


def test_permutation_and_bootstrap_deterministic(ran):
    s = [r for r in ran["sensitivity_analysis"] if r["analysis"] == "S_permutation"]
    assert len(s) == 2
    # fixed seed: re-running the same primitive gives identical p-values
    import sys
    sys.path.insert(0, P4A)
    import flex4a as f4a
    recs = f4a.load_records()
    mx = [r["d0_mm_val"] for r in recs if r["fuel"] == "Methanol" and r["d0_mm_val"] is not None]
    my = [r["d0_mm_val"] for r in recs if r["fuel"] == "Heptane" and r["d0_mm_val"] is not None]
    assert f4a.perm_p(mx, my) == pytest.approx(float(s[0]["p_value"]), abs=1e-3)


def test_missingness_counts_preserved(ran):
    total = {}
    for r in ran["extinction_diameter_assessment"]:
        if r["metric"] == "d_ext_mm_descriptive":
            fuel = r["group"].split(",")[0]  # fuel=Methanol,outcome=...
            total[fuel] = total.get(fuel, 0) + int(r["n_total"])
    assert total["fuel=Methanol"] == 157 and total["fuel=Heptane"] == 117
    miss = sum(int(r["n_missing"]) for r in ran["extinction_diameter_assessment"]
               if r["metric"] == "d_ext_mm_descriptive")
    assert miss == 77
    # the eight zero records are listed verbatim, not dropped
    zeros = [r for r in ran["extinction_diameter_assessment"]
             if r["metric"] == "zero_measurement_floor_record"]
    assert len(zeros) == 8
    assert all(r["median"] == "0" for r in zeros)


def test_descriptive_identity_holds(ran):
    for name in ("duration_comparison", "diameter_comparison",
                 "extinction_diameter_assessment"):
        for r in ran[name]:
            if r["metric"].endswith("_descriptive") and r["n_total"]:
                assert int(r["n_total"]) == (int(r["n_used"]) + int(r["n_missing"])
                                             + int(r["n_approx_excluded"])), r


def test_approximate_values_verbatim(ran):
    approx = [r for r in ran["duration_comparison"]
              if r["metric"] == "burn_time_s_approximate_verbatim"]
    assert len(approx) == 2
    assert {r["median"] for r in approx} == {"~6", "~9"}


# --- condition cells -----------------------------------------------------------
def test_condition_cell_classification(ran):
    cells = [r for r in ran["condition_comparison"]
             if r["analysis"] == "C_condition_cell" and r["metric"] == "cell_summary"]
    classes = {}
    for r in cells:
        o2 = r["group"].split("=")[1]
        cls = r["note"].split("class=")[1].split(";")[0]
        classes[o2] = cls
    full = sorted(o for o, c in classes.items() if c == "full")
    partial = sorted(o for o, c in classes.items() if c == "partial")
    rejected = sorted(o for o, c in classes.items() if c == "rejected")
    assert full == ["0.16", "0.17", "0.18", "0.24"], classes
    assert partial == ["0.2", "0.21", "0.23"], classes
    assert rejected == ["0.14", "0.15", "0.19"], classes
    # full cells: both sides >= 3 and identical N2
    for r in cells:
        if "class=full" in r["note"]:
            assert "identical N2 balance" in r["note"]


def test_pressure_confounding_disclosed(ran):
    row = [r for r in ran["condition_comparison"]
           if r["metric"] == "pressure_confounding_disclosure"][0]
    assert row["n_total"] == "9"
    assert "confounded" in row["note"] and "no independent" in row["note"]


# --- no forbidden assertions -----------------------------------------------------
OUTPUT_FILES = ["results_summary.csv", "outcome_comparison.csv",
                "duration_comparison.csv", "diameter_comparison.csv",
                "extinction_diameter_assessment.csv", "condition_comparison.csv",
                "sensitivity_analysis.csv", "limitations_register.csv"]


def test_no_nan_or_none_in_outputs():
    for name in OUTPUT_FILES:
        text = open(os.path.join(P4A, name)).read()
        assert "nan" not in text.lower(), name
        assert "None" not in text, name


def test_no_unit_assigned_to_burning_rate():
    for name in OUTPUT_FILES:
        text = open(os.path.join(P4A, name)).read()
        assert "mm2/s" not in text and "mm²/s" not in text, name
        assert "burning rate constant" not in text.lower(), name


def test_no_modelling_code():
    src = open(os.path.join(P4A, "run_analysis.py")).read()
    for banned in ("sklearn", "LinearRegression", "LogisticRegression",
                   "RandomForest", "curve_fit", "polyfit", "d2_law", "d²-law"):
        assert banned not in src, banned
    # flex4a has the d2/t consistency helper only in the manifest provenance text
    lib = open(os.path.join(P4A, "flex4a.py")).read()
    assert "def fit" not in lib


def test_no_imputation_or_renormalisation_in_outputs():
    """'imputed' may appear only inside an explicit negation."""
    import re
    for name in OUTPUT_FILES:
        text = open(os.path.join(P4A, name)).read().lower()
        for m in re.finditer(r"imput\w*", text):
            ctx = text[max(0, m.start() - 80):m.start()]
            assert any(k in ctx for k in ("never", "not ", "no ", "none",
                                          "nothing", "without")), (name, ctx)
        assert "renormalis" not in text and "renormaliz" not in text, name


# --- reproducibility -----------------------------------------------------------------
def test_manifest_hashes_match_disk(ran):
    man = ran["_manifest"]
    assert man["inputs"][0]["sha256"] == RAW_SHA256
    assert man["inputs"][0]["records"] == 274
    for name, entry in man["outputs"].items():
        rel = os.path.join("analysis", "phase4a", name)
        assert sha256_of(rel) == entry["sha256"], name


def test_rerun_byte_identical():
    def digest():
        subprocess.run([sys.executable, os.path.join(P4A, "run_analysis.py")],
                       check=True, capture_output=True, cwd=ROOT)
        return {n: sha256_of(os.path.join("analysis", "phase4a", n))
                for n in OUTPUT_FILES}
    first = digest()
    second = digest()
    for n in OUTPUT_FILES:
        assert first[n] == second[n], n


def test_figures_exist():
    figs = sorted(os.listdir(os.path.join(P4A, "figures")))
    assert len(figs) == 6
    for f in figs:
        assert os.path.getsize(os.path.join(P4A, "figures", f)) > 30000, f


def test_series_sensitivity_reported(ran):
    rows = [r for r in ran["sensitivity_analysis"] if r["analysis"] == "S_series_level"]
    assert len(rows) == 2
    assert all("only 4 of 81 series" in r["note"] for r in rows)


def test_headline_manifest_block(ran):
    man = ran["_manifest"]
    h = man["headline"]
    assert h["outcome_table"] == [[126, 23, 8], [60, 38, 19]]
    assert h["outcome_cramers_v"] == "0.3099"
    assert h["cells"]["full"] == ["0.16", "0.17", "0.18", "0.24"]
    assert h["duration_mwu"]["U"] == 4838
    assert h["diameter_mwu"]["U"] == 7190
    assert man["restrictions"]["modelling"].startswith("none")
