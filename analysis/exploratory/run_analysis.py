#!/usr/bin/env python3
"""FLEX PSI-69 Phase 2 exploratory analysis entry point.

Reproducible, read-only-with-respect-to-data pipeline:

    notebooks/.venv/bin/python analysis/exploratory/run_analysis.py

What it does:
  1. Loads and VALIDATES the raw experimental table (raw file untouched;
     sha256 checked against the value recorded in flex_core.py).
  2. Computes descriptive statistics stratified by fuel, outcome and
     condition family. Exact values only; approximate values reported
     separately; flagged/implausible records retained in "as_reported"
     results and excluded only in explicitly documented "screened" variants.
  3. Writes the six analysis CSVs.
  4. Writes figures into figures/.
  5. Writes run_manifest.json (inputs, hashes, versions, outputs, limitations).

Scientific guardrails enforced here:
  * No imputation, no unit conversion, no derived burning-rate constants.
  * Burning-rate columns are labelled "unit unresolved" everywhere.
  * No regression or machine learning. Hypothesis tests (Mann-Whitney,
    Spearman, Fisher) are descriptive/exploratory, reported with sample
    sizes, methods and caveats; no causal language.
"""

import csv
import json
import os
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flex_core as fc

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(OUT_DIR, "figures")
SCRIPT_VERSION = "2.0.0"

# --- consistent plotting conventions (documented in README) ------------------
FUEL_COLORS = {"Methanol": "#1f77b4", "Heptane": "#d62728"}
OUTCOME_COLORS = {"Extinction": "#2ca02c", "Disruption": "#ff7f0e",
                  "Completion": "#9467bd"}
FLAG_COLOR = "#000000"
APPROX_COLOR = "#8c564b"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 9,
    "axes.titlesize": 10, "axes.labelsize": 9, "axes.grid": True,
    "grid.alpha": 0.3, "legend.fontsize": 8, "figure.constrained_layout.use": True,
})

EXPECTED = dict(n_records=274, n_methanol=157, n_heptane=117,
                complete_core=196, pressure_zero=1, extinction_zero=8,
                dup_identifier="193F001", n_flagged_records=39)


def validate(records):
    """Fail loudly if the source is not the audited Phase 1 dataset."""
    actual = dict(
        n_records=len(records),
        n_methanol=sum(1 for r in records if r["fuel"] == "Methanol"),
        n_heptane=sum(1 for r in records if r["fuel"] == "Heptane"),
        complete_core=sum(1 for r in records
                          if all(r[k + "_val"] is not None for k in fc.CORE_MEASUREMENT_KEYS)),
        pressure_zero=sum("pressure_reported_zero" in r["flags"] for r in records),
        extinction_zero=sum("extinction_diameter_reported_zero" in r["flags"] for r in records),
        dup_identifier=next((k for k, v in Counter(r["flex_identifier"] for r in records).items()
                             if v > 1), None),
        n_flagged_records=sum(1 for r in records if r["flags"]),
    )
    problems = {k: (v, EXPECTED[k]) for k, v in actual.items() if v != EXPECTED[k]}
    if problems:
        raise fc.SourceDataError(f"source validation failed: {problems}")
    return actual


# ---------------------------------------------------------------------------
# statistic extraction helpers
# ---------------------------------------------------------------------------
def values(records, key):
    return [(r[key + "_val"], r[key + "_approx"]) for r in records]


def stat_row(variable, label, stratum, mode, stats, note=""):
    rule = ("implausible-value records excluded per documented flags"
            if mode == "screened" else "all reported values retained")
    return OrderedDict(
        variable=variable, variable_label=label,
        unit_status=("UNRESOLVED - recorded scalar, no physical unit assigned"
                     if variable == "burn_rate_raw" else "as headed in source"),
        stratum=stratum, mode=mode, exclusion_rule=rule,
        n_total=stats["n_total"], n_used=stats["n_used"], n_missing=stats["n_missing"],
        n_approx_excluded=stats["n_approx_excluded"],
        mean=fc.fmt_num(stats["mean"]), std=fc.fmt_num(stats["std"]),
        min=fc.fmt_num(stats["min"]), q1=fc.fmt_num(stats["q1"]),
        median=fc.fmt_num(stats["median"]), q3=fc.fmt_num(stats["q3"]),
        max=fc.fmt_num(stats["max"]), iqr=fc.fmt_num(stats["iqr"]),
        quartile_method=fc.QUARTILE_METHOD, notes=note)


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# A. descriptive statistics
# ---------------------------------------------------------------------------
def analysis_descriptive(records):
    rows = []
    strata = OrderedDict(
        [("All", records)] + [(f, [r for r in records if r["fuel"] == f]) for f in fc.FUELS])
    for variable, label in fc.VARIABLES.items():
        for stratum, subset in strata.items():
            rows.append(stat_row(variable, label, stratum, "as_reported",
                                 fc.descriptive_stats(values(subset, variable))))
            screened = [r for r in subset if not fc.screened_out(r)]
            rows.append(stat_row(variable, label, stratum, "screened",
                                 fc.descriptive_stats(values(screened, variable)),
                                 note=f"screened n_records={len(screened)}"))
    return rows


# ---------------------------------------------------------------------------
# B. diameter analysis (initial diameter kept distinct from extinction diameter)
# ---------------------------------------------------------------------------
def iqr_outlier_flags(arr_stats):
    if arr_stats["q1"] is None:
        return None, None
    low = arr_stats["q1"] - 1.5 * arr_stats["iqr"]
    high = arr_stats["q3"] + 1.5 * arr_stats["iqr"]
    return low, high


def analysis_diameter(records):
    rows = []
    groups = OrderedDict()
    for fuel in fc.FUELS + ("All",):
        subset = records if fuel == "All" else [r for r in records if r["fuel"] == fuel]
        groups[f"fuel={fuel}"] = subset
        for outcome in fc.OUTCOMES:
            groups[f"fuel={fuel},outcome={outcome}"] = [
                r for r in subset if r["test_end"] == outcome]
    for glabel, subset in groups.items():
        for variable, label in (("d0_mm", "Droplet initial diameter (mm)"),
                                ("d_ext_mm", "Visible flame extinction diameter (mm)")):
            for mode, sub2 in (("as_reported", subset),
                               ("screened", [r for r in subset if not fc.screened_out(r)])):
                st = fc.descriptive_stats(values(sub2, variable))
                low, high = iqr_outlier_flags(st)
                arr = [v for v, a in values(sub2, variable) if v is not None and not a]
                n_low = sum(1 for v in arr if low is not None and v < low)
                n_high = sum(1 for v in arr if high is not None and v > high)
                rows.append(OrderedDict(
                    analysis="B_diameter", group=glabel, variable=variable,
                    variable_label=label, mode=mode,
                    n_total=st["n_total"], n_used=st["n_used"], n_missing=st["n_missing"],
                    n_approx_excluded=st["n_approx_excluded"],
                    mean=fc.fmt_num(st["mean"]), std=fc.fmt_num(st["std"]),
                    min=fc.fmt_num(st["min"]), q1=fc.fmt_num(st["q1"]),
                    median=fc.fmt_num(st["median"]), q3=fc.fmt_num(st["q3"]),
                    max=fc.fmt_num(st["max"]), iqr=fc.fmt_num(st["iqr"]),
                    iqr_outlier_fence_low=fc.fmt_num(low), iqr_outlier_fence_high=fc.fmt_num(high),
                    n_iqr_outliers=n_low + n_high,
                     notes=("IQR fences are descriptive labels only, not exclusions"
                            + ("; screened excludes flagged implausible records"
                               if mode == "screened" else ""))))
    # d_ext/d0 ratio: dimensionless descriptive ratio on a visible-flame basis.
    # Identity enforced: n_total = stratum records, n_used = pairs with both
    # diameters (d0 != 0), n_missing = records without such a pair.
    for fuel in fc.FUELS + ("All",):
        subset = records if fuel == "All" else [r for r in records if r["fuel"] == fuel]
        pairs = [(r["d0_mm_val"], r["d_ext_mm_val"]) for r in subset
                 if r["d0_mm_val"] not in (None, 0.0) and r["d_ext_mm_val"] is not None]
        ratios = [b / a for a, b in pairs]
        screened_pairs = [(r["d0_mm_val"], r["d_ext_mm_val"]) for r in subset
                          if not fc.screened_out(r)
                          and r["d0_mm_val"] not in (None, 0.0) and r["d_ext_mm_val"] is not None]
        ratios_s = [b / a for a, b in screened_pairs]
        q = np.percentile(ratios, [25, 50, 75]) if ratios else [None, None, None]
        rows.append(OrderedDict(
            analysis="B_diameter_ratio", group=f"fuel={fuel}", variable="d_ext_over_d0",
            variable_label="visible flame extinction diameter / initial diameter (dimensionless)",
            mode="as_reported", n_total=len(subset), n_used=len(ratios),
            n_missing=len(subset) - len(ratios), n_approx_excluded=0,
            mean=fc.fmt_num(sum(ratios) / len(ratios) if ratios else None),
            std=fc.fmt_num(
                (sum((x - sum(ratios) / len(ratios)) ** 2 for x in ratios) / (len(ratios) - 1)) ** 0.5
                if len(ratios) > 1 else None),
            min=fc.fmt_num(min(ratios) if ratios else None),
            q1=fc.fmt_num(q[0]), median=fc.fmt_num(q[1]), q3=fc.fmt_num(q[2]),
            max=fc.fmt_num(max(ratios) if ratios else None),
            iqr=fc.fmt_num(q[2] - q[0]) if ratios else "",
            iqr_outlier_fence_low="", iqr_outlier_fence_high="", n_iqr_outliers="",
            notes=("screened variant n_used=%d MEAN=%s (excludes pressure/zero-diameter/"
                   "gt-diameter flags)"
                   % (len(ratios_s),
                      fc.fmt_num(sum(ratios_s) / len(ratios_s) if ratios_s else None)))))

    # Mann-Whitney fuel contrast per variable (nonparametric, independent-sample
    # assumption caveated; exploratory)
    for variable, label in (("d0_mm", "initial diameter (mm)"),
                            ("d_ext_mm", "visible flame extinction diameter (mm)")):
        x = [r[variable + "_val"] for r in records
             if r["fuel"] == "Methanol" and r[variable + "_val"] is not None
             and not r[variable + "_approx"]]
        y = [r[variable + "_val"] for r in records
             if r["fuel"] == "Heptane" and r[variable + "_val"] is not None
             and not r[variable + "_approx"]]
        u, p, nx, ny = fc.mann_whitney_u(x, y)
        rows.append(OrderedDict(
            analysis="B_diameter_fuel_contrast", group="Methanol vs Heptane",
            variable=variable, variable_label=f"Mann-Whitney U: {label}, fuel contrast",
            mode="as_reported", n_total=len(x) + len(y), n_used=len(x) + len(y),
            n_missing="", n_approx_excluded=0,
            mean=fc.fmt_num(u, 1), std=fc.fmt_p(p), min="", q1="", median="",
            q3="", max="", iqr="", iqr_outlier_fence_low="", iqr_outlier_fence_high="",
            n_iqr_outliers="",
            notes=(f"U={u} p={p:.5f} n_MeOH={nx} n_Hep={ny}; two-sided asymptotic "
                   "rank-sum test with tie correction and continuity correction; "
                   "DESCRIPTIVE exploratory contrast only; independence caveat "
                   "(193F001 collision); no multiplicity correction applied; "
                   "duplicate-sensitivity variants follow below")))
    # Sensitivity to the 193F001 identifier collision: two distinct records
    # share that identifier and may not be independent runs. Recompute each
    # fuel contrast with each of the two records removed so readers can see
    # whether conclusions depend on that pair.
    collision_rows = [r for r in records if r["flex_identifier"] == "193F001"]
    for i, dropped in enumerate(collision_rows, start=1):
        keep = [r for r in records if r is not dropped]
        for variable, label in (("d0_mm", "initial diameter (mm)"),
                                ("d_ext_mm", "visible flame extinction diameter (mm)")):
            x = [r[variable + "_val"] for r in keep
                 if r["fuel"] == "Methanol" and r[variable + "_val"] is not None
                 and not r[variable + "_approx"]]
            y = [r[variable + "_val"] for r in keep
                 if r["fuel"] == "Heptane" and r[variable + "_val"] is not None
                 and not r[variable + "_approx"]]
            u, p, nx, ny = fc.mann_whitney_u(x, y)
            rows.append(OrderedDict(
                analysis="B_diameter_sensitivity_duplicate", group="Methanol vs Heptane",
                variable=variable,
                variable_label=f"MWU sensitivity: {label}, excluding collision record {i}",
                mode="screened", n_total=len(keep), n_used=nx + ny, n_missing="",
                n_approx_excluded=0, mean=fc.fmt_num(u, 1), std=fc.fmt_p(p),
                min="", q1="", median="", q3="", max="", iqr="",
                iqr_outlier_fence_low="", iqr_outlier_fence_high="", n_iqr_outliers="",
                notes=(f"U={u} p={p:.5g} n_MeOH={nx} n_Hep={ny}; excludes FLEX Test "
                       f"#{dropped['flex_test_no']} (identifier 193F001 collision); "
                       "sensitivity analysis, not a primary result")))
    return rows


# ---------------------------------------------------------------------------
# C. burning-rate analysis (unit unresolved; descriptive associations only)
# ---------------------------------------------------------------------------
def analysis_burning_rate(records):
    rows = []
    groups = OrderedDict()
    for fuel in fc.FUELS + ("All",):
        subset = records if fuel == "All" else [r for r in records if r["fuel"] == fuel]
        groups[f"fuel={fuel}"] = subset
        for outcome in fc.OUTCOMES:
            groups[f"fuel={fuel},outcome={outcome}"] = [
                r for r in subset if r["test_end"] == outcome]
    for glabel, subset in groups.items():
        st = fc.descriptive_stats(values(subset, "burn_rate_raw"))
        rows.append(OrderedDict(
            analysis="C_burning_rate", group=glabel,
            variable="burn_rate_raw",
            variable_label="Burning rate as recorded (UNIT UNRESOLVED)",
            mode="as_reported", n_total=st["n_total"], n_used=st["n_used"],
            n_missing=st["n_missing"], n_approx_excluded=st["n_approx_excluded"],
            mean=fc.fmt_num(st["mean"]), std=fc.fmt_num(st["std"]),
            min=fc.fmt_num(st["min"]), q1=fc.fmt_num(st["q1"]),
            median=fc.fmt_num(st["median"]), q3=fc.fmt_num(st["q3"]),
            max=fc.fmt_num(st["max"]), iqr=fc.fmt_num(st["iqr"]),
            notes=("Recorded scalar only. No physical unit is assigned; no burning-rate "
                   "or d2-law constant is computed; all unit-dependent conclusions provisional.")))
    # Spearman associations (dimensionless, rank-based; descriptive only)
    assoc_targets = [("d0_mm", "initial diameter (mm)"),
                     ("burn_time_s", "burn time (s)"),
                     ("d_ext_mm", "visible flame extinction diameter (mm)"),
                     ("o2_mf", "O2 mole fraction"),
                     ("pressure_mmHg", "ambient pressure (mmHg)")]
    for fuel in fc.FUELS + ("All",):
        subset = records if fuel == "All" else [r for r in records if r["fuel"] == fuel]
        for key, label in assoc_targets:
            pairs = [(r["burn_rate_raw_val"], r[key + "_val"]) for r in subset
                     if r["burn_rate_raw_val"] is not None and r[key + "_val"] is not None
                     and not r["burn_rate_raw_approx"]]
            rho, p = fc.spearman_rho([a for a, _ in pairs], [b for _, b in pairs])
            rows.append(OrderedDict(
                analysis="C_burning_rate_association", group=f"fuel={fuel}",
                variable=f"burn_rate_raw_vs_{key}",
                variable_label=f"Spearman rank association: burning rate (unit unresolved) vs {label}",
                mode="as_reported", n_total=len(subset), n_used=len(pairs),
                n_missing="", n_approx_excluded="",
                mean=fc.fmt_num(rho, 3), std=fc.fmt_p(p),
                min="", q1="", median="", q3="", max="", iqr="",
                notes=("Rank correlation is dimensionless and therefore unit-invariant; "
                       "DESCRIPTIVE ASSOCIATION ONLY, no causal or mechanistic claim; "
                       "multiplicity unaddressed; identifier collision 193F001 may violate independence.")))
    return rows


# ---------------------------------------------------------------------------
# D. duration analysis (approximate values preserved and separated)
# ---------------------------------------------------------------------------
def analysis_duration(records):
    rows = []
    approx_records = [r for r in records if r["burn_time_s_approx"]]
    groups = OrderedDict()
    for fuel in fc.FUELS + ("All",):
        subset = records if fuel == "All" else [r for r in records if r["fuel"] == fuel]
        groups[f"fuel={fuel}"] = subset
        for outcome in fc.OUTCOMES:
            groups[f"fuel={fuel},outcome={outcome}"] = [
                r for r in subset if r["test_end"] == outcome]
    for glabel, subset in groups.items():
        st = fc.descriptive_stats(values(subset, "burn_time_s"))
        rows.append(OrderedDict(
            analysis="D_duration", group=glabel, variable="burn_time_s",
            variable_label="Burn time (s); exact values only",
            mode="as_reported", n_total=st["n_total"], n_used=st["n_used"],
            n_missing=st["n_missing"], n_approx_excluded=st["n_approx_excluded"],
            mean=fc.fmt_num(st["mean"]), std=fc.fmt_num(st["std"]),
            min=fc.fmt_num(st["min"]), q1=fc.fmt_num(st["q1"]),
            median=fc.fmt_num(st["median"]), q3=fc.fmt_num(st["q3"]),
            max=fc.fmt_num(st["max"]), iqr=fc.fmt_num(st["iqr"]),
            notes=("Approximate (~) records excluded from statistics and listed separately"
                   if st["n_approx_excluded"] else "")))
    for r in approx_records:
        rows.append(OrderedDict(
            analysis="D_duration_approximate_values", group=f"fuel={r['fuel']}",
            variable="burn_time_s",
            variable_label="Burn time (s) recorded with '~' approximation marker",
            mode="as_reported_approximate", n_total=1, n_used=0, n_missing=0,
            n_approx_excluded=1, mean=r["burn_time_s"], std="", min=r["burn_time_s"],
            q1="", median="", q3="", max=r["burn_time_s"], iqr="",
            notes=(f"identifier={r['flex_identifier']} test#{r['flex_test_no']} "
                   "value kept as recorded, flagged approximate; excluded from all "
                   "group statistics above")))
    # Mann-Whitney fuel contrast (exploratory; independence caveat 193F001)
    x = [r["burn_time_s_val"] for r in records
         if r["fuel"] == "Methanol" and r["burn_time_s_val"] is not None
         and not r["burn_time_s_approx"]]
    y = [r["burn_time_s_val"] for r in records
         if r["fuel"] == "Heptane" and r["burn_time_s_val"] is not None
         and not r["burn_time_s_approx"]]
    u, p, nx, ny = fc.mann_whitney_u(x, y)
    rows.append(OrderedDict(
        analysis="D_duration_fuel_contrast", group="Methanol vs Heptane",
        variable="burn_time_s",
        variable_label="Mann-Whitney U: burn time (s), fuel contrast, exact values only",
        mode="as_reported", n_total=nx + ny, n_used=nx + ny, n_missing="",
        n_approx_excluded=2,
        mean=fc.fmt_num(u, 1), std=fc.fmt_p(p), min="", q1="", median="",
        q3="", max="", iqr="",
        notes=(f"U={u} p={p:.5f} n_MeOH={nx} n_Hep={ny}; two-sided asymptotic rank-sum "
               "test, tie- and continuity-corrected; approximate (~) values excluded; "
               "DESCRIPTIVE exploratory contrast only; independence caveat "
               "(193F001 collision); no multiplicity correction applied")))
    # Sensitivity to the 193F001 identifier collision for burn time
    collision_rows = [r for r in records if r["flex_identifier"] == "193F001"]
    for i, dropped in enumerate(collision_rows, start=1):
        keep = [r for r in records if r is not dropped]
        x = [r["burn_time_s_val"] for r in keep
             if r["fuel"] == "Methanol" and r["burn_time_s_val"] is not None
             and not r["burn_time_s_approx"]]
        y = [r["burn_time_s_val"] for r in keep
             if r["fuel"] == "Heptane" and r["burn_time_s_val"] is not None
             and not r["burn_time_s_approx"]]
        u, p, nx, ny = fc.mann_whitney_u(x, y)
        rows.append(OrderedDict(
            analysis="D_duration_sensitivity_duplicate", group="Methanol vs Heptane",
            variable="burn_time_s",
            variable_label=f"MWU sensitivity: burn time (s), excluding collision record {i}",
            mode="screened", n_total=len(keep), n_used=nx + ny, n_missing="",
            n_approx_excluded=2,
            mean=fc.fmt_num(u, 1), std=fc.fmt_p(p), min="", q1="", median="",
            q3="", max="", iqr="",
            notes=(f"U={u} p={p:.5g} n_MeOH={nx} n_Hep={ny}; excludes FLEX Test "
                   f"#{dropped['flex_test_no']} (identifier 193F001 collision); "
                   "sensitivity analysis, not a primary result")))
    return rows


# ---------------------------------------------------------------------------
# E. outcome analysis (labels kept distinct from measured quantities)
# ---------------------------------------------------------------------------
def analysis_outcome(records):
    rows = []
    for fuel in fc.FUELS + ("All",):
        subset = records if fuel == "All" else [r for r in records if r["fuel"] == fuel]
        n = len(subset)
        for outcome in fc.OUTCOMES:
            k = sum(1 for r in subset if r["test_end"] == outcome)
            rows.append(OrderedDict(
                analysis="E_outcome", group=f"fuel={fuel}", metric="outcome_count",
                outcome=outcome, n_fuel=n, count=k,
                proportion=fc.fmt_num(k / n, 4),
                notes="recorded experimental outcome label"))
        # measurement availability within each outcome (labels vs measurements)
        for outcome in fc.OUTCOMES:
            sub = [r for r in subset if r["test_end"] == outcome]
            have = sum(1 for r in sub if r["d_ext_mm_val"] is not None)
            rows.append(OrderedDict(
                analysis="E_outcome", group=f"fuel={fuel}",
                metric=f"d_ext_measured_within_{outcome}", outcome=outcome,
                n_fuel=len(sub), count=have, proportion=fc.fmt_num(have / len(sub), 4) if sub else "",
                notes=("visible flame extinction diameter is a MEASUREMENT, distinct from "
                       "the outcome label; label without measurement is never imputed")))
    # Fisher exact tests: each outcome vs rest, methanol vs heptane (exploratory)
    meoh = [r for r in records if r["fuel"] == "Methanol"]
    hep = [r for r in records if r["fuel"] == "Heptane"]
    for outcome in fc.OUTCOMES:
        a = sum(1 for r in meoh if r["test_end"] == outcome)
        b = len(meoh) - a
        c = sum(1 for r in hep if r["test_end"] == outcome)
        d = len(hep) - c
        p, _ = fc.fisher_exact_2x2(a, b, c, d)
        rows.append(OrderedDict(
            analysis="E_outcome_fuel_test", group="All",
            metric="fisher_exact_outcome_vs_rest", outcome=outcome,
            n_fuel=f"MeOH {len(meoh)} / Hep {len(hep)}",
            count=f"a={a},b={b},c={c},d={d}",
            proportion=fc.fmt_p(p),
            notes=("two-sided Fisher exact, outcome vs rest, unadjusted; Holm-adjusted "
                   "values in p_holm below; exploratory only, independence caveat")))
    # Holm adjustment across the three outcome tests
    tests = [r for r in rows if r["metric"] == "fisher_exact_outcome_vs_rest"]
    pvals = [float(r["proportion"]) for r in tests]
    adj = fc.holm_adjust(pvals)
    for r, a in zip(tests, adj):
        rows.append(OrderedDict(
            analysis="E_outcome_fuel_test", group="All",
            metric="holm_adjusted_p", outcome=r["outcome"], n_fuel=r["n_fuel"],
            count=r["count"], proportion=fc.fmt_p(a),
            notes="Holm-Bonferroni adjustment across the 3 outcome contrasts"))
    return rows


# ---------------------------------------------------------------------------
# F. condition analysis (confounding made explicit)
# ---------------------------------------------------------------------------
def analysis_condition(records):
    rows = []
    families = OrderedDict()
    for r in records:
        families.setdefault(fc.condition_family(r), []).append(r)
    for fam, subset in families.items():
        bands = Counter(fc.pressure_band(r["pressure_mmHg_val"]) for r in subset)
        n_meoh = sum(1 for r in subset if r["fuel"] == "Methanol")
        n_hep = sum(1 for r in subset if r["fuel"] == "Heptane")
        complete = sum(1 for r in subset
                       if all(r[k + "_val"] is not None for k in fc.CORE_MEASUREMENT_KEYS))
        rows.append(OrderedDict(
            analysis="F_condition_family", family=fam,
            diluent=fc.diluent_type(subset[0]),
            o2_mf=subset[0]["o2_mf"],
            o2_n2_co2_he_mf=(f"{subset[0]['o2_mf']}/{subset[0]['n2_mf']}/"
                             f"{subset[0]['co2_mf']}/{subset[0]['he_mf']}"),
            pressure_bands=";".join(f"{b}:{n}" for b, n in sorted(bands.items())),
            n_total=len(subset), n_methanol=n_meoh, n_heptane=n_hep,
            n_co2_substituted="", n_he_substituted="", n2_sets="",
            n_complete_measurements=complete,
            confounded_flag=("pressure-confounded: mixture family occurs only at "
                             + ";".join(sorted(bands))
                             if any(b in ("800-2100 mmHg", ">2100 mmHg") for b in bands)
                             else "check cross-band availability before claiming pressure effects"),
            comparability_verdict="", notes="mole fractions as reported; not renormalised"))
    # matched-O2 diluent-substitution cells: CO2-substituted vs He-substituted.
    # Comparability requires (a) shared pressure bands, (b) matching N2 balance
    # as reported, and (c) enough records on BOTH sides to support any contrast.
    MIN_CELL_SIDE_N = 3
    by_o2 = OrderedDict()
    for fam, subset in families.items():
        o2 = subset[0]["o2_mf"]
        dt = fc.diluent_type(subset[0])
        if dt in ("CO2", "He"):
            by_o2.setdefault(o2, {}).setdefault(dt, []).append(subset)
    for o2, kinds in sorted(by_o2.items()):
        if "CO2" in kinds and "He" in kinds:
            co2_recs = [r for s in kinds["CO2"] for r in s]
            he_recs = [r for s in kinds["He"] for r in s]
            co2_bands = Counter(fc.pressure_band(r["pressure_mmHg_val"]) for r in co2_recs)
            he_bands = Counter(fc.pressure_band(r["pressure_mmHg_val"]) for r in he_recs)
            shared = sorted(set(co2_bands) & set(he_bands))
            n2_co2 = sorted({r["n2_mf"] for r in co2_recs})
            n2_he = sorted({r["n2_mf"] for r in he_recs})
            n2_match = set(n2_co2) == set(n2_he)
            enough = (len(co2_recs) >= MIN_CELL_SIDE_N and len(he_recs) >= MIN_CELL_SIDE_N)
            if not enough:
                verdict = (f"NOT comparable: insufficient records "
                           f"(CO2-side n={len(co2_recs)}, He-side n={len(he_recs)}, "
                           f"minimum required {MIN_CELL_SIDE_N} per side)")
            elif not shared:
                verdict = "NOT directly comparable: no shared pressure band"
            elif not n2_match:
                verdict = (f"comparable only within shared pressure band(s) "
                           f"{';'.join(shared)} AND within matching N2 balances "
                           f"{set(n2_co2)}: N2 balances differ across sides "
                           f"(CO2-side {n2_co2} vs He-side {n2_he})")
            else:
                verdict = (f"comparable within shared pressure band(s) "
                           f"{';'.join(shared)} and identical N2 balance set {set(n2_co2)} "
                           "as reported")
            rows.append(OrderedDict(
                analysis="F_diluent_substitution_cell", family=f"O2={o2}",
                diluent="CO2 vs He", o2_mf=o2,
                o2_n2_co2_he_mf=(f"CO2-side N2 {n2_co2} vs He-side N2 {n2_he}"),
                pressure_bands=("CO2:" + ";".join(f"{b}:{n}" for b, n in sorted(co2_bands.items()))
                                + " | He:" + ";".join(f"{b}:{n}" for b, n in sorted(he_bands.items()))),
                n_total=len(co2_recs) + len(he_recs),
                n_methanol="", n_heptane="",
                n_co2_substituted=len(co2_recs), n_he_substituted=len(he_recs),
                n2_sets=f"CO2-side {n2_co2} vs He-side {n2_he}",
                n_complete_measurements="",
                confounded_flag=("pressure bands as reported for each side; "
                                 "comparability evaluated within shared bands only"),
                comparability_verdict=verdict,
                notes=("matched-O2 diluent-substitution cell; n_co2_substituted counts the "
                       "CO2-substituted family records, n_he_substituted the He-substituted "
                       "ones (these are NOT fuel counts); mole fractions as reported, "
                       "not renormalised; minimum per-side n for any contrast is %d"
                       % MIN_CELL_SIDE_N)))
    return rows


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def figures(records):
    os.makedirs(FIG_DIR, exist_ok=True)
    written = []

    def save(fig, name):
        path = os.path.join(FIG_DIR, name)
        fig.savefig(path)
        plt.close(fig)
        written.append(name)

    # fig01: initial diameter distributions by fuel (all reported values)
    fig, ax = plt.subplots()
    for fuel in fc.FUELS:
        vals = [r["d0_mm_val"] for r in records
                if r["fuel"] == fuel and r["d0_mm_val"] is not None]
        ax.hist(vals, bins=24, alpha=0.55, color=FUEL_COLORS[fuel], label=f"{fuel} (n={len(vals)})")
    ax.set_xlabel("Droplet initial diameter (mm)")
    ax.set_ylabel("Count of records")
    ax.set_title("Initial droplet diameter distribution by fuel (all reported values)")
    ax.legend()
    save(fig, "fig01_initial_diameter_by_fuel.png")

    # fig02: fuel comparison with box + points (axis starts at 0)
    fig, ax = plt.subplots()
    data, labels = [], []
    rng = np.random.default_rng(20241112)
    for i, fuel in enumerate(fc.FUELS):
        vals = [r["d0_mm_val"] for r in records
                if r["fuel"] == fuel and r["d0_mm_val"] is not None]
        data.append(vals)
        labels.append(f"{fuel}\nn={len(vals)}")
        ax.scatter(np.full(len(vals), i) + rng.uniform(-0.08, 0.08, len(vals)), vals,
                   s=12, alpha=0.6, color=FUEL_COLORS[fuel], edgecolors="none", zorder=3)
    ax.boxplot(data, tick_labels=labels, showfliers=True, widths=0.35, zorder=2)
    ax.set_ylabel("Droplet initial diameter (mm)")
    ax.set_ylim(bottom=0)
    ax.set_title("Initial diameter by fuel (box=IQR, line=median; axis from zero; jittered points shown)")
    save(fig, "fig02_diameter_box_by_fuel.png")

    # fig03: burn duration by fuel; approximate values marked distinctly
    fig, ax = plt.subplots()
    for fuel in fc.FUELS:
        vals = [r["burn_time_s_val"] for r in records
                if r["fuel"] == fuel and r["burn_time_s_val"] is not None
                and not r["burn_time_s_approx"]]
        ax.hist(vals, bins=30, alpha=0.55, color=FUEL_COLORS[fuel],
                label=f"{fuel} exact (n={len(vals)})")
        approx = [r["burn_time_s_val"] for r in records
                  if r["fuel"] == fuel and r["burn_time_s_approx"]]
        if approx:
            ax.scatter(approx, [ax.get_ylim()[1] * 0.02] * len(approx), marker="D",
                       color=APPROX_COLOR, zorder=5,
                       label=f"{fuel} approximate (~), excluded from stats (n={len(approx)})")
    ax.set_xlabel("Burn time (s)")
    ax.set_ylabel("Count of records")
    ax.set_title("Burn duration by fuel; approximate (~) values marked, not pooled")
    ax.legend()
    save(fig, "fig03_burn_duration_by_fuel.png")

    # fig04: outcome distribution by fuel (bars from zero, counts labelled)
    fig, ax = plt.subplots()
    width = 0.38
    x = range(len(fc.OUTCOMES))
    for i, fuel in enumerate(fc.FUELS):
        subset = [r for r in records if r["fuel"] == fuel]
        counts = [sum(1 for r in subset if r["test_end"] == o) for o in fc.OUTCOMES]
        bars = ax.bar([xx + (i - 0.5) * width for xx in x], counts, width,
                      color=FUEL_COLORS[fuel], label=f"{fuel} (n={len(subset)})")
        for b, c in zip(bars, counts):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1,
                    f"{c}\n({c / len(subset):.0%})", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(fc.OUTCOMES)
    ax.set_ylabel("Count of records")
    ax.set_title("Recorded experimental outcome labels by fuel (labels, not measured quantities)")
    ax.legend()
    save(fig, "fig04_outcome_distribution.png")

    # fig05: condition coverage (O2 vs diluent; pressure vs O2)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axes[0]
    fam_sizes = Counter(fc.condition_family(r) for r in records)
    for r in records:
        dil = fc.diluent_type(r)
        y = r["co2_mf_val"] if dil == "CO2" else (r["he_mf_val"] if dil == "He" else 0.0)
        if y is None:
            y = 0.0
        ax.scatter(r["o2_mf_val"], y, s=18 + 2.6 * fam_sizes[fc.condition_family(r)],
                   color=FUEL_COLORS[r["fuel"]], alpha=0.6, edgecolors="none",
                   marker="o" if dil == "CO2" else ("^" if dil == "He" else "s"))
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("O2 initial mole fraction (as reported)")
    ax.set_ylabel("CO2 (circle) or He (triangle) initial mole fraction")
    ax.set_title("Condition coverage: O2 vs inert diluent\n(point size scales with records in the mixture family; colour = fuel)")
    ax2 = axes[1]
    for r in records:
        flagged = "pressure_reported_zero" in r["flags"]
        ax2.scatter(r["o2_mf_val"], r["pressure_mmHg_val"], s=20,
                    color=FLAG_COLOR if flagged else FUEL_COLORS[r["fuel"]],
                    marker="x" if flagged else "o",
                    edgecolors="none" if not flagged else None,
                    alpha=0.65)
    ax2.scatter([], [], marker="x", color=FLAG_COLOR, label="flagged 0 mmHg placeholder (C11M201)")
    ax2.axhline(800, color="red", lw=0.8, ls="--")
    ax2.text(0.02, 830, "800 mmHg band boundary", color="red", fontsize=7.5,
             transform=ax2.get_yaxis_transform())
    ax2.set_xlabel("O2 initial mole fraction (as reported)")
    ax2.set_ylabel("Ambient pressure (mmHg, as reported)")
    ax2.set_title("Pressure vs O2: the 9 records above 800 mmHg\nbelong to a single CO2-diluted family (confounded)")
    ax2.legend(loc="upper left", fontsize=7.5)
    for ax_ in axes:
        ax_.set_xlim(left=0.10)
    save(fig, "fig05_condition_coverage.png")

    # fig06: missingness by variable (stacked by fuel)
    fig, ax = plt.subplots()
    var_labels = ["Ambient pressure", "O2 mole fraction", "N2 mole fraction",
                  "CO2 mole fraction", "He mole fraction", "Initial diameter (mm)",
                  "Extinction diameter (mm)", "Burning rate (unit unresolved)",
                  "Burn time (s)", "Test GMT time"]
    keys = ["pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf", "d0_mm",
            "d_ext_mm", "burn_rate_raw", "burn_time_s", "test_gmt"]
    meoh_counts = [sum(1 for r in records if r["fuel"] == "Methanol" and fc.is_missing(r[k]))
                   for k in keys]
    hep_counts = [sum(1 for r in records if r["fuel"] == "Heptane" and fc.is_missing(r[k]))
                  for k in keys]
    ypos = range(len(keys))
    ax.barh(ypos, meoh_counts, color=FUEL_COLORS["Methanol"], label="Methanol (n=157)")
    ax.barh(ypos, hep_counts, left=meoh_counts, color=FUEL_COLORS["Heptane"], label="Heptane (n=117)")
    for i, (m, h) in enumerate(zip(meoh_counts, hep_counts)):
        if m + h:
            ax.text(m + h + 1, i, f"{m}+{h}", va="center", fontsize=7.5)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(var_labels)
    ax.invert_yaxis()
    ax.set_xlabel("Records with value not reported (includes 0x96 blank markers)")
    ax.set_title("Missingness by variable and fuel (missing is never imputed or zero-filled)")
    ax.legend(loc="lower right")
    save(fig, "fig06_missingness_by_variable.png")

    # fig07: visible flame extinction diameter by outcome and fuel
    fig, axes = plt.subplots(1, len(fc.OUTCOMES), figsize=(11, 4.2), sharey=True)
    rng = np.random.default_rng(19700305)
    for ax, outcome in zip(axes, fc.OUTCOMES):
        data, labels = [], []
        for i, fuel in enumerate(fc.FUELS):
            vals = [r["d_ext_mm_val"] for r in records
                    if r["fuel"] == fuel and r["test_end"] == outcome
                    and r["d_ext_mm_val"] is not None and not r["d_ext_mm_approx"]]
            data.append(vals)
            labels.append(f"{fuel}\nn={len(vals)}")
            if vals:
                ax.scatter(np.full(len(vals), i + 1) + rng.uniform(-0.08, 0.08, len(vals)),
                           vals, s=12, alpha=0.6, color=FUEL_COLORS[fuel],
                           edgecolors="none", zorder=3)
            zeros = [r["d_ext_mm_val"] for r in records
                     if r["fuel"] == fuel and r["test_end"] == outcome
                     and r["d_ext_mm_val"] == 0.0]
            for z in zeros:
                ax.scatter([i + 1], [z], marker="x", s=45, color=FLAG_COLOR, zorder=4)
        positions = [i + 1 for i in range(len(fc.FUELS)) if data[i]]
        if positions:
            ax.boxplot([d for d in data if d], positions=positions, widths=0.35,
                       showfliers=True, zorder=2)
        ax.set_xticks([1, 2])
        ax.set_xticklabels(labels)
        ax.set_title(f"Outcome recorded as {outcome}")
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("Visible flame extinction diameter (mm)")
    fig.suptitle("Visible flame extinction diameter by recorded outcome and fuel "
                 "(x = flagged 0 mm placeholder, retained not dropped)")
    save(fig, "fig07_extinction_diameter_by_outcome.png")
    return written


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    csv_path = os.path.join(ROOT, fc.CSV_PATH)
    digest = fc.sha256_of(csv_path)
    hash_ok = digest == fc.EXPECTED_CSV_SHA256
    records = fc.load_records(csv_path)
    validation = validate(records)
    print(f"[input] {csv_path} sha256={digest} expected_match={hash_ok}")
    if not hash_ok:
        raise fc.SourceDataError("raw CSV sha256 does not match the audited Phase 1 value")
    print(f"[input] validated: {validation}")

    outputs = OrderedDict()
    csv_outputs = OrderedDict([
        ("descriptive_statistics.csv", analysis_descriptive(records)),
        ("diameter_analysis.csv", analysis_diameter(records)),
        ("burning_rate_analysis.csv", analysis_burning_rate(records)),
        ("duration_analysis.csv", analysis_duration(records)),
        ("outcome_analysis.csv", analysis_outcome(records)),
        ("condition_analysis.csv", analysis_condition(records)),
    ])
    for name, rows in csv_outputs.items():
        path = os.path.join(OUT_DIR, name)
        write_csv(path, rows)
        outputs[name] = dict(path=os.path.relpath(path, ROOT), rows=len(rows),
                             sha256=fc.sha256_of(path))
        print(f"[csv] {name}: {len(rows)} rows")

    figs = figures(records)
    for name in figs:
        path = os.path.join(FIG_DIR, name)
        outputs[f"figures/{name}"] = dict(path=os.path.relpath(path, ROOT),
                                          sha256=fc.sha256_of(path))
    print(f"[figures] {len(figs)} written")

    manifest = OrderedDict(
        analysis="FLEX PSI-69 exploratory analysis (Phase 2)",
        script=dict(name="run_analysis.py", version=SCRIPT_VERSION,
                    location=os.path.relpath(os.path.abspath(__file__), ROOT),
                    core_module="flex_core.py",
                    entrypoint="notebooks/.venv/bin/python analysis/exploratory/run_analysis.py"),
        inputs=[dict(path=fc.CSV_PATH, sha256=digest,
                     expected_sha256=fc.EXPECTED_CSV_SHA256, hash_match=hash_ok,
                     records=validation["n_records"],
                     encoding="latin-1 read byte-preserving; 0x96 byte (Windows-1252 "
                              "en-dash artifact) treated as a missing marker, not data")],
        validation=validation,
        environment=fc.python_env(),
        quartile_method=fc.QUARTILE_METHOD,
        integrity=dict(
            imputation="none - missing values are never filled or zero-filled",
            unit_conversion="none - burning-rate unit remains unresolved",
            flagged_records="retained in as_reported results; excluded only in screened variants with documentation",
            approximate_values="kept as recorded with approx flag; excluded from statistics and reported separately",
            modelling="no regression, no machine learning, no derived burning-rate constants"),
        outputs=outputs,
        limitations=[
            "Burning rate unit unresolved (source header 'Burning rate; mm'); no physically interpreted quantity computed.",
            "Pressure and diluent composition are confounded above 800 mmHg (single CO2-diluted family).",
            "Ambient temperature and per-run gravity are not recorded.",
            "Visible flame extinction diameter is not chemical extinction.",
            "Telemetry linkage covers 8/274 runs with three unreconciled clock domains.",
            "Identifier collision 193F001: two records share one identifier (independence caveat for tests).",
            "Missingness mechanism unknown; patterns reported descriptively only.",
        ],
    )
    import datetime
    manifest["executed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    man_path = os.path.join(OUT_DIR, "run_manifest.json")
    with open(man_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"[manifest] {man_path}")


if __name__ == "__main__":
    main()
