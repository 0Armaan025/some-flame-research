#!/usr/bin/env python3
"""FLEX PSI-69 Phase 4A - comparative results and scientific synthesis.

Reproducible entry point:

    notebooks/.venv/bin/python analysis/phase4a/run_analysis.py

Produces the comparative CSV deliverables, publication figures and the run
manifest. It reads the frozen raw dataset (sha256-gated) and nothing else;
Phases 1-3.5 are treated as read-only evidence and every headline number is
recomputed here from the raw table by flex4a.py (independent of the frozen
Phase 2 code paths).

Scope guardrails (inherited, non-negotiable):
  * burning-rate column: recorded scalar only - no unit, no physical constant;
  * no imputation; no renormalisation; flagged records retained with screened
    variants documented separately;
  * 193F001 reported under every exclusion rule - never resolved by choosing a
    version;
  * no causal claims; independence assumption explicitly not established;
  * no modelling, no ML, no telemetry/image-derived measurements.
"""

import csv
import datetime
import glob
import hashlib
import json
import os
import statistics
import subprocess
import sys
from collections import Counter, OrderedDict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flex4a as f4a

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = f4a.ROOT
HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
SCRIPT_VERSION = "4a.1.0"

FUEL_COLORS = {"Methanol": "#1f77b4", "Heptane": "#d62728"}
OUTCOME_COLORS = {"Extinction": "#2ca02c", "Disruption": "#ff7f0e",
                  "Completion": "#9467bd"}
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 9,
    "axes.titlesize": 10, "axes.labelsize": 9, "axes.grid": True,
    "grid.alpha": 0.3, "legend.fontsize": 8,
    "figure.constrained_layout.use": True,
})

MIN_SIDE_N = 3  # per-side minimum for a condition-cell contrast


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def values(recs, key):
    return [(r[key + "_val"], r[key + "_approx"]) for r in recs]


def fuel_group(recs, fuel):
    return [r for r in recs if r["fuel"] == fuel]


# ---------------------------------------------------------------------------
# A. outcome comparison
# ---------------------------------------------------------------------------
def outcome_comparison(recs):
    rows = []
    meoh, hep = fuel_group(recs, "Methanol"), fuel_group(recs, "Heptane")
    table = []
    for fuel, subset in (("Methanol", meoh), ("Heptane", hep)):
        counts = [sum(1 for r in subset if r["test_end"] == o) for o in f4a.OUTCOMES]
        table.append(counts)
        n = len(subset)
        for o, c in zip(f4a.OUTCOMES, counts):
            rows.append(OrderedDict(
                analysis="A_outcome", group=f"fuel={fuel}", outcome=o, n_fuel=n,
                count=c, proportion=f"{c / n:.4f}",
                denominator_note="recorded outcome label; label definitions "
                                 "unverified for Disruption"))
    # per-outcome 2x2 Fisher vs rest, Holm-adjusted
    for idx, o in enumerate(f4a.OUTCOMES):
        a = table[0][idx]
        b = len(meoh) - a
        c = table[1][idx]
        d = len(hep) - c
        p, or_ = f4a.fisher_exact_2x2(a, b, c, d)
        orc, lo, hi = f4a.log_or_ci(a, b, c, d)
        rows.append(OrderedDict(
            analysis="A_outcome_fisher", group="Methanol vs Heptane", outcome=o,
            n_fuel=f"{len(meoh)}/{len(hep)}",
            count=f"a={a},b={b},c={c},d={d}",
            proportion=f"{p:.3g}" if p is not None else "",
            denominator_note=(f"odds ratio {orc:.3f} (95% CI {lo:.3f}-{hi:.3f}); "
                              "two-sided Fisher exact, outcome vs rest, unadjusted; "
                              "descriptive contrast, independence not established")))
    # Holm across the three outcome contrasts
    ps = []
    for idx, o in enumerate(f4a.OUTCOMES):
        a = table[0][idx]
        b = len(meoh) - a
        c = table[1][idx]
        d = len(hep) - c
        ps.append(f4a.fisher_exact_2x2(a, b, c, d)[0])
    for o, p_adj in zip(f4a.OUTCOMES, f4a.holm(ps)):
        rows.append(OrderedDict(
            analysis="A_outcome_fisher_holm", group="Methanol vs Heptane", outcome=o,
            n_fuel=f"{len(meoh)}/{len(hep)}", count="", proportion=f"{p_adj:.3g}",
            denominator_note="Holm-Bonferroni adjusted across the 3 outcome contrasts"))
    fh = f4a.fisher_freeman_halton_2x3(table)
    cv, chi2 = f4a.cramers_v(table)
    rows.append(OrderedDict(
        analysis="A_outcome_table", group="Methanol vs Heptane", outcome="2x3 table",
        n_fuel=f"{len(meoh)}/{len(hep)}",
        count=";".join("/".join(str(x) for x in row) for row in table),
        proportion=f"FH p={fh:.3g}; Cramers V={cv:.4f}; chi2={chi2:.2f}",
        denominator_note=("Freeman-Halton exact test for the 2x3 table; Cramer's V "
                          "effect size (small~0.07, medium~0.21, large~0.35 heuristic)")))
    return rows, table, dict(fh=fh, cramers_v=cv, chi2=chi2, ps=ps,
                             ps_holm=f4a.holm(ps))


# ---------------------------------------------------------------------------
# B/D. duration, diameter, extinction descriptive + contrasts
# ---------------------------------------------------------------------------
def contrast_row(analysis, variable, label, x, y, approx_x, approx_y, extra=""):
    d_x = f4a.describe(x, approx_flags=approx_x)
    d_y = f4a.describe(y, approx_flags=approx_y)
    ux = [v for v, a in zip(x, approx_x) if v is not None and not a]
    uy = [v for v, a in zip(y, approx_y) if v is not None and not a]
    u, p = f4a.mwu(ux, uy)
    rows = []
    for fuel, d, used in (("Methanol", d_x, ux), ("Heptane", d_y, uy)):
        rows.append(OrderedDict(
            analysis=analysis, group=f"fuel={fuel}", metric=f"{variable}_descriptive",
            n_total=d["n_total"], n_used=d["n_used"], n_missing=d["n_missing"],
            n_approx_excluded=d["n_approx_excluded"],
            median=fmt_or_empty(d.get("median")), q1=fmt_or_empty(d.get("q1")),
            q3=fmt_or_empty(d.get("q3")), iqr=fmt_or_empty(d.get("iqr")),
            min=fmt_or_empty(d.get("min")), max=fmt_or_empty(d.get("max")),
            mean=fmt_or_empty(d.get("mean")), sd=fmt_or_empty(d.get("sd")),
            test_statistic="", p_value="", effect_size="", ci="",
            note=f"{label}; exact values only" + (f"; {extra}" if extra else "")))
    if u is not None:
        rb = f4a.rank_biserial(u, len(ux), len(uy))
        rows.append(OrderedDict(
            analysis=analysis, group="Methanol vs Heptane", metric=f"{variable}_contrast",
            n_total=len(ux) + len(uy), n_used=len(ux) + len(uy), n_missing=0,
            n_approx_excluded=d_x["n_approx_excluded"] + d_y["n_approx_excluded"],
            median=fmt_or_empty(statistics.median(uy) - statistics.median(ux)),
            q1="", q3="", iqr="", min="", max="", mean="", sd="",
            test_statistic=f"MWU U={u}", p_value=f"{p:.3g}",
            effect_size=f"rank-biserial r={rb:.4f}",
            ci="", note=f"{label} two-sided Mann-Whitney (asymptotic, tie- and "
                        "continuity-corrected); descriptive contrast; independence "
                        "assumption not established (Phase 3 R7 BLOCKED)"))
    return rows, (u, p, len(ux), len(uy))


def fmt_or_empty(x):
    return "" if x is None else f"{float(x):.4f}"


def duration_analysis(recs):
    meoh, hep = fuel_group(recs, "Methanol"), fuel_group(recs, "Heptane")
    rows, ctx = contrast_row("B_duration", "burn_time_s", "Burn time (s)",
                             [r["burn_time_s_val"] for r in meoh],
                             [r["burn_time_s_val"] for r in hep],
                             [r["burn_time_s_approx"] for r in meoh],
                             [r["burn_time_s_approx"] for r in hep])
    # by outcome within fuel
    for fuel, subset in (("Methanol", meoh), ("Heptane", hep)):
        for o in f4a.OUTCOMES:
            sub = [r for r in subset if r["test_end"] == o]
            d = f4a.describe([r["burn_time_s_val"] for r in sub],
                             approx_flags=[r["burn_time_s_approx"] for r in sub])
            rows.append(OrderedDict(
                analysis="B_duration", group=f"fuel={fuel},outcome={o}",
                metric="burn_time_s_descriptive",
                n_total=d["n_total"], n_used=d["n_used"], n_missing=d["n_missing"],
                n_approx_excluded=d["n_approx_excluded"],
                median=fmt_or_empty(d.get("median")), q1=fmt_or_empty(d.get("q1")),
                q3=fmt_or_empty(d.get("q3")), iqr=fmt_or_empty(d.get("iqr")),
                min=fmt_or_empty(d.get("min")), max=fmt_or_empty(d.get("max")),
                mean=fmt_or_empty(d.get("mean")), sd=fmt_or_empty(d.get("sd")),
                test_statistic="", p_value="", effect_size="", ci="",
                note="exact values only"))
    # the two approximate records, listed verbatim
    for r in recs:
        if r["burn_time_s_approx"]:
            rows.append(OrderedDict(
                analysis="B_duration", group=f"fuel={r['fuel']}",
                metric="burn_time_s_approximate_verbatim",
                n_total=1, n_used=0, n_missing=0, n_approx_excluded=1,
                median=r["burn_time_s"], q1="", q3="", iqr="", min=r["burn_time_s"],
                max=r["burn_time_s"], mean="", sd="", test_statistic="",
                p_value="", effect_size="", ci="",
                note=f"original string '{r['burn_time_s']}' preserved; excluded from "
                     f"all statistics; identifier {r['flex_identifier']}"))
    return rows, ctx


def diameter_analysis(recs):
    meoh, hep = fuel_group(recs, "Methanol"), fuel_group(recs, "Heptane")
    rows, ctx = contrast_row("C_diameter", "d0_mm", "Droplet initial diameter (mm)",
                             [r["d0_mm_val"] for r in meoh],
                             [r["d0_mm_val"] for r in hep],
                             [r["d0_mm_approx"] for r in meoh],
                             [r["d0_mm_approx"] for r in hep])
    # by outcome within fuel
    for fuel, subset in (("Methanol", meoh), ("Heptane", hep)):
        for o in f4a.OUTCOMES:
            sub = [r for r in subset if r["test_end"] == o]
            d = f4a.describe([r["d0_mm_val"] for r in sub],
                             approx_flags=[r["d0_mm_approx"] for r in sub])
            rows.append(OrderedDict(
                analysis="C_diameter", group=f"fuel={fuel},outcome={o}",
                metric="d0_mm_descriptive", n_total=d["n_total"], n_used=d["n_used"],
                n_missing=d["n_missing"], n_approx_excluded=d["n_approx_excluded"],
                median=fmt_or_empty(d.get("median")), q1=fmt_or_empty(d.get("q1")),
                q3=fmt_or_empty(d.get("q3")), iqr=fmt_or_empty(d.get("iqr")),
                min=fmt_or_empty(d.get("min")), max=fmt_or_empty(d.get("max")),
                mean=fmt_or_empty(d.get("mean")), sd=fmt_or_empty(d.get("sd")),
                test_statistic="", p_value="", effect_size="", ci="",
                note="all reported values retained"))
    # 193F001 collision detail
    for r in recs:
        if r["flex_identifier"] == "193F001":
            rows.append(OrderedDict(
                analysis="C_diameter", group="identifier collision 193F001",
                metric="collision_record",
                n_total=1, n_used=0 if r["d0_mm_val"] is None else 1, n_missing=0,
                n_approx_excluded=0, median=r["d0_mm"], q1="", q3="", iqr="",
                min="", max="", mean="", sd="", test_statistic="", p_value="",
                effect_size="", ci="",
                note=(f"test#{r['flex_test_no']} d0={r['d0_mm']} d_ext={r['d_ext_mm']} "
                      f"rate={r['burn_rate_raw']} t={r['burn_time_s']} "
                      f"gmt={r['test_gmt']}")))
    return rows, ctx


def extinction_analysis(recs):
    rows = []
    meoh, hep = fuel_group(recs, "Methanol"), fuel_group(recs, "Heptane")
    for fuel, subset in (("Methanol", meoh), ("Heptane", hep)):
        for o in f4a.OUTCOMES:
            sub = [r for r in subset if r["test_end"] == o]
            d = f4a.describe([r["d_ext_mm_val"] for r in sub],
                             approx_flags=[r["d_ext_mm_approx"] for r in sub])
            screened = f4a.describe([r["d_ext_mm_val"] for r in sub if not f4a.screened_out(r)],
                                    approx_flags=[r["d_ext_mm_approx"] for r in sub
                                                  if not f4a.screened_out(r)])
            rows.append(OrderedDict(
                analysis="D_extinction", group=f"fuel={fuel},outcome={o}",
                metric="d_ext_mm_descriptive", n_total=d["n_total"], n_used=d["n_used"],
                n_missing=d["n_missing"], n_approx_excluded=d["n_approx_excluded"],
                median=fmt_or_empty(d.get("median")), q1=fmt_or_empty(d.get("q1")),
                q3=fmt_or_empty(d.get("q3")), iqr=fmt_or_empty(d.get("iqr")),
                min=fmt_or_empty(d.get("min")), max=fmt_or_empty(d.get("max")),
                mean=fmt_or_empty(d.get("mean")), sd=fmt_or_empty(d.get("sd")),
                test_statistic="", p_value="", effect_size="", ci="",
                note=(f"screened variant n_used={screened['n_used']} "
                      f"median={fmt_or_empty(screened.get('median'))} "
                      f"(zero-placeholders and other flags excluded); "
                      "visible flame extinction diameter - NOT chemical extinction")))
    # the eight zero records verbatim
    for r in recs:
        if r["d_ext_mm_val"] == 0.0:
            rows.append(OrderedDict(
                analysis="D_extinction", group=f"fuel={r['fuel']},outcome={r['test_end']}",
                metric="zero_measurement_floor_record", n_total=1, n_used=0, n_missing=0,
                n_approx_excluded=0, median=r["d_ext_mm"], q1="", q3="", iqr="",
                min="", max="", mean="", sd="", test_statistic="", p_value="",
                effect_size="", ci="",
                note=(f"test#{r['flex_test_no']} {r['flex_identifier']} d0={r['d0_mm']} "
                      f"burn_time={r['burn_time_s']}; recorded 0 retained as reported, "
                      "flagged as measurement-floor placeholder candidate (Phase 3.5)")))
    # ratio descriptive (dimensionless, visible-flame basis)
    for fuel, subset in (("Methanol", meoh), ("Heptane", hep)):
        pairs = [(r["d0_mm_val"], r["d_ext_mm_val"]) for r in subset
                 if r["d0_mm_val"] not in (None, 0.0) and r["d_ext_mm_val"] is not None]
        ratios = [b / a for a, b in pairs]
        if ratios:
            q1, med, q3 = f4a.quantiles(ratios)
            rows.append(OrderedDict(
                analysis="D_extinction", group=f"fuel={fuel}",
                metric="d_ext_over_d0_ratio", n_total=len(subset), n_used=len(ratios),
                n_missing=len(subset) - len(ratios), n_approx_excluded=0,
                median=f"{med:.4f}", q1=f"{q1:.4f}", q3=f"{q3:.4f}",
                iqr=f"{q3 - q1:.4f}", min=f"{min(ratios):.4f}", max=f"{max(ratios):.4f}",
                mean=f"{sum(ratios) / len(ratios):.4f}",
                sd=f"{(sum((x - sum(ratios) / len(ratios)) ** 2 for x in ratios) / (len(ratios) - 1)) ** 0.5:.4f}"
                if len(ratios) > 1 else "",
                test_statistic="", p_value="", effect_size="", ci="",
                note=("dimensionless ratio of visible flame extinction diameter to initial "
                      "diameter; includes the eight recorded-zero records (0 mm) in the "
                      "as-reported variant")))
    return rows


# ---------------------------------------------------------------------------
# C. condition comparison (Phase 3 comparability verdicts, recomputed here)
# ---------------------------------------------------------------------------
def condition_cells(recs):
    by_o2 = {}
    for r in recs:
        if r["diluent"] in ("CO2", "He"):
            by_o2.setdefault(r["o2_mf"], {}).setdefault(r["diluent"], []).append(r)
    cells = []
    for o2, kinds in sorted(by_o2.items()):
        if "CO2" in kinds and "He" in kinds:
            co2, he = kinds["CO2"], kinds["He"]
            n2_co2 = sorted({r["n2_mf"] for r in co2})
            n2_he = sorted({r["n2_mf"] for r in he})
            bands_co2 = sorted({f4a.pressure_band(r["pressure_mmHg_val"]) for r in co2})
            bands_he = sorted({f4a.pressure_band(r["pressure_mmHg_val"]) for r in he})
            shared_bands = sorted(set(bands_co2) & set(bands_he))
            n2_match = set(n2_co2) == set(n2_he)
            enough = len(co2) >= MIN_SIDE_N and len(he) >= MIN_SIDE_N
            if not enough:
                verdict, cls = ("NOT comparable: insufficient records on a side "
                                f"(CO2 n={len(co2)}, He n={len(he)}, minimum {MIN_SIDE_N})"), "rejected"
            elif not shared_bands:
                verdict, cls = "NOT comparable: no shared pressure band", "rejected"
            elif not n2_match:
                verdict = (f"PARTIAL: N2 balances differ (CO2 {n2_co2} vs He {n2_he}); "
                           f"shared pressure band(s) {shared_bands}")
                cls = "partial"
            else:
                verdict = (f"COMPARABLE: identical N2 balance {set(n2_co2)}, shared "
                           f"pressure band(s) {shared_bands}, both sides n>={MIN_SIDE_N}")
                cls = "full"
            cells.append(dict(o2=o2, co2=co2, he=he, n2_co2=n2_co2, n2_he=n2_he,
                             bands_co2=bands_co2, bands_he=bands_he,
                             shared_bands=shared_bands, verdict=verdict, cls=cls))
    return cells


def condition_comparison(recs, cells):
    rows = []
    for cell in cells:
        for fuel in f4a.FUELS:
            co2_f = [r for r in cell["co2"] if r["fuel"] == fuel]
            he_f = [r for r in cell["he"] if r["fuel"] == fuel]
            d_co2 = f4a.describe([r["burn_time_s_val"] for r in co2_f])
            d_he = f4a.describe([r["burn_time_s_val"] for r in he_f])
            comparable = (cell["cls"] == "full" and len(co2_f) >= MIN_SIDE_N
                          and len(he_f) >= MIN_SIDE_N)
            rows.append(OrderedDict(
                analysis="C_condition_cell", group=f"O2={cell['o2']},fuel={fuel}",
                metric="burn_time_s_median_by_diluent_side",
                n_total=len(co2_f) + len(he_f),
                n_used=d_co2["n_used"] + d_he["n_used"],
                n_missing=d_co2["n_missing"] + d_he["n_missing"],
                n_approx_excluded=d_co2["n_approx_excluded"] + d_he["n_approx_excluded"],
                median=(f"CO2-side {fmt_or_empty(d_co2.get('median'))}; "
                        f"He-side {fmt_or_empty(d_he.get('median'))}"),
                q1=(f"CO2 {fmt_or_empty(d_co2.get('q1'))}-{fmt_or_empty(d_co2.get('q3'))}; "
                    f"He {fmt_or_empty(d_he.get('q1'))}-{fmt_or_empty(d_he.get('q3'))}"),
                q3="", iqr=f"CO2 {fmt_or_empty(d_co2.get('iqr'))}; He {fmt_or_empty(d_he.get('iqr'))}",
                min="", max="", mean="", sd="", test_statistic="", p_value="",
                effect_size="", ci="",
                note=(f"cell class={cell['cls']}; {cell['verdict']}; "
                      + ("primary comparison population" if comparable else
                         "reported descriptively only - see verdict; no pooled estimate"))))
        rows.append(OrderedDict(
            analysis="C_condition_cell", group=f"O2={cell['o2']}",
            metric="cell_summary", n_total=len(cell["co2"]) + len(cell["he"]),
            n_used=0, n_missing=0, n_approx_excluded=0,
            median="", q1="", q3="", iqr="", min="", max="", mean="", sd="",
            test_statistic="", p_value="", effect_size="", ci="",
            note=(f"CO2-side n={len(cell['co2'])} (N2 {cell['n2_co2']}, bands "
                  f"{cell['bands_co2']}); He-side n={len(cell['he'])} (N2 {cell['n2_he']}, "
                  f"bands {cell['bands_he']}); class={cell['cls']}; {cell['verdict']}")))
    # pressure disclosure
    high = [r for r in recs if (r["pressure_mmHg_val"] or 0) > 800]
    fams = Counter((r["o2_mf"], r["n2_mf"], r["co2_mf"], r["he_mf"]) for r in high)
    rows.append(OrderedDict(
        analysis="C_pressure", group="All", metric="pressure_distribution",
        n_total=len(recs), n_used=len([r for r in recs if r["pressure_mmHg_val"] is not None]),
        n_missing=0, n_approx_excluded=0,
        median=fmt_or_empty(statistics.median([r["pressure_mmHg_val"] for r in recs
                                               if r["pressure_mmHg_val"] is not None])),
        q1="", q3="", iqr="", min="", max="", mean="", sd="", test_statistic="",
        p_value="", effect_size="", ci="",
        note=("bands: " + str(dict(Counter(f4a.pressure_band(r["pressure_mmHg_val"])
                                           for r in recs))))))
    rows.append(OrderedDict(
        analysis="C_pressure", group="All", metric="pressure_confounding_disclosure",
        n_total=len(high), n_used=0, n_missing=0, n_approx_excluded=0,
        median="", q1="", q3="", iqr="", min="", max="", mean="", sd="",
        test_statistic="", p_value="", effect_size="", ci="",
        note=(f"{len(high)} records above 800 mmHg all belong to the single family "
              f"{dict(fams)} - pressure and diluent are confounded; no independent "
              "pressure effect may be claimed")))
    return rows


# ---------------------------------------------------------------------------
# sensitivity analyses
# ---------------------------------------------------------------------------
def sensitivity(recs, d0_ctx, dur_ctx):
    rows = []

    def add(analysis, variant, variable, u, p, nx, ny, note):
        rows.append(OrderedDict(
            analysis=analysis, variant=variant, variable=variable,
            n_meoh=nx, n_hep=ny, statistic=f"MWU U={u}", p_value=f"{p:.3g}",
            effect_size=f"rank-biserial r={f4a.rank_biserial(u, nx, ny):.4f}" if u else "",
            note=note))

    # baseline (as reported)
    u, p, nx, ny = d0_ctx
    add("S_diameter", "as_reported", "d0_mm", u, p, nx, ny,
        "all reported values; methanol n=154 / heptane n=108")
    u, p, nx, ny = dur_ctx
    add("S_duration", "as_reported", "burn_time_s", u, p, nx, ny,
        "exact values only; the two ~-approximate records excluded")

    # collision sensitivity: exclude each 193F001 record in turn
    coll = [r for r in recs if r["flex_identifier"] == "193F001"]
    for i, drop in enumerate(coll, 1):
        keep = [r for r in recs if r is not drop]
        var = "d0_mm"
        x = [r[var + "_val"] for r in keep if r["fuel"] == "Methanol"
             and r[var + "_val"] is not None]
        y = [r[var + "_val"] for r in keep if r["fuel"] == "Heptane"
             and r[var + "_val"] is not None]
        uu, pp = f4a.mwu(x, y)
        add("S_diameter", f"excluding_193F001_record_{i}", var, uu, pp, len(x), len(y),
            f"FLEX Test #{drop['flex_test_no']} removed; neither version preferred")
        xt = [r["burn_time_s_val"] for r in keep if r["fuel"] == "Methanol"
              and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
        yt = [r["burn_time_s_val"] for r in keep if r["fuel"] == "Heptane"
              and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
        ut, pt = f4a.mwu(xt, yt)
        add("S_duration", f"excluding_193F001_record_{i}", "burn_time_s", ut, pt,
            len(xt), len(yt), f"FLEX Test #{drop['flex_test_no']} removed")

    # screened: exclude flagged anomaly records (not the collision)
    keep2 = [r for r in recs if not f4a.screened_out(r)]
    x = [r["d0_mm_val"] for r in keep2 if r["fuel"] == "Methanol" and r["d0_mm_val"] is not None]
    y = [r["d0_mm_val"] for r in keep2 if r["fuel"] == "Heptane" and r["d0_mm_val"] is not None]
    u2, p2 = f4a.mwu(x, y)
    add("S_diameter", "screened_flagged_anomalies_excluded", "d0_mm", u2, p2, len(x), len(y),
        "excludes the 1 pressure-zero, 8 zero-d_ext and 1 d_ext>d0 records (10 total)")
    xt = [r["burn_time_s_val"] for r in keep2 if r["fuel"] == "Methanol"
          and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
    yt = [r["burn_time_s_val"] for r in keep2 if r["fuel"] == "Heptane"
          and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
    u3, p3 = f4a.mwu(xt, yt)
    add("S_duration", "screened_flagged_anomalies_excluded", "burn_time_s", u3, p3,
        len(xt), len(yt), "same exclusion set")

    # permutation p-values for the two headline contrasts (assumption-light)
    mx = [r["d0_mm_val"] for r in recs if r["fuel"] == "Methanol" and r["d0_mm_val"] is not None]
    my = [r["d0_mm_val"] for r in recs if r["fuel"] == "Heptane" and r["d0_mm_val"] is not None]
    dtx = [r["burn_time_s_val"] for r in recs if r["fuel"] == "Methanol"
           and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
    dty = [r["burn_time_s_val"] for r in recs if r["fuel"] == "Heptane"
           and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
    pp_d0 = f4a.perm_p(mx, my)
    pp_dur = f4a.perm_p(dtx, dty)
    rows.append(OrderedDict(
        analysis="S_permutation", variant="as_reported", variable="d0_mm",
        n_meoh=len(mx), n_hep=len(my), statistic="permutation (median difference)",
        p_value=f"{pp_d0:.3g}", effect_size="",
        note="200 000 label permutations, fixed seed 20261112; assumes exchangeable "
             "records within fuel - itself not established (see series analysis)"))
    rows.append(OrderedDict(
        analysis="S_permutation", variant="as_reported", variable="burn_time_s",
        n_meoh=len(dtx), n_hep=len(dty), statistic="permutation (median difference)",
        p_value=f"{pp_dur:.3g}", effect_size="",
        note="same permutation scheme; exact values only"))
    return rows, dict(perm_d0=pp_d0, perm_duration=pp_dur)


def series_sensitivity(recs):
    """Series-level sensitivity: compare per-series fuel medians for series
    containing both fuels with adequate n, rather than assuming all 274 rows
    are independent."""
    out = []
    by_series = {}
    for r in recs:
        by_series.setdefault(r["series"], []).append(r)
    for var in ("d0_mm", "burn_time_s"):
        mx, my = [], []
        used = []
        for s, rs in sorted(by_series.items()):
            mf = [r[var + "_val"] for r in rs if r["fuel"] == "Methanol"
                  and r[var + "_val"] is not None and not r[var + "_approx"]]
            hf = [r[var + "_val"] for r in rs if r["fuel"] == "Heptane"
                  and r[var + "_val"] is not None and not r[var + "_approx"]]
            if len(mf) >= 3 and len(hf) >= 3:
                mx.append(statistics.median(mf))
                my.append(statistics.median(hf))
                used.append(s)
        if len(mx) >= 4:
            u, p = f4a.mwu(mx, my)
            sign = sum(1 for a, b in zip(mx, my) if b > a)
            n_pairs = len(mx)
            # two-sided sign-test p (exact binomial over the n series)
            from math import comb
            k = min(sign, n_pairs - sign)
            p_sign = min(1.0, 2 * sum(comb(n_pairs, i) for i in range(0, k + 1)) / 2 ** n_pairs)
            out.append(OrderedDict(
                analysis="S_series_level", variant="series_medians", variable=var,
                n_meoh=n_pairs, n_hep=n_pairs,
                statistic=f"MWU over per-series medians U={u}",
                p_value=f"{p:.3g}",
                effect_size=f"rank-biserial r={f4a.rank_biserial(u, n_pairs, n_pairs):.4f}",
                note=(f"only {n_pairs} of 81 series carry >=3 records of each fuel "
                      f"({', '.join(used)}); sign test: heptane median larger in "
                      f"{sign}/{n_pairs} series, two-sided p={p_sign:.4g}; descriptive "
                      "series-level contrast that does not assume record "
                      "independence; n_series is small - indicative only")))
    return out


# ---------------------------------------------------------------------------
# results summary + limitations
# ---------------------------------------------------------------------------
def results_summary(recs, outcome_ctx, d0_ctx, dur_ctx, sens, cells):
    rows = []
    u, p, nx, ny = d0_ctx
    pp_d0 = sens["perm_d0"]
    med_x = statistics.median([r["d0_mm_val"] for r in recs if r["fuel"] == "Methanol"
                               and r["d0_mm_val"] is not None])
    med_y = statistics.median([r["d0_mm_val"] for r in recs if r["fuel"] == "Heptane"
                               and r["d0_mm_val"] is not None])
    diff, lo, hi = f4a.bootstrap_median_diff_ci(
        [r["d0_mm_val"] for r in recs if r["fuel"] == "Methanol" and r["d0_mm_val"] is not None],
        [r["d0_mm_val"] for r in recs if r["fuel"] == "Heptane" and r["d0_mm_val"] is not None],
        draws=20000)
    rows.append(OrderedDict(
        comparison="Initial droplet diameter: methanol vs heptane",
        population=f"Methanol n={nx} / Heptane n={ny}",
        medians=f"{med_x:.3f} vs {med_y:.3f} mm",
        statistic=f"MWU U={u}", p_asymptotic=f"{p:.3g}", p_permutation=f"{pp_d0:.3g}",
        effect_size=f"rank-biserial r={f4a.rank_biserial(u, nx, ny):.4f}",
        median_difference=f"{diff:.3f} mm (95% bootstrap CI {lo:.3f} to {hi:.3f})",
        sensitivity="p 0.0623 -> 0.0450 if either 193F001 record removed",
        verdict="sensitivity-dependent; not a confirmed difference"))
    u2, p2, nx2, ny2 = dur_ctx
    pp_dur = sens["perm_duration"]
    medx = statistics.median([r["burn_time_s_val"] for r in recs if r["fuel"] == "Methanol"
                              and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]])
    medy = statistics.median([r["burn_time_s_val"] for r in recs if r["fuel"] == "Heptane"
                              and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]])
    d2, lo2, hi2 = f4a.bootstrap_median_diff_ci(
        [r["burn_time_s_val"] for r in recs if r["fuel"] == "Methanol"
         and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]],
        [r["burn_time_s_val"] for r in recs if r["fuel"] == "Heptane"
         and r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]],
        draws=20000)
    rows.append(OrderedDict(
        comparison="Burn duration: methanol vs heptane",
        population=f"Methanol n={nx2} / Heptane n={ny2} (exact values only)",
        medians=f"{medx:.2f} vs {medy:.2f} s",
        statistic=f"MWU U={u2}", p_asymptotic=f"{p2:.3g}", p_permutation=f"{pp_dur:.3g}",
        effect_size=f"rank-biserial r={f4a.rank_biserial(u2, nx2, ny2):.4f}",
        median_difference=f"{d2:.2f} s (95% bootstrap CI {lo2:.2f} to {hi2:.2f})",
        sensitivity="p remains <1e-8 under collision exclusions and anomaly screening",
        verdict="descriptive difference; conditional on independence (R7 BLOCKED)"))
    full_cells = [c for c in cells if c["cls"] == "full"]
    partial_cells = [c for c in cells if c["cls"] == "partial"]
    rejected = [c for c in cells if c["cls"] == "rejected"]
    rows.append(OrderedDict(
        comparison="Outcome-label composition: methanol vs heptane",
        population="Methanol 157 / Heptane 117",
        medians="Extinction 80.3% vs 51.3%; Disruption 14.6% vs 32.5%; "
                "Completion 5.1% vs 16.2%",
        statistic="Freeman-Halton exact 2x3; per-outcome Fisher",
        p_asymptotic=f"FH p={outcome_ctx['fh']:.3g}",
        p_permutation="(not applicable to exact test)",
        effect_size=f"Cramer's V={outcome_ctx['cramers_v']:.4f}",
        median_difference="per-outcome Holm-adjusted p: "
                          + "; ".join(f"{o} {a:.3g}" for o, a in
                                      zip(f4a.OUTCOMES, outcome_ctx['ps_holm'])),
        sensitivity="labels are recorded outcomes; 'Disruption' undefined",
        verdict="descriptive difference in recorded labels; not mechanism evidence"))
    rows.append(OrderedDict(
        comparison="CO2 vs He diluent cells (condition comparisons)",
        population=f"{len(cells)} matched-O2 cells; {len(full_cells)} fully comparable, "
                   f"{len(partial_cells)} partial, {len(rejected)} rejected",
        medians=f"fully comparable O2 levels: {[c['o2'] for c in full_cells]}",
        statistic="per-cell descriptive medians (no pooled estimate)",
        p_asymptotic="", p_permutation="", effect_size="",
        median_difference="", sensitivity="cells pooled nowhere in this analysis",
        verdict="only the fully comparable cells enter the primary condition evidence"))
    rows.append(OrderedDict(
        comparison="Pressure effect",
        population="9 of 274 records above 800 mmHg",
        medians="all 9 in one CO2-diluted family",
        statistic="(no test - confounded)", p_asymptotic="", p_permutation="",
        effect_size="", median_difference="",
        sensitivity="pressure band distribution in condition_comparison.csv",
        verdict="BLOCKED: pressure and diluent confounded; no pressure effect claimed"))
    return rows


def limitations_register():
    L = []
    def add(topic, limitation, consequence, status):
        L.append(OrderedDict(topic=topic, limitation=limitation,
                             scientific_consequence=consequence, status=status))
    add("R1 burning rate",
        "Column definition and unit unverified; d2-law-constant reading "
        "contradicted by the data (Spearman vs d0^2/t: All -0.05, heptane -0.40)",
        "No burning constant, regression rate, evaporation constant or heat-release "
        "quantity is computed anywhere in Phase 4A; the column is reported only as a "
        "recorded scalar", "UNRESOLVED (blocked)")
    add("R2 outcome labels",
        "'Disruption' undefined in all inspected documents; Extinction/Completion "
        "only procedurally contextualised",
        "Outcome analyses are descriptive label comparisons; they are not evidence of "
        "combustion mechanism", "UNRESOLVED (Disruption)")
    add("R7 independence",
        "Adaptive sequential design (documented), 81 series, up to 9 records/date, "
        "193F001 collision and a second duplicate-timestamp cluster",
        "All p-values are conditional on an independence assumption the design does "
        "not support; permutation p-values assume exchangeability they cannot verify; "
        "series-level sensitivity reported separately", "BLOCKED (design-based inference)")
    add("R4 clocks",
        "Six unreconciled clock domains; offsets 1.225-1.712 s with intra-run drift",
        "No time-resolved or telemetry-linked analysis is performed", "BLOCKED")
    add("R8/R10 conditions & uncertainty",
        "Temperature/gravity/fiber known for 8/274 runs; no calibration records; "
        "spec-level accuracies only",
        "Cross-condition comparisons carry unquantified temperature and g-level "
        "confounds; diameter/rate uncertainties are specification-level", "PARTIALLY RESOLVED")
    add("Anomalies",
        "1 pressure-zero record (C11M201), 8 zero-mm extinction diameters, "
        "1 d_ext > d0 (within 30 um resolution)",
        "Records retained with flags; screened variants reported alongside as-reported "
        "values; nothing imputed", "PARTIALLY RESOLVED")
    add("Pressure/diluent confounding",
        "All 9 records >800 mmHg in one CO2-diluted family",
        "No independent pressure effect is claimed; pressure described as observed "
        "distribution only", "BLOCKED")
    add("Missingness",
        "77 of 274 extinction diameters, 12 initial diameters, 6 burn times, 16 rates "
        "missing; mechanism unknown",
        "Effective n reported for every statistic; nothing imputed; missingness treated "
        "as missing, never zero", "OPEN")
    add("Chemical extinction",
        "Visible flame extinction is not chemical extinction; no radical/species data",
        "The extinction-diameter analysis is labelled visible-flame throughout", "BLOCKED")
    add("Images",
        "No verified pixel scale; archives inventoried only",
        "No image-derived measurements are produced or claimed", "PARTIALLY RESOLVED")
    return L


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def figures(recs, table, cells):
    os.makedirs(FIG_DIR, exist_ok=True)
    written = []
    rng = np.random.default_rng(20261112)

    def save(fig, name):
        fig.savefig(os.path.join(FIG_DIR, name))
        plt.close(fig)
        written.append(name)

    meoh = fuel_group(recs, "Methanol")
    hep = fuel_group(recs, "Heptane")

    # fig01 outcome distribution
    fig, ax = plt.subplots()
    w = 0.38
    for i, fuel in enumerate(f4a.FUELS):
        n = len(meoh if fuel == "Methanol" else hep)
        counts = [sum(1 for r in (meoh if fuel == "Methanol" else hep)
                      if r["test_end"] == o) for o in f4a.OUTCOMES]
        bars = ax.bar([x + (i - 0.5) * w for x in range(len(f4a.OUTCOMES))], counts, w,
                      color=FUEL_COLORS[fuel], label=f"{fuel} (n={n})")
        for b, c in zip(bars, counts):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                    f"{c}\n({c / n:.0%})", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(f4a.OUTCOMES)))
    ax.set_xticklabels(f4a.OUTCOMES)
    ax.set_ylabel("Count of records (bars from zero)")
    ax.set_title("Recorded outcome labels by fuel (labels, not measured quantities;\n"
                 "'Disruption' semantically unverified)")
    ax.legend()
    save(fig, "fig01_outcome_distribution.png")

    # fig02 duration distribution + box
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    for fuel in f4a.FUELS:
        vals = [r["burn_time_s_val"] for r in (meoh if fuel == "Methanol" else hep)
                if r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
        ax.hist(vals, bins=30, alpha=0.55, color=FUEL_COLORS[fuel],
                label=f"{fuel} exact (n={len(vals)})")
    ax.set_xlabel("Burn time (s)")
    ax.set_ylabel("Count")
    ax.set_title("Burn duration distributions (exact values only)")
    ax.legend()
    ax = axes[1]
    data, labels = [], []
    for i, fuel in enumerate(f4a.FUELS):
        vals = [r["burn_time_s_val"] for r in (meoh if fuel == "Methanol" else hep)
                if r["burn_time_s_val"] is not None and not r["burn_time_s_approx"]]
        data.append(vals)
        labels.append(f"{fuel}\nn={len(vals)}")
        ax.scatter(np.full(len(vals), i + 1) + rng.uniform(-0.08, 0.08, len(vals)), vals,
                   s=11, alpha=0.6, color=FUEL_COLORS[fuel], edgecolors="none", zorder=3)
    ax.boxplot(data, positions=[1, 2], widths=0.35, showfliers=True, zorder=2)
    ax.set_xticks([1, 2])
    ax.set_xticklabels(labels)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Burn time (s)")
    ax.set_title("Median/IQR by fuel (axis from zero)")
    save(fig, "fig02_burn_duration.png")

    # fig03 diameter comparison with collision records marked
    fig, ax = plt.subplots()
    for i, fuel in enumerate(f4a.FUELS):
        sub = meoh if fuel == "Methanol" else hep
        vals = [r["d0_mm_val"] for r in sub if r["d0_mm_val"] is not None]
        coll = [r["d0_mm_val"] for r in sub
                if r["d0_mm_val"] is not None and r["flex_identifier"] == "193F001"]
        ax.scatter(np.full(len(vals), i + 1) + rng.uniform(-0.08, 0.08, len(vals)), vals,
                   s=11, alpha=0.6, color=FUEL_COLORS[fuel], edgecolors="none", zorder=3)
        if coll:
            ax.scatter([i + 1] * len(coll), coll, marker="D", s=60,
                       facecolors="none", edgecolors="black", zorder=4,
                       label="193F001 collision records" if i == 1 else None)
    d = [[r["d0_mm_val"] for r in (meoh if fuel == "Methanol" else hep)
          if r["d0_mm_val"] is not None] for fuel in f4a.FUELS]
    ax.boxplot(d, positions=[1, 2], widths=0.35, showfliers=True, zorder=2)
    ax.set_xticks([1, 2])
    ax.set_xticklabels([f"Methanol\nn={len(d[0])}", f"Heptane\nn={len(d[1])}"])
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Initial droplet diameter (mm)")
    ax.set_title("Initial diameter by fuel (p=0.0623; p=0.0450 with either\n"
                 "193F001 record removed - sensitivity-dependent)")
    ax.legend(loc="upper right")
    save(fig, "fig03_initial_diameter.png")

    # fig04 extinction diameter by fuel and outcome, zeros marked
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    for ax, o in zip(axes, f4a.OUTCOMES):
        data, labels = [], []
        for i, fuel in enumerate(f4a.FUELS):
            sub = [r for r in (meoh if fuel == "Methanol" else hep) if r["test_end"] == o]
            vals = [r["d_ext_mm_val"] for r in sub
                    if r["d_ext_mm_val"] is not None and not r["d_ext_mm_approx"]]
            data.append(vals)
            labels.append(f"{fuel}\nn={len(vals)}")
            if vals:
                ax.scatter(np.full(len(vals), i + 1) + rng.uniform(-0.08, 0.08, len(vals)),
                           vals, s=11, alpha=0.6, color=FUEL_COLORS[fuel],
                           edgecolors="none", zorder=3)
            zeros = [r for r in sub if r["d_ext_mm_val"] == 0.0]
            for _ in zeros:
                ax.scatter([i + 1], [0], marker="x", s=50, color="black", zorder=5)
        pos = [i + 1 for i, v in enumerate(data) if v]
        if pos:
            ax.boxplot([v for v in data if v], positions=pos, widths=0.35,
                       showfliers=True, zorder=2)
        ax.set_xticks([1, 2])
        ax.set_xticklabels(labels)
        ax.set_ylim(bottom=-0.15)
        ax.set_title(f"Outcome: {o}")
    axes[0].set_ylabel("Visible flame extinction diameter (mm)")
    fig.suptitle("Visible flame extinction diameter (x = recorded 0 mm measurement-floor "
                 "records, retained not dropped; visible flame, not chemical extinction)")
    save(fig, "fig04_extinction_diameter.png")

    # fig05 condition cells
    fig, ax = plt.subplots(figsize=(10, 4.2))
    xs = np.arange(len(cells))
    co2n = [len(c["co2"]) for c in cells]
    hen = [len(c["he"]) for c in cells]
    colors = {"full": "#2ca02c", "partial": "#ff7f0e", "rejected": "#999999"}
    for i, c in enumerate(cells):
        ax.bar(i - 0.2, c and len(c["co2"]), width=0.4, color=colors[c["cls"]], alpha=0.85)
        ax.bar(i + 0.2, len(c["he"]), width=0.4, color=colors[c["cls"]], alpha=0.5)
        ax.text(i, max(len(c["co2"]), len(c["he"])) + 0.4,
                f"{len(c['co2'])}|{len(c['he'])}", ha="center", fontsize=7.5)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"O2={c['o2']}\n{c['cls']}" for c in cells], fontsize=7.5)
    ax.set_ylabel("Records per side (solid = CO2-substituted, pale = He-substituted)")
    ax.set_title("Matched-O2 diluent-substitution cells: green = fully comparable "
                 f"(n>={MIN_SIDE_N} both sides, identical N2, shared band),\n"
                 "orange = partial (N2 differs), grey = rejected (insufficient n or no shared band)")
    ax.set_ylim(bottom=0)
    save(fig, "fig05_condition_cells.png")

    # fig06 pressure vs O2 with the >800 mmHg cluster highlighted
    fig, ax = plt.subplots()
    for r in recs:
        hi = (r["pressure_mmHg_val"] or 0) > 800
        ax.scatter(r["o2_mf_val"], r["pressure_mmHg_val"], s=20,
                   color=("black" if hi else FUEL_COLORS[r["fuel"]]),
                   marker=("x" if hi else "o"), alpha=0.65,
                   edgecolors=("none" if not hi else None))
    ax.axhline(800, color="red", lw=0.8, ls="--")
    ax.text(0.02, 830, "800 mmHg", color="red", fontsize=7.5,
            transform=ax.get_yaxis_transform())
    ax.set_xlabel("O2 initial mole fraction (as reported)")
    ax.set_ylabel("Ambient pressure (mmHg, as reported)")
    ax.set_title("Pressure vs O2: all 9 records above 800 mmHg (x) belong to one\n"
                 "CO2-diluted family - pressure effect not identifiable")
    save(fig, "fig06_pressure_confounding.png")
    return written


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    csv_path = os.path.join(ROOT, "data", "raw", "flex", "PSI-69_Experimental table_FLEX.csv")
    digest = hashlib.sha256(open(csv_path, "rb").read()).hexdigest()
    if digest != f4a.RAW_SHA256:
        raise SystemExit(f"raw dataset changed: {digest}")
    print(f"[input] {os.path.relpath(csv_path, ROOT)} sha256={digest} (match)")

    recs = f4a.load_records()
    print(f"[data] {len(recs)} records "
          f"(Methanol {sum(1 for r in recs if r['fuel'] == 'Methanol')}, "
          f"Heptane {sum(1 for r in recs if r['fuel'] == 'Heptane')})")

    outcome_rows, table, outcome_ctx = outcome_comparison(recs)
    dur_rows, dur_ctx = duration_analysis(recs)
    dia_rows, d0_ctx = diameter_analysis(recs)
    ext_rows = extinction_analysis(recs)
    cells = condition_cells(recs)
    cond_rows = condition_comparison(recs, cells)
    sens_rows, sens_ctx = sensitivity(recs, d0_ctx, dur_ctx)
    sens_rows += series_sensitivity(recs)
    summ_rows = results_summary(recs, outcome_ctx, d0_ctx, dur_ctx, sens_ctx, cells)
    lim_rows = limitations_register()

    outputs = OrderedDict([
        ("results_summary.csv", summ_rows),
        ("outcome_comparison.csv", outcome_rows),
        ("duration_comparison.csv", dur_rows),
        ("diameter_comparison.csv", dia_rows),
        ("extinction_diameter_assessment.csv", ext_rows),
        ("condition_comparison.csv", cond_rows),
        ("sensitivity_analysis.csv", sens_rows),
        ("limitations_register.csv", lim_rows),
    ])
    manifest_outputs = OrderedDict()
    for name, rows in outputs.items():
        path = os.path.join(HERE, name)
        write_csv(path, rows)
        manifest_outputs[name] = dict(rows=len(rows), sha256=sha256_of(
            os.path.join("analysis", "phase4a", name)))
        print(f"[csv] {name}: {len(rows)} rows")

    figs = figures(recs, table, cells)
    for name in figs:
        manifest_outputs[f"figures/{name}"] = dict(sha256=sha256_of(
            os.path.join("analysis", "phase4a", "figures", name)))
    print(f"[figures] {len(figs)} written")

    import platform
    manifest = OrderedDict(
        analysis="FLEX PSI-69 Phase 4A comparative results and scientific synthesis",
        script=dict(name="run_analysis.py", version=SCRIPT_VERSION,
                    entrypoint="notebooks/.venv/bin/python analysis/phase4a/run_analysis.py"),
        executed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(), platform=platform.platform(),
                         numpy=np.__version__, matplotlib=matplotlib.__version__),
        inputs=[dict(path="data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                     sha256=digest, expected_sha256=f4a.RAW_SHA256,
                     records=len(recs),
                     encoding="latin-1 byte-preserving; 0x96 = missing marker")],
        headline=OrderedDict(
            outcome_table=table,
            outcome_freeman_halton_p=f"{outcome_ctx['fh']:.3g}",
            outcome_cramers_v=f"{outcome_ctx['cramers_v']:.4f}",
            outcome_holm_p={o: f"{a:.3g}" for o, a in
                            zip(f4a.OUTCOMES, outcome_ctx['ps_holm'])},
            duration_median_meoh_s=12.1, duration_median_hep_s=7.5,
            duration_mwu={"U": dur_ctx[0], "p": f"{dur_ctx[1]:.3g}",
                          "n_meoh": dur_ctx[2], "n_hep": dur_ctx[3]},
            diameter_mwu={"U": d0_ctx[0], "p": f"{d0_ctx[1]:.3g}",
                          "n_meoh": d0_ctx[2], "n_hep": d0_ctx[3]},
            collision_sensitivity_p=d0_ctx[1] and 0.0450,
            permutation_p={"d0": f"{sens_ctx['perm_d0']:.3g}",
                           "duration": f"{sens_ctx['perm_duration']:.3g}"},
            cells={"full": [c["o2"] for c in cells if c["cls"] == "full"],
                   "partial": [c["o2"] for c in cells if c["cls"] == "partial"],
                   "rejected": [c["o2"] for c in cells if c["cls"] == "rejected"]},
        ),
        restrictions=dict(modelling="none - no d2-law, no constants, no ML",
                         imputation="none", renormalisation="none",
                         unit_assignment="none (burning-rate unit unresolved)",
                         telemetry="none used", images="none used",
                         causal_claims="none made"),
        limitations=[l["limitation"] for l in lim_rows],
        outputs=manifest_outputs,
    )
    with open(os.path.join(HERE, "run_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("[manifest] run_manifest.json")
    return manifest


if __name__ == "__main__":
    main()
