"""Independent tests for the FLEX PSI-69 Phase 2 exploratory analysis.

Run from the repository root:

    notebooks/.venv/bin/python -m pytest analysis/exploratory/tests/ -v

The tests verify input loading, missing-value and approximate-value handling,
fuel classification, record counts, the statistical primitives against
hand/published reference values, CSV output generation, and that the raw
dataset is never modified. No test writes outside analysis/exploratory/
except outputs explicitly produced by running the analysis entry point.
"""

import csv
import json
import os
import sys
from collections import Counter

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flex_core as fc
import run_analysis as ra

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="module")
def records():
    return fc.load_records(os.path.join(ROOT, fc.CSV_PATH))


@pytest.fixture(scope="module")
def csv_path():
    return os.path.join(ROOT, fc.CSV_PATH)


# --- input loading and preservation -----------------------------------------
def test_raw_dataset_sha256_unchanged(csv_path):
    assert fc.sha256_of(csv_path) == fc.EXPECTED_CSV_SHA256


def test_load_records_counts(records):
    assert len(records) == 274
    assert sum(1 for r in records if r["fuel"] == "Methanol") == 157
    assert sum(1 for r in records if r["fuel"] == "Heptane") == 117


def test_all_fuel_labels_known(records):
    assert {r["fuel"] for r in records} == set(fc.FUELS)
    assert {r["test_end"] for r in records} == set(fc.OUTCOMES)


def test_source_layout_validation(records):
    # matches the Phase 1 audit expectations
    assert ra.validate(records)["complete_core"] == 196


def test_expected_source_error_on_wrong_layout(tmp_path, records):
    # a file missing a required column must raise, not silently load
    bad = tmp_path / "bad.csv"
    cols = list(fc.COLUMNS.values())[:-1]
    with open(bad, "w", newline="", encoding="latin-1") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for r in records[:5]:
            writer.writerow({c: "" for c in cols})
    with pytest.raises(fc.SourceDataError):
        fc.load_records(bad)


# --- missing-value handling ---------------------------------------------------
def test_missing_marker_is_none_not_zero(records):
    zero_byte = [r for r in records if r["missing_marker_bytes"] > 0]
    assert len(zero_byte) > 0
    for r in zero_byte:
        for key in ("d0_mm", "d_ext_mm", "burn_rate_raw"):
            if r[key] == fc.MISSING_BYTE:
                assert r[key + "_val"] is None  # never parsed as 0


def test_missing_counts_match_audit(records):
    assert sum(1 for r in records if r["d_ext_mm_val"] is None) == 77
    assert sum(1 for r in records if r["d0_mm_val"] is None) == 12
    assert sum(1 for r in records if r["burn_time_s_val"] is None) == 6


def test_descriptive_stats_partition():
    st = fc.descriptive_stats([(1.0, False), (2.0, False), (None, False), (9.0, True)])
    assert st["n_total"] == 4 and st["n_used"] == 2 and st["n_missing"] == 1
    assert st["n_approx_excluded"] == 1
    assert st["mean"] == 1.5


# --- approximate values -------------------------------------------------------
def test_approximate_values_preserved(records):
    approx = [r for r in records if r["burn_time_s_approx"]]
    assert len(approx) == 2
    assert sorted(r["burn_time_s"] for r in approx) == ["~6", "~9"]
    for r in approx:
        assert r["burn_time_s_val"] in (6.0, 9.0)
        assert "contains_approximate_value" in r["flags"]
    st = fc.descriptive_stats([(r["burn_time_s_val"], r["burn_time_s_approx"]) for r in records])
    assert st["n_used"] == 266 and st["n_approx_excluded"] == 2  # approx not pooled in


# --- flagged records retained -------------------------------------------------
def test_flagged_records_retained(records):
    flags = [f for r in records for f in r["flags"]]
    assert flags.count("pressure_reported_zero") == 1
    assert flags.count("extinction_diameter_reported_zero") == 8
    assert flags.count("extinction_diameter_gt_initial_diameter") == 1
    assert flags.count("composition_sum_not_one") == 29
    ids = [r["flex_identifier"] for r in records]
    assert ids.count("193F001") == 2  # collision retained, both rows present
    assert len(records) == 274  # nothing dropped


def test_screened_excludes_only_flagged(records):
    screened = [r for r in records if not fc.screened_out(r)]
    assert len(screened) == 274 - 10  # 1 pressure-zero + 8 zero-d_ext + 1 gt-diameter


def test_composition_not_renormalised(records):
    for r in records:
        if r["comp_sum_mf"] is not None:
            assert abs(r["comp_sum_mf"] - 1.0) < 0.051
            # values reported verbatim, not adjusted
    explicit = [r for r in records if "composition_sum_not_one" in r["flags"]]
    assert explicit and all(r["comp_sum_mf"] != 1.0 for r in explicit)


# --- statistics primitives ----------------------------------------------------
def test_descriptive_stats_reference():
    st = fc.descriptive_stats([(v, False) for v in [1.0, 2.0, 3.0, 4.0]])
    assert st["mean"] == pytest.approx(2.5)
    assert st["std"] == pytest.approx(1.2909944487358056)  # ddof=1
    assert (st["q1"], st["median"], st["q3"]) == (pytest.approx(1.75),
                                                  pytest.approx(2.5), pytest.approx(3.25))
    assert st["iqr"] == pytest.approx(1.5)
    assert (st["min"], st["max"]) == (1.0, 4.0)
    assert st["n_total"] == st["n_used"] + st["n_missing"] + st["n_approx_excluded"]


def test_mann_whitney_reference_values():
    u, p, nx, ny = fc.mann_whitney_u([1, 2, 3], [4, 5, 6])
    assert (u, nx, ny) == (0.0, 3, 3)
    assert p == pytest.approx(0.08086, abs=2e-4)  # asymptotic two-sided, continuity corrected
    # identical samples with ties: U = 4.5 (expected value), tie-corrected
    # normal approximation with continuity correction
    u2, p2, _, _ = fc.mann_whitney_u([1, 2, 3], [1, 2, 3])
    assert u2 == pytest.approx(4.5)
    assert p2 == pytest.approx(0.8195, abs=2e-3)
    assert fc.mann_whitney_u([], [1, 2]) == (None, None, 0, 2)


def test_spearman_reference_values():
    rho, _ = fc.spearman_rho([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
    assert rho == pytest.approx(-1.0)
    rho2, _ = fc.spearman_rho([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert rho2 == pytest.approx(1.0)
    assert fc.spearman_rho([1, 1], [2, 2])[0] is None


def test_spearman_p_bounded():
    rho, p = fc.spearman_rho([1, 2, 3], [3, 2, 1])
    assert p is None or 0.0 <= p <= 1.0


def test_spearman_p_reference_values():
    # p must be the two-sided t tail: erfc(|t|/sqrt(2)). An earlier version
    # returned 2*(1-0.5*erfc(...)) = 2*Phi(|t|) >= 1, clipped to exactly 1.0.
    rho, p = fc.spearman_rho([1, 2, 3, 4, 5], [2, 1, 4, 3, 5])
    assert rho == pytest.approx(0.8, abs=1e-12)
    # t = rho*sqrt((n-2)/(1-rho^2)) = 0.8*sqrt(3/0.36); p = erfc(|t|/sqrt(2))
    import math
    t = 0.8 * math.sqrt(3.0 / (1.0 - 0.64))
    expected = math.erfc(abs(t) / math.sqrt(2.0))
    assert p == pytest.approx(expected)
    assert p < 1.0  # the regression always produced exactly 1.0
    rho2, p2 = fc.spearman_rho([1, 2, 3, 4, 5, 6, 7], [7, 6, 5, 4, 3, 2, 1])
    assert rho2 == pytest.approx(-1.0, abs=1e-12)
    assert p2 is None or p2 == pytest.approx(0.0, abs=1e-9)


def test_spearman_p_not_all_one_on_real_data(records):
    # the burning-rate association table must contain a spread of real p-values
    rows = ra.analysis_burning_rate(records)
    pvals = {float(r["std"]) for r in rows if r["analysis"] == "C_burning_rate_association"
             and r["std"] != ""}
    assert pvals and min(pvals) < 1e-6 and max(pvals) > 0.01, pvals


def test_fisher_exact_reference_values():
    # classic hypergeometric tables: [[3,0],[0,3]] -> two-sided p = 0.1
    p, _ = fc.fisher_exact_2x2(3, 0, 0, 3)
    assert p == pytest.approx(0.1)
    # published example: [[3,5],[10,6]] -> p ~= 0.3905
    p2, _ = fc.fisher_exact_2x2(3, 5, 10, 6)
    assert p2 == pytest.approx(0.39045, abs=1e-4)
    assert fc.fisher_exact_2x2(0, 0, 0, 0) == (None, None)


def test_holm_adjustment():
    adj = fc.holm_adjust([0.01, 0.04, 0.03])
    assert adj == [pytest.approx(0.03), pytest.approx(0.06), pytest.approx(0.06)]
    # adjusted p-values are monotone non-decreasing in the step-down order
    assert fc.holm_adjust([0.5, 0.9]) == [pytest.approx(1.0), pytest.approx(1.0)]


# --- condition helpers --------------------------------------------------------
def test_pressure_bands():
    assert fc.pressure_band(None) == "not_reported"
    assert fc.pressure_band(530) == "<560 mmHg"
    assert fc.pressure_band(760) == "560-800 mmHg"
    assert fc.pressure_band(1500) == "800-2100 mmHg"
    assert fc.pressure_band(2320) == ">2100 mmHg"


def test_diluent_type():
    base = {k + "_val": 0.0 for k in ("o2_mf", "n2_mf", "co2_mf", "he_mf")}
    assert fc.diluent_type(base) == "none"
    base["co2_mf_val"] = 0.2
    assert fc.diluent_type(base) == "CO2"
    base["co2_mf_val"] = 0.0
    base["he_mf_val"] = 0.2
    assert fc.diluent_type(base) == "He"


def test_condition_family_confounded_high_pressure(records):
    high = [r for r in records if (r["pressure_mmHg_val"] or 0) > 800]
    assert len(high) == 9
    assert len({fc.condition_family(r) for r in high}) == 1  # single CO2 family


# --- analysis outputs ---------------------------------------------------------
def test_analysis_csvs_generate(records, tmp_path):
    for name, rows in (
        ("descriptive_statistics.csv", ra.analysis_descriptive(records)),
        ("diameter_analysis.csv", ra.analysis_diameter(records)),
        ("burning_rate_analysis.csv", ra.analysis_burning_rate(records)),
        ("duration_analysis.csv", ra.analysis_duration(records)),
        ("outcome_analysis.csv", ra.analysis_outcome(records)),
        ("condition_analysis.csv", ra.analysis_condition(records)),
    ):
        assert rows, name
        ra.write_csv(tmp_path / name, rows)
        with open(tmp_path / name) as fh:
            text = fh.read()
        # missing must be serialised as empty, never as nan/None/0
        assert "nan" not in text.lower(), name
        assert "None" not in text, name


def test_descriptive_csv_partition_and_units(records, tmp_path):
    rows = ra.analysis_descriptive(records)
    for row in rows:
        assert row["n_total"] == row["n_used"] + row["n_missing"] + row["n_approx_excluded"]
        if row["variable"] == "burn_rate_raw":
            assert row["unit_status"].startswith("UNRESOLVED")
        assert row["mode"] in ("as_reported", "screened")
    modes = {r["mode"] for r in rows}
    assert modes == {"as_reported", "screened"}  # screened variants always documented


def test_duration_csv_lists_approximate_separately(records):
    rows = ra.analysis_duration(records)
    approx_rows = [r for r in rows if r["mode"] == "as_reported_approximate"]
    assert len(approx_rows) == 2
    # original '~' strings preserved verbatim in the output
    assert {r["mean"] for r in approx_rows} == {"~6", "~9"}


def test_outcome_counts_consistent(records):
    rows = [r for r in ra.analysis_outcome(records)
            if r["metric"] == "outcome_count" and r["group"] == "fuel=All"]
    total = Counter()
    for r in rows:
        total[r["outcome"]] += int(r["count"])
    assert total == {"Extinction": 186, "Disruption": 61, "Completion": 27}


def test_full_run_writes_manifest_and_outputs():
    ra.main()  # deterministic re-run into analysis/exploratory/
    man_path = os.path.join(os.path.dirname(ra.__file__), "run_manifest.json")
    with open(man_path) as fh:
        man = json.load(fh)
    assert man["inputs"][0]["hash_match"] is True
    assert man["inputs"][0]["records"] == 274
    assert "executed_utc" in man
    assert any("sha256" in v for v in man["outputs"].values())
    assert any(v.get("rows", 0) > 0 for v in man["outputs"].values())


def test_figures_exist():
    fig_dir = os.path.join(os.path.dirname(ra.__file__), "figures")
    names = sorted(os.listdir(fig_dir))
    assert len(names) == 7
    for n in names:
        assert n.endswith(".png")


def test_audit_deliverables_not_overwritten():
    audit = os.path.join(ROOT, "analysis", "audit")
    for f in ("dataset_inventory.md", "fuel_comparison_inventory.csv",
              "missing_data_report.csv", "condition_coverage.csv",
              "data_quality_report.md", "audit_flex_psi69.py"):
        assert os.path.exists(os.path.join(audit, f)), f


def test_burning_rate_stats_match_independent_parser(records):
    """Recompute burn-rate statistics from the raw CSV with an independent
    parser (no flex_core import) and compare with the delivered CSV rows."""
    import csv as _csv
    path = os.path.join(ROOT, fc.CSV_PATH)
    with open(path, newline="", encoding="latin-1") as fh:
        raw = list(_csv.DictReader(fh))
    rate_col = "Burning rate; mm"
    vals = {}
    for fuel in fc.FUELS:
        vals[fuel] = [float(r[rate_col]) for r in raw
                      if r["Fuel"] == fuel and r[rate_col].strip() not in ("", "\x96")]
    import numpy as _np
    rows = [r for r in ra.analysis_burning_rate(records)
            if r["analysis"] == "C_burning_rate" and r["group"] in
            ("fuel=Methanol", "fuel=Heptane")]
    delivered = {r["group"].split("=")[1]: r for r in rows}
    for fuel, v in vals.items():
        a = _np.asarray(v)
        row = delivered[fuel]
        assert int(row["n_used"]) == len(v), (fuel, row["n_used"], len(v))
        assert float(row["mean"]) == pytest.approx(float(a.mean()), abs=5e-5)  # CSV stores 4 decimals
        assert float(row["median"]) == pytest.approx(float(_np.median(a)), abs=5e-5)


def test_manifest_hashes_match_disk():
    man_path = os.path.join(os.path.dirname(ra.__file__), "run_manifest.json")
    with open(man_path) as fh:
        man = json.load(fh)
    for name, entry in man["outputs"].items():
        disk = os.path.join(ROOT, entry["path"])
        assert os.path.exists(disk), name
        assert fc.sha256_of(disk) == entry["sha256"], name
    assert fc.sha256_of(os.path.join(ROOT, fc.CSV_PATH)) == man["inputs"][0]["sha256"]


def test_duplicate_sensitivity_rows_present(records):
    rows = ra.analysis_diameter(records)
    sens = [r for r in rows if r["analysis"] == "B_diameter_sensitivity_duplicate"]
    d0_primary = [r for r in rows if r["analysis"] == "B_diameter_fuel_contrast"
                  and r["variable"] == "d0_mm"][0]
    d0_sens = [r for r in sens if r["variable"] == "d0_mm"]
    assert len(d0_sens) == 2  # one row per collision record
    # the initial-diameter contrast is duplicate-sensitive: removing either
    # collision record moves p (disclosed in README)
    assert float(d0_primary["std"]) != pytest.approx(float(d0_sens[0]["std"]), abs=1e-12)


def test_substitution_cell_columns_and_guards(records):
    rows = ra.analysis_condition(records)
    cells = [r for r in rows if r["analysis"] == "F_diluent_substitution_cell"]
    assert len(cells) == 10
    for c in cells:
        n_co2, n_he = int(c["n_co2_substituted"]), int(c["n_he_substituted"])
        assert n_co2 >= 1 and n_he >= 1
        if min(n_co2, n_he) < 3:
            assert "insufficient records" in c["comparability_verdict"]
        assert c["n2_sets"]  # per-side N2 balances always reported
    # cells with a side n<3 exist in this dataset and must be flagged
    assert any("insufficient records" in c["comparability_verdict"] for c in cells)
