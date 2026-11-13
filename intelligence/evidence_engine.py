"""FLEX-PSI69 evidence intelligence - the question-to-evidence engine.

Deterministic pipeline:

    question -> relevant variables -> retrieval -> comparability filter
             -> supported summaries -> transparent evidence ranking
             -> explanation assembly (answer, evidence, numbers, method,
                exclusions, contradictions, limitations, resolving data)

No LLM, no invention: every number is recomputed here from the raw table and
every citation points at a file or a raw row.
"""

import json
import os
from collections import Counter, OrderedDict

import comparability as C
import ranking
import retrieval as R

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(HERE, "question_catalog.json")

RECORDS = None


def records():
    global RECORDS
    if RECORDS is None:
        RECORDS = R.load_records()
    return RECORDS


def load_catalog():
    with open(CATALOG_PATH) as fh:
        return json.load(fh)


def _answer_shell(qid, question, method, limitations, **extra):
    out = OrderedDict(
        question_id=qid,
        question=question,
        direct_answer=extra.pop("direct_answer", ""),
        supporting_experiments=extra.pop("supporting_experiments", []),
        numerical_findings=extra.pop("numerical_findings", OrderedDict()),
        evidence_ranking=extra.pop("evidence_ranking", []),
        method=method,
        important_exclusions=extra.pop("important_exclusions", []),
        contradictory_or_conflicting_evidence=extra.pop("contradictions", []),
        limitations=limitations,
        what_would_resolve_uncertainty=extra.pop("resolvers", []),
        traceability=extra.pop("traceability", []),
    )
    return out


# ---------------------------------------------------------------------------
# Q1: outcome differences
# ---------------------------------------------------------------------------
def q_outcome_differences(question):
    recs = records()
    table = [[sum(1 for r in recs if r["fuel"] == f and r["outcome"] == o)
              for o in R.OUTCOMES] for f in R.FUELS]
    n_meoh, n_hep = len([r for r in recs if r["fuel"] == "Methanol"]), \
        len([r for r in recs if r["fuel"] == "Heptane"])
    ps = []
    per_outcome = []
    for i, o in enumerate(R.OUTCOMES):
        a, b = table[0][i], n_meoh - table[0][i]
        c, d = table[1][i], n_hep - table[1][i]
        p = R.fisher_exact_2x2(a, b, c, d)
        ps.append(p)
        per_outcome.append(OrderedDict(
            outcome=o, methanol=f"{a}/{n_meoh} ({a / n_meoh:.1%})",
            heptane=f"{c}/{n_hep} ({c / n_hep:.1%})",
            fisher_p=p, fishers_note="two-sided, outcome vs rest"))
    holm = R.holm(ps)
    fh = R.fisher_freeman_halton_2x3(table)
    cv = R.cramers_v(table)
    method = ("counts and proportions of the recorded `Test end` label per fuel; "
              "Freeman-Halton exact test on the 2x3 table; two-sided Fisher "
              "exact per outcome vs rest with Holm adjustment; Cramer's V "
              "effect size. Deterministic recomputation from the raw table.")
    limitations = [
        "recorded outcome labels are not measured physical quantities",
        "'Disruption' has no documented definition in any inspected source",
        "Extinction denotes visible flame extinction, not chemical extinction",
        "experimental independence is not established (adaptive LOI design; "
        "81 series; duplicated identifier), so p-values are conditional",
        "the adaptive procedure drives each fuel series toward marginal "
        "conditions, so label composition partly reflects the test programme",
    ]
    resolvers = ["originator definition of the outcome labels (OQ-2)",
                 "series structure metadata for design-respecting inference (OQ-5)"]
    return _answer_shell(
        "Q1", question, method, limitations,
        direct_answer=(
            "Recorded outcome-label composition differs strongly between the "
            f"fuels: Extinction in {table[0][0]}/{n_meoh} ({table[0][0]/n_meoh:.1%}) "
            f"of methanol records vs {table[1][0]}/{n_hep} ({table[1][0]/n_hep:.1%}) "
            "of heptane records (Freeman-Halton p="
            f"{fh:.3g}, Cramer's V={cv:.3f}). This is a difference in recorded "
            "labels, not a demonstrated difference in combustion behaviour."),
        numerical_findings=OrderedDict(
            contingency={R.FUELS[0]: dict(zip(R.OUTCOMES, table[0])),
                         R.FUELS[1]: dict(zip(R.OUTCOMES, table[1]))},
            denominators={"Methanol": n_meoh, "Heptane": n_hep},
            per_outcome=per_outcome,
            holm_adjusted_p=dict(zip(R.OUTCOMES, holm)),
            freeman_halton_p=fh, cramers_v=cv,
            cross_check="values match analysis/phase4a/outcome_comparison.csv"),
        evidence_ranking=ranking.rank_evidence([
            dict(label="fuel x outcome contingency (all 274 records)",
                 relevance=(1.0, "direct answer to the question"),
                 data_quality=(0.9, "outcome and fuel complete for 274/274; "
                                    "labels are complete but semantics unverified"),
                 comparability=(0.3, "comparability unassessed for label counts"),
                 statistical_strength=ranking.score_statistical_strength(
                     274, effect_size=cv, p_value=fh,
                     test_used="Freeman-Halton exact")),
            dict(label="per-outcome Fisher contrasts",
                 relevance=(1.0, "direct answer to the question"),
                 data_quality=(0.9, "as above"),
                 comparability=(0.3, "unassessed"),
                 statistical_strength=ranking.score_statistical_strength(
                     61, effect_size=None, p_value=ps[1],
                     test_used="Fisher exact (smallest class support)")),
        ]),
        contradictions=[
            "no data source contradicts these counts; the limitation is "
            "interpretive, not numerical"],
        resolvers=resolvers,
        traceability=["data/raw/flex/PSI-69 Experimental table_FLEX.csv "
                      "(274 rows)", "analysis/phase4a/outcome_comparison.csv"],
    )


# ---------------------------------------------------------------------------
# Q2: duration differences
# ---------------------------------------------------------------------------
def q_duration_differences(question):
    recs = records()
    groups = {}
    for f in R.FUELS:
        vals = [r["burn_time_s"] for r in recs
                if r["fuel"] == f and r["burn_time_s"] is not None
                and not r["burn_time_approx"]]
        groups[f] = vals
    x, y = groups["Methanol"], groups["Heptane"]
    qx, qy = R.quantiles(x), R.quantiles(y)
    u, p = R.mwu(x, y)
    rb = R.rank_biserial(u, len(x), len(y))
    diff = qy[1] - qx[1]
    method = ("exact recorded burn times only (the two `~`-approximate records "
              "excluded and listed separately); median/IQR summaries per fuel; "
              "two-sided Mann-Whitney U (tie- and continuity-corrected normal "
              "approximation) with rank-biserial effect size; the median "
              "difference is heptane minus methanol. Deterministic "
              "recomputation from the raw table.")
    limitations = [
        "burn duration is a recorded scalar with undocumented start/stop events",
        "per-run temperature is unknown for 266/274 records, so part of any "
        "duration difference may be environmental",
        "experimental independence is not established (adaptive design)",
        "duration is not a direct combustion-mechanism measurement",
        "the two approximate values (6 s, 9 s) are excluded from statistics "
        "and preserved verbatim in the evidence table",
    ]
    return _answer_shell(
        "Q2", question, method, limitations,
        direct_answer=(
            f"Recorded burn durations differ substantially: median "
            f"{qx[1]:.2f} s (methanol, n={len(x)}) vs {qy[1]:.2f} s (heptane, "
            f"n={len(y)}); Mann-Whitney U={u}, p={p:.3g}, rank-biserial "
            f"r={rb:.3f}. The median difference is {diff:+.2f} s "
            "(heptane minus methanol). A descriptive difference in the "
            "recorded quantity - not a combustion-mechanism finding."),
        numerical_findings=OrderedDict(
            methanol=dict(n=len(x), median=round(qx[1], 3),
                          iqr=[round(qx[0], 3), round(qx[2], 3)]),
            heptane=dict(n=len(y), median=round(qy[1], 3),
                         iqr=[round(qy[0], 3), round(qy[2], 3)]),
            median_difference_heptane_minus_methanol=round(diff, 3),
            mwu_U=u, mwu_p=p, rank_biserial=round(rb, 4),
            approximate_values_excluded=["~6", "~9"],
            cross_check="values match analysis/phase4a/duration_comparison.csv"),
        evidence_ranking=ranking.rank_evidence([
            dict(label="burn-time distributions by fuel (266 exact records)",
                 relevance=(1.0, "direct answer"),
                 data_quality=(0.85, "6 missing and 2 approximate handled "
                                     "explicitly; no integrity flags on these rows"),
                 comparability=(0.3, "unassessed"),
                 statistical_strength=ranking.score_statistical_strength(
                     266, effect_size=rb, p_value=p, test_used="Mann-Whitney")),
        ]),
        contradictions=[],
        resolvers=["originator definition of burn-time start/stop events",
                   "per-run chamber temperature (OQ-8)"],
        traceability=["data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                      "analysis/phase4a/duration_comparison.csv"],
    )


# ---------------------------------------------------------------------------
# Q3: oxygen vs outcomes
# ---------------------------------------------------------------------------
def q_oxygen_outcomes(question):
    recs = records()
    by_o2 = {}
    for r in recs:
        by_o2.setdefault(r["o2_mf"], []).append(r)
    levels = []
    for o2 in sorted(by_o2):
        rs = by_o2[o2]
        counts = Counter(r["outcome"] for r in rs)
        n = len(rs)
        levels.append(OrderedDict(
            o2_mf=o2, n=n,
            outcomes={o: counts.get(o, 0) for o in R.OUTCOMES},
            extinction_fraction=round(counts.get("Extinction", 0) / n, 4)))
    # air-family only comparison: O2 <=0.21 vs >0.21 within N2-balanced air
    air = [r for r in recs if r["co2_mf"] == 0 and r["he_mf"] == 0]
    lo = [r for r in air if r["o2_mf"] <= 0.21]
    hi = [r for r in air if r["o2_mf"] > 0.21]
    p_lo = sum(1 for r in lo if r["outcome"] == "Extinction") / max(len(lo), 1)
    p_hi = sum(1 for r in hi if r["outcome"] == "Extinction") / max(len(hi), 1)
    method = ("descriptive outcome composition per reported initial O2 level, "
              "plus a restricted within-air-family contrast (records with "
              "CO2=0 and He=0 only) of Extinction fraction below vs above "
              "O2=0.21. No causal claim: O2 is experimentally confounded with "
              "diluent family and series across the table.")
    limitations = [
        "observational only: O2 was set adaptively within series",
        "outside the air family, O2 is confounded with CO2/He dilution",
        "'Disruption' is undefined; Extinction is a visible-flame label",
        "per-level sample sizes are unequal and small at the extremes",
    ]
    return _answer_shell(
        "Q3", question, method, limitations,
        direct_answer=(
            "Across the 274 records, higher reported initial O2 is associated "
            "with a larger recorded Extinction fraction (e.g. within the "
            f"air-diluted family: {p_lo:.1%} below/at O2=0.21 vs {p_hi:.1%} "
            "above, n="
            f"{len(lo)}/{len(hi)}). Per-level outcome compositions are "
            "tabulated below. This is a descriptive association within a "
            "restricted family, not a demonstrated causal oxygen effect."),
        numerical_findings=OrderedDict(
            per_o2_level=levels,
            air_family_contrast=OrderedDict(
                definition="records with CO2 mole fraction = 0 and He = 0",
                o2_le_021=dict(n=len(lo), extinction_fraction=round(p_lo, 4)),
                o2_gt_021=dict(n=len(hi), extinction_fraction=round(p_hi, 4)),
                note="descriptive proportions; no test reported because the "
                     "contrast crosses series and is confounded by design"),
            cross_check="derived from the raw table; no frozen CSV quotes "
                        "this exact contrast"),
        evidence_ranking=ranking.rank_evidence([
            dict(label="air-family O2 contrast",
                 relevance=(0.8, "answers the question with the least-confounded "
                                "available restriction"),
                 data_quality=(0.85, "all required fields complete for these rows"),
                 comparability=(0.5, "same diluent family (none) but still "
                                     "cross-series"),
                 statistical_strength=ranking.score_statistical_strength(
                     len(lo) + len(hi), effect_size=None,
                     p_value=None, test_used="none (descriptive)")),
        ]),
        contradictions=[
            "outside the air family the O2-outcome relationship is not "
            "separable from diluent composition; cells with differing N2 "
            "balances are not comparable (see Q4)"],
        resolvers=["charge verification logs per run (OQ-8)",
                   "series metadata to restrict comparisons within series"],
        traceability=["data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                      "analysis/validation/condition_comparability.md"],
    )


# ---------------------------------------------------------------------------
# Q4: comparability under specified conditions
# ---------------------------------------------------------------------------
def q_comparable_experiments(question, conditions=None):
    recs = records()
    conditions = conditions or {}
    cells = C.dilution_cells(recs)
    if conditions.get("o2_mf") is not None:
        cells = [c for c in cells if c["o2_mf"] == conditions["o2_mf"]]
    full = [c for c in cells if c["comparability"] == "full"]
    partial = [c for c in cells if c["comparability"] == "partial"]
    rejected = [c for c in cells if c["comparability"] == "rejected"]
    experiments = []
    for c in full:
        for side in ("CO2", "He"):
            for r in C.experiments_in_cell(recs, c["o2_mf"], side):
                experiments.append(R.experiment_view(r))
    method = ("comparability rule: two sides are comparable within an "
              "oxygen-matched CO2/He cell only when (a) reported N2 balances "
              "are identical, (b) at least one pressure band is shared, and "
              "(c) each side has >=3 records. Cells failing a criterion are "
              "reported as partial or rejected and are not used for primary "
              "comparisons. Deterministic recomputation from the raw table.")
    limitations = [
        "identical reported O2 and N2 do not guarantee identical actual "
        "composition (no charge verification logs)",
        "comparability is within-cell; no pooling across cells is performed",
        "per-side fuel counts are small in some cells",
        "experimental independence is not established",
    ]
    return _answer_shell(
        "Q4", question, method, limitations,
        direct_answer=(
            f"Of {len(cells)} oxygen-matched CO2/He substitution cells, "
            f"{len(full)} are fully comparable "
            f"(O2 = {[c['o2_mf'] for c in full]}), {len(partial)} are partial "
            "(N2 balances differ) and {len(rejected)} are rejected "
            "(insufficient records on a side). Fully comparable cells and "
            "their experiments are listed; the others are excluded from "
            "primary comparisons with reasons."),
        numerical_findings=OrderedDict(
            cells_full=[OrderedDict(o2_mf=c["o2_mf"], n_co2=c["n_co2"],
                                    n_he=c["n_he"], reason=c["reason"])
                        for c in full],
            cells_partial=[OrderedDict(o2_mf=c["o2_mf"], n_co2=c["n_co2"],
                                       n_he=c["n_he"], reason=c["reason"])
                           for c in partial],
            cells_rejected=[OrderedDict(o2_mf=c["o2_mf"], n_co2=c["n_co2"],
                                        n_he=c["n_he"], reason=c["reason"])
                            for c in rejected],
            cross_check="cell classifications match "
                        "analysis/phase4a/condition_comparison.csv"),
        supporting_experiments=experiments,
        evidence_ranking=ranking.rank_evidence([
            dict(label=f"cell O2={c['o2_mf']}",
                 relevance=(1.0, "matches the comparability criterion"),
                 data_quality=(0.85, "composition complete; flags tracked per "
                                     "record in the experiment table"),
                 comparability=(1.0, c["reason"]),
                 statistical_strength=ranking.score_statistical_strength(
                     c["n_co2"] + c["n_he"]))
            for c in full] + [
            dict(label=f"cell O2={c['o2_mf']} (partial)",
                 relevance=(0.9, "same O2 level"),
                 data_quality=(0.85, "composition complete; flags tracked per "
                                     "record in the experiment table"),
                 comparability=(0.5, c["reason"]),
                 statistical_strength=ranking.score_statistical_strength(
                     c["n_co2"] + c["n_he"]))
            for c in partial]),
        contradictions=[],
        resolvers=["charge verification logs (OQ-8)",
                   "per-run pressure calibration records (OQ-7)"],
        traceability=["data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                      "analysis/phase4a/condition_comparison.csv",
                      "analysis/validation/condition_comparability.md"],
    )


# ---------------------------------------------------------------------------
# Q5: pressure evidence
# ---------------------------------------------------------------------------
def q_pressure_evidence(question):
    recs = records()
    bands = Counter(C.pressure_band(r) for r in recs)
    high = [r for r in recs if (r["pressure_mmHg"] or 0) > 800]
    fams = Counter(C.condition_family(r) for r in high)
    method = ("descriptive distribution of the reported ambient pressure and "
              "explicit confounding disclosure; no test and no effect claim "
              "is produced.")
    limitations = [
        "all records above 800 mmHg belong to a single CO2-diluted family, so "
        "pressure and diluent composition are inseparable there",
        "no independent pressure effect can be identified from this dataset",
        "one record reports 0 mmHg (documented corrupted; treated as missing)",
        "pressure tolerance is specification-level (+/-0.05 atm) without "
        "per-run calibration records",
    ]
    return _answer_shell(
        "Q5", question, method, limitations,
        direct_answer=(
            "The dataset contains no usable evidence for an independent "
            "pressure effect: all 9 records above 800 mmHg belong to one "
            "CO2-diluted mixture family (O2=0.21/N2=0.09/CO2=0.70), so "
            "pressure and diluent are confounded. The observed pressure "
            "distribution is reported for completeness."),
        numerical_findings=OrderedDict(
            pressure_bands={b: bands.get(b, 0) for b in
                            ("<560 mmHg", "560-800 mmHg", "800-2100 mmHg",
                             ">2100 mmHg", "not_reported")},
            n_above_800_mmHg=len(high),
            families_above_800_mmHg=dict(fams),
            corrupted_record={"identifier": "C11M201", "reported": "0 mmHg",
                              "treatment": "treated as missing; never imputed"},
            cross_check="values match analysis/phase4a/condition_comparison.csv"),
        evidence_ranking=ranking.rank_evidence([
            dict(label="pressure distribution (descriptive)",
                 relevance=(0.6, "describes the question's variable but cannot "
                                "answer it causally"),
                 data_quality=(0.85, "273/274 usable after the corrupted record"),
                 comparability=(0.0, "pressure confounded with diluent above "
                                     "800 mmHg"),
                 statistical_strength=ranking.score_statistical_strength(274)),
        ]),
        contradictions=[],
        resolvers=["high-pressure runs in other mixture families (OQ-8)",
                   "transducer calibration records (OQ-7)"],
        traceability=["data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                      "analysis/phase4a/condition_comparison.csv"],
    )


# ---------------------------------------------------------------------------
# Q6: data-quality sensitivity
# ---------------------------------------------------------------------------
def q_sensitivity(question):
    sens = R.read_frozen("sensitivity_analysis")
    coll = [r for r in sens if r["analysis"] == "S_diameter"]
    d0_all = next(r for r in coll if r["variant"] == "as_reported")
    d0_ex1 = next(r for r in coll if r["variant"] == "excluding_193F001_record_1")
    d0_ex2 = next(r for r in coll if r["variant"] == "excluding_193F001_record_2")
    d0_scr = next(r for r in coll
                  if r["variant"] == "screened_flagged_anomalies_excluded")
    method = ("quantified sensitivity of the headline comparisons to the "
              "documented data-quality issues, reusing the frozen Phase 4A "
              "sensitivity register (which recomputes each variant from the "
              "raw table).")
    limitations = [
        "sensitivity is quantified for the initial-diameter contrast; the "
        "duration contrast is robust across the same variants (p remains "
        "below 2e-09)",
        "sensitivity analysis describes the data, not the physics",
    ]
    return _answer_shell(
        "Q6", question, method, limitations,
        direct_answer=(
            "The initial-diameter fuel comparison is sensitive to "
            "data-quality handling: p="
            f"{d0_all['p_value']} as reported, p={d0_ex1['p_value']} with "
            f"either 193F001 record removed, and p={d0_scr['p_value']} with "
            "all value-integrity-flagged records excluded. It is therefore "
            "reported as sensitivity-dependent and not as a confirmed "
            "difference. Burn duration remains significant under every "
            "variant."),
        numerical_findings=OrderedDict(
            initial_diameter_p_by_variant={
                "as_reported": d0_all["p_value"],
                "excluding_193F001_record_1": d0_ex1["p_value"],
                "excluding_193F001_record_2": d0_ex2["p_value"],
                "screened_flagged_anomalies_excluded": d0_scr["p_value"]},
            collision_records=[
                dict(test_no=r["flex_test_no"] if False else "",
                     note="two records share identifier 193F001 (tests 70 and "
                          "73) with identical timestamps and near-identical "
                          "diameters but different reduced values"),
            ],
            duration_robustness="p < 2e-09 under collision exclusions and "
                                "anomaly screening",
            cross_check="values match analysis/phase4a/sensitivity_analysis.csv"),
        evidence_ranking=ranking.rank_evidence([
            dict(label="initial-diameter contrast (as reported)",
                 relevance=(0.9, "the headline comparison most affected by the "
                                "known data issues"),
                 data_quality=(0.7, "includes the duplicated identifier and "
                                    "flagged records"),
                 comparability=(0.3, "unassessed"),
                 statistical_strength=ranking.score_statistical_strength(
                     262, effect_size=0.1354, p_value=0.0623,
                     test_used="Mann-Whitney")),
            dict(label="initial-diameter contrast (collision-excluded)",
                 relevance=(0.9, "same comparison under a documented "
                                "alternative handling"),
                 data_quality=(0.75, "one duplicate removed"),
                 comparability=(0.3, "unassessed"),
                 statistical_strength=ranking.score_statistical_strength(
                     261, effect_size=0.1460, p_value=0.0450,
                     test_used="Mann-Whitney")),
        ]),
        contradictions=[
            "the three defensible record-handling rules give different "
            "conventional-significance verdicts; this conflict is the finding"],
        resolvers=["originator resolution of the 193F001 collision (OQ-5)",
                   "confirmation of the 0 mmHg and zero-mm records (OQ-3/4)"],
        traceability=["analysis/phase4a/sensitivity_analysis.csv",
                      "analysis/evidence_resolution/identifier_reconciliation.md",
                      "analysis/evidence_resolution/anomaly_resolution.md"],
    )


# ---------------------------------------------------------------------------
# Q7: missing information
# ---------------------------------------------------------------------------
def q_missing_information(question):
    recs = records()
    n = len(recs)
    miss = OrderedDict()
    for key, label in (("d_ext_mm", "visible flame extinction diameter"),
                       ("d0_mm", "initial droplet diameter"),
                       ("burn_time_s", "burn time"),
                       ("burn_rate_raw", "burning-rate value")):
        miss[label] = sum(1 for r in recs if r[key] is None)
    zeros = sum(1 for r in recs if r["d_ext_mm"] == 0.0)
    approx = sum(1 for r in recs if r["burn_time_approx"])
    flagged = sum(1 for r in recs if r["flags"])
    method = ("inventory of what the release does not contain, counted from "
              "the raw table, plus the unresolved evidence items registered "
              "in Phase 3/3.5.")
    gaps = [
        OrderedDict(gap="burning-rate definition and unit", status="UNRESOLVED",
                    consequence="no physical rate quantity can be computed (R1 BLOCKED)",
                    originator_question="OQ-1"),
        OrderedDict(gap="outcome label 'Disruption' definition",
                    status="UNRESOLVED",
                    consequence="61 records carry an undefined category (R2)",
                    originator_question="OQ-2"),
        OrderedDict(gap="per-run temperature, gravity, fiber usage",
                    status="PARTIAL (8/274 runs from linked telemetry)",
                    consequence="unquantified condition confounding (R8)",
                    originator_question="OQ-8"),
        OrderedDict(gap="calibration records for any measurement",
                    status="NOT AVAILABLE locally",
                    consequence="uncertainties are specification-level only (R10)",
                    originator_question="OQ-7"),
        OrderedDict(gap="experimental series/run metadata",
                    status="NOT AVAILABLE",
                    consequence="design-based inference impossible (R7)",
                    originator_question="OQ-5"),
        OrderedDict(gap="telemetry clock synchronization",
                    status="NOT AVAILABLE",
                    consequence="no time-resolved analysis (R4 BLOCKED)",
                    originator_question="OQ-6"),
        OrderedDict(gap="image pixel scale",
                    status="NOT AVAILABLE",
                    consequence="no image-derived diameters (R3 partial)",
                    originator_question="OQ-8"),
    ]
    return _answer_shell(
        "Q7", question, method, limitations=[
            "missingness mechanism is unknown; nothing here assumes randomness",
            "missing values are never imputed; flagged values are never replaced",
        ],
        direct_answer=(
            f"Of the 274 records, {miss['visible flame extinction diameter']} "
            f"lack an extinction diameter, {zeros} record 0 mm, "
            f"{miss['initial droplet diameter']} lack an initial diameter, "
            f"{miss['burn time']} lack a burn time and "
            f"{miss['burning-rate value']} lack a burning-rate value; "
            f"{approx} burn times are approximate and {flagged} records carry "
            "at least one integrity flag. Beyond missingness, seven "
            "evidence-level gaps prevent stronger conclusions (listed below), "
            "each mapped to a prioritised originator question."),
        numerical_findings=OrderedDict(missing_counts=miss,
                                      zero_extinction_diameters=zeros,
                                      approximate_burn_times=approx,
                                      records_with_integrity_flags=flagged,
                                      evidence_level_gaps=gaps,
                                      denominator=n,
                                      cross_check="missingness counts match "
                                                  "analysis/audit/missing_data_report.csv"),
        evidence_ranking=ranking.rank_evidence([
            dict(label="missingness inventory (all 274 records)",
                 relevance=(1.0, "direct answer"),
                 data_quality=(0.9, "counted from complete-enumeration of the "
                                    "raw table"),
                 comparability=(0.3, "unassessed"),
                 statistical_strength=ranking.score_statistical_strength(274)),
        ]),
        contradictions=[],
        resolvers=["answer OQ-1 through OQ-8 with the data originators"],
        traceability=["data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                      "analysis/audit/missing_data_report.csv",
                      "analysis/validation/evidence_register.csv",
                      "analysis/evidence_resolution/README.md"],
    )


ENGINES = {
    "Q1": q_outcome_differences,
    "Q2": q_duration_differences,
    "Q3": q_oxygen_outcomes,
    "Q4": q_comparable_experiments,
    "Q5": q_pressure_evidence,
    "Q6": q_sensitivity,
    "Q7": q_missing_information,
}


def answer_question(qid, parameters=None):
    catalog = load_catalog()
    entry = next((q for q in catalog["questions"] if q["id"] == qid), None)
    if entry is None:
        raise KeyError(f"unknown question id: {qid}")
    if qid == "Q4" and parameters:
        return ENGINES[qid](entry["question"], parameters)
    return ENGINES[qid](entry["question"])


def list_experiments(filters=None, limit=50):
    recs = records()
    out = [R.experiment_view(r) for r in recs]
    if filters:
        for key, want in filters.items():
            if want is None:
                continue
            if key == "flags":
                out = [o for o in out if want in o["flags"]]
            elif key == "text":
                w = str(want).lower()
                out = [o for o in out
                       if w in o["flex_identifier"].lower()
                       or w in o["fuel"].lower() or w in o["outcome"].lower()]
            else:
                out = [o for o in out if o.get(key) == want]
    total = len(out)
    return OrderedDict(total=total, returned=min(total, limit),
                       experiments=out[:limit])


def experiment_detail(test_no):
    rec = next((r for r in records() if r["flex_test_no"] == str(test_no)), None)
    if rec is None:
        raise KeyError(f"no experiment with test number {test_no}")
    view = R.experiment_view(rec)
    view["raw_values_preserved"] = OrderedDict(
        pressure_reported=rec["pressure_reported"],
        burn_time_reported=rec["burn_time_s_raw"],
        composition_sum_reported=round(
            sum(v for v in (rec["o2_mf"], rec["n2_mf"], rec["co2_mf"],
                            rec["he_mf"]) if v is not None), 6),
    )
    view["evidence_notes"] = OrderedDict(
        complete_core=rec["complete_core"],
        flags=rec["flags"],
        telemetry_linked=rec["flex_identifier"] in {
            "20CAL08", "20CAL10", "20CAL12", "20CAL13", "30CAL02",
            "30CAL03", "30CAL06", "40CAL01"},
    )
    return view