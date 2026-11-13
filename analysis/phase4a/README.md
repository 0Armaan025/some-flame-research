# FLEX PSI-69 — Phase 4A: Comparative Results & Scientific Synthesis

Scope, execution instructions, and findings summary. The complete scientific
report is `research_report.md`.

## Scope

One research question: *what measurable differences between methanol and
n-heptane are supported by the FLEX-PSI69 records, and how strong are the
available comparisons?* Everything prohibited by the Phase 4A brief was
avoided: no units or physical meaning assigned to the unresolved
burning-rate column, no constants, no d²-law fits, no chemical-extinction
inference, no time-resolved analysis, no pixel-scale inference, no imputation,
no causal claims, no ML, no contact with originators, no external publication.
Phases 1–3.5, raw data, schema, src, and tests are frozen (per-file SHA-256
enforced by the test suite).

## Execution

```bash
notebooks/.venv/bin/python analysis/phase4a/run_analysis.py      # CSVs + figures + manifest
notebooks/.venv/bin/python -m pytest analysis/phase4a/tests/ -v  # 22 tests
```

Deterministic: seeded permutation (200 000 draws, seed 20261112) and bootstrap
(20 000 resamples, seed 20261112); re-running reproduces every output
byte-identically (tested).

## Files

| File | Contents |
|---|---|
| `research_report.md` | full scientific report (methods, results, integrity, bounded conclusions) |
| `results_summary.csv` | headline comparisons: population, medians, statistic, p, permutation p, effect size, bootstrap CI, sensitivity, verdict |
| `outcome_comparison.csv` | 2×3 contingency, proportions, per-outcome Fisher + Holm, Freeman–Halton, Cramér's V |
| `duration_comparison.csv` | duration descriptive by fuel and outcome + contrast; the two `~` records verbatim |
| `diameter_comparison.csv` | initial-diameter descriptive by fuel and outcome + contrast + the two collision records verbatim |
| `extinction_diameter_assessment.csv` | missingness and stats by fuel×outcome, screened variants, the eight zero records verbatim, d_ext/d0 ratios |
| `condition_comparison.csv` | ten matched-O2 cells (4 full / 3 partial / 3 rejected) with per-side counts, N2 sets, bands, verdicts; pressure distribution + confounding disclosure |
| `sensitivity_analysis.csv` | collision exclusions, anomaly screening, permutation p-values, series-level contrasts |
| `limitations_register.csv` | 10 limitations mapped to frozen-phase findings |
| `figures/fig01–fig06*.png` | outcomes, duration, diameter (collision marked), extinction diameter (zeros marked), condition cells, pressure confounding |
| `run_analysis.py`, `flex4a.py`, `run_manifest.json`, `tests/test_phase4a.py` | pipeline, independent library, manifest, 22 tests |

## Headline findings

1. **Outcome labels** differ strongly: Extinction 80.3% (MeOH) vs 51.3% (Hep);
   Disruption 14.6% vs 32.5%; Completion 5.1% vs 16.2%. Freeman–Halton
   p = 1.75×10⁻⁶, Cramér's V = 0.3099; Holm-adjusted per-outcome p ≤ 3.5×10⁻³.
   Descriptive label difference; Disruption is semantically unverified.
2. **Burn duration**: medians 12.1 s vs 7.5 s; MWU U = 4838, p = 1.17×10⁻⁹
   (permutation 5×10⁻⁶); rank-biserial r = 0.438; median difference −4.6 s
   (95% CI −7.8 to −2.9). Strongest supported difference — conditional on
   independence.
3. **Initial diameter**: p = 0.0623 as reported, **p = 0.0450 with either
   193F001 record removed**, p = 0.123 with anomalies screened → reported as
   sensitivity-dependent, **not a confirmed difference**.
4. **Extinction diameter**: 28.1% missing; heptane median ratio 0.781 vs
   methanol 0.549 (as reported, incl. zeros); eight 0 mm records retained
   verbatim as measurement-floor candidates.
5. **Conditions**: only 4 of 10 matched-O2 CO2/He cells are fully comparable
   (O2 = 0.16, 0.17, 0.18, 0.24); no pooled diluent estimate; all 9 records
   above 800 mmHg in one CO2 family → pressure effect blocked.

## Requirement traceability

Evaluated against the frozen Phase 3 R1–R10 list (Phase 3↔3.5 mapping in
`analysis/evidence_resolution/README.md` §2b): R1 (blocked — no rate
quantity computed), R2 (labels only), R3 (no image use), R4 (no telemetry
use), R5 (pressure descriptive + FCU cross-check cited), R6 (composition as
reported, never renormalised), R7 (independence caveated + series-level
sensitivity), R8 (8-run-only metadata respected), R9 (chemical extinction not
claimed), R10 (uncertainty via bootstrap CIs and effect sizes; calibration
gaps disclosed).

## Completion statement

This is comparative experimental analysis of recorded quantities, not
validated physical modelling. No burning constant, d²-law parameter,
evaporation constant, extinction limit, or chemical-extinction quantity was
computed, and no causal effect is claimed.
