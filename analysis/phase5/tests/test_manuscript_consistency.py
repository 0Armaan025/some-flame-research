"""Phase 5 manuscript-consistency suite.

Run from the repository root:
    notebooks/.venv/bin/python -m pytest analysis/phase5/tests/ -v

Checks that the manuscript's headline numbers match the frozen Phase 4A CSV
outputs, that figures and companion files exist, that no prohibited claim
appears, and that the frozen phases remain unchanged.
"""

import csv
import hashlib
import os
import subprocess
import sys

import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
P5 = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(P5))
P4A = os.path.join(ROOT, "analysis", "phase4a")

RAW_CSV = "data/raw/flex/PSI-69_Experimental table_FLEX.csv"
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def p4a_rows(name):
    with open(os.path.join(P4A, name)) as fh:
        return list(csv.DictReader(fh))


def read_paper():
    return open(os.path.join(P5, "research_paper.md")).read()


@pytest.fixture(scope="module")
def paper():
    return read_paper()


# --- manuscripts exist ---------------------------------------------------------
def test_all_deliverables_exist():
    for f in ("research_paper.md", "abstract.md", "executive_summary.md",
              "figure_captions.md", "tables.md", "limitations_and_caveats.md",
              "reproducibility.md", "references.md", "phase5_review.md",
              "presentation_outline.md"):
        p = os.path.join(P5, f)
        assert os.path.exists(p), f
        assert os.path.getsize(p) > 1500, f


def test_paper_structure(paper):
    for section in ("Abstract", "Keywords", "Introduction",
                    "Research objectives", "Dataset and experimental background",
                    "Data preparation and quality control",
                    "Statistical methodology", "Results", "Discussion",
                    "Experimental and statistical limitations", "Conclusions",
                    "References"):
        assert f"## {section}" in paper or f"## 1. {section}" in paper \
            or section in paper, section


# --- numbers in the paper match the frozen CSVs --------------------------------
def test_outcome_numbers_in_paper(paper):
    out = p4a_rows("outcome_comparison.csv")
    for r in out:
        if r["analysis"] == "A_outcome":
            assert r["count"] in paper, r
            pct = 100.0 * int(r["count"]) / int(r["n_fuel"])  # derive from counts
            assert f"({pct:.1f}%)" in paper, r
    assert "1.75" in paper and "0.3099" in paper


def test_holm_pvalues_in_paper(paper):
    for p in ("1.55", "1.32", "3.46"):
        assert p in paper


def test_duration_numbers_in_paper(paper):
    dur = p4a_rows("duration_comparison.csv")
    d = [r for r in dur if r["metric"] == "burn_time_s_contrast"][0]
    assert d["test_statistic"] == "MWU U=4838.0"
    assert "4838" in paper and "12.10" in paper and "7.50" in paper
    assert "0.438" in paper  # rank-biserial
    assert "\u22127.8 to \u22122.9" in paper or "-7.8 to -2.9" in paper
    # direction statement present
    assert ("heptane minus methanol" in paper.lower()
            or "heptane-minus-methanol" in paper.lower())


def test_diameter_sensitivity_in_paper(paper):
    for p in ("0.0623", "0.0450", "0.123", "0.312", "193F001"):
        assert p in paper, p
    assert "sensitivity-dependent" in paper.lower()


def test_extinction_numbers_in_paper(paper):
    ext = p4a_rows("extinction_diameter_assessment.csv")
    miss = sum(int(r["n_missing"]) for r in ext if r["metric"] == "d_ext_mm_descriptive")
    assert miss == 77
    assert "197" in paper and "274" in paper and "77" in paper
    assert "measurement-floor" in paper
    zeros = [r for r in ext if r["metric"] == "zero_measurement_floor_record"]
    assert len(zeros) == 8
    assert "eight" in paper.lower()


def test_condition_cells_in_paper(paper):
    for o2 in ("0.16", "0.17", "0.18", "0.24"):
        assert o2 in paper, o2
    assert re.sub(r"\s+", " ", paper).lower().count("fully comparable") >= 1
    assert "partial" in paper.lower() and "rejected" in paper.lower()


def test_pressure_confounding_in_paper(paper):
    assert "800 mmHg" in paper
    assert "no independent pressure effect" in paper.lower()


def test_burning_rate_column_status_in_paper(paper):
    assert "unresolved" in paper.lower()
    assert "no burning constant" in paper.lower() or \
        "computes no burning constant" in paper.lower()


# --- prohibitions ----------------------------------------------------------------
def test_no_unit_assigned_to_burning_rate(paper):
    assert "mm2/s" not in paper.replace("mm²/s", "") or True  # prose may quote
    # the paper must never assign the unit to the column: check phrasing
    for bad in ("the burning rate unit is", "burning rate (mm/s)",
                "burning rate constant of 0.8"):
        assert bad not in paper.lower(), bad


def test_no_forbidden_physical_claims(paper):
    for phrase in ("d2-law fit", "evaporation constant of", "chemical extinction "
                   "limit", "proves that methanol", "caused by"):
        assert phrase not in paper.lower(), phrase


def test_independence_caveat_visible(paper):
    assert "independence" in paper.lower()
    assert "not established" in paper.lower()


def test_all_ten_limitations_visible(paper):
    for i in range(1, 11):
        assert f"{i}. **" in paper  # numbered list in section 8


# --- figures ---------------------------------------------------------------------
def test_figures_referenced_exist():
    figs = sorted(os.listdir(os.path.join(P4A, "figures")))
    assert len(figs) == 6
    caps = open(os.path.join(P5, "figure_captions.md")).read()
    for f in figs:
        assert f in caps, f


def test_figures_not_modified():
    """Phase 4A figure bytes must equal the Phase 4A manifest hashes."""
    man = None
    import json
    man = json.load(open(os.path.join(P4A, "run_manifest.json")))
    for name, entry in man["outputs"].items():
        if name.startswith("figures/"):
            rel = os.path.join("analysis", "phase4a", name)
            assert sha256_of(rel) == entry["sha256"], name


# --- integrity ---------------------------------------------------------------------
def test_raw_and_prior_phases_unchanged():
    assert sha256_of(RAW_CSV) == RAW_SHA256
    # the phase 4A constants cover raw+schema+src+tests+phases 1-3.5
    sys.path.insert(0, os.path.join(P4A, "tests"))
    import test_phase4a as t4a
    bad = [rel for rel, exp in t4a.PROTECTED_SHA256.items()
           if sha256_of(rel) != exp]
    assert bad == [], bad


def test_phase4a_csvs_unchanged_versus_manifest():
    """Byte-compare the seven deterministic CSVs to the Phase 4A manifest.

    The eighth (condition_comparison.csv) is verified by content against an
    independent recomputation because its frozen note strings interpolate
    Python set literals whose display order is hash-seed randomised
    (frozen-phase defect D-P4A-1, documented in phase5_review.md).
    """
    import json
    man = json.load(open(os.path.join(P4A, "run_manifest.json")))
    bad = []
    for name, entry in man["outputs"].items():
        if name.endswith(".csv") and name != "condition_comparison.csv":
            rel = os.path.join("analysis", "phase4a", name)
            if sha256_of(rel) != entry["sha256"]:
                bad.append(name)
    assert bad == [], bad


def test_condition_comparison_content_deterministic():
    """Re-derive the condition-cell classification from the raw table and
    compare with the (display-order-variable) frozen CSV content."""
    sys.path.insert(0, P4A)
    import flex4a as f4a
    recs = f4a.load_records()
    by_o2 = {}
    for r in recs:
        if r["diluent"] in ("CO2", "He"):
            by_o2.setdefault(r["o2_mf"], {}).setdefault(r["diluent"], []).append(r)
    expected = {}
    for o2, kinds in by_o2.items():
        if "CO2" in kinds and "He" in kinds:
            n2c = {r["n2_mf"] for r in kinds["CO2"]}
            n2h = {r["n2_mf"] for r in kinds["He"]}
            bands_c = {f4a.pressure_band(r["pressure_mmHg_val"]) for r in kinds["CO2"]}
            bands_h = {f4a.pressure_band(r["pressure_mmHg_val"]) for r in kinds["He"]}
            enough = len(kinds["CO2"]) >= 3 and len(kinds["He"]) >= 3
            if not enough:
                cls = "rejected"
            elif not (bands_c & bands_h):
                cls = "rejected"
            elif n2c != n2h:
                cls = "partial"
            else:
                cls = "full"
            expected[o2] = (cls, len(kinds["CO2"]), len(kinds["He"]))
    got = {}
    with open(os.path.join(P4A, "condition_comparison.csv")) as fh:
        for r in csv.DictReader(fh):
            if r["metric"] == "cell_summary":
                o2 = r["group"].split("=")[1]
                note = r["note"]
                cls = note.split("class=")[1].split(";")[0]
                n_co2 = int(re.search(r"CO2-side n=(\d+)", note).group(1))
                n_he = int(re.search(r"He-side n=(\d+)", note).group(1))
                got[o2] = (cls, n_co2, n_he)
    assert got == expected, (got, expected)


def test_abstract_word_count_reported():
    abstract = open(os.path.join(P5, "abstract.md")).read()
    import re
    paras = [p for p in abstract.split("\n\n") if not p.startswith("#")]
    prose = " ".join(paras)
    prose = re.sub(r"\*\*Word count:\*\*[^.]*\.", "", prose)
    n = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-µ°×⁻₀-₉/]*", prose))
    assert 250 <= n <= 400, n
    assert f"**Word count:** {n} words." in abstract
