# FLEX PSI-69 — Phase 4A Research Report: Comparative Results & Scientific Synthesis

**Research question:** *What measurable differences between methanol and
n-heptane ("Heptane") are supported by the FLEX-PSI69 experimental records,
and how strong are the available comparisons?*

This is a **comparative experimental analysis**, not validated physical
modelling. No d²-law fit, burning constant, evaporation constant, chemical-
extinction inference, time-resolved analysis, or machine-learning model was
performed. Every number below is recomputed by `run_analysis.py` from the
frozen raw table (sha256 `37c88ce8…e1b96`) and is quoted from the generated
CSV outputs.

Reproduce: `notebooks/.venv/bin/python analysis/phase4a/run_analysis.py`;
tests: `notebooks/.venv/bin/python -m pytest analysis/phase4a/tests/ -v` (22 passed).

---

## 1. Scope and evidential basis

| Prior-phase constraint (frozen findings) | Consequence for this report |
|---|---|
| Burning-rate column definition/unit unverified (R1 BLOCKED) | the column is never analysed or interpreted; no unit, no constants |
| "Disruption" label undefined (R2) | outcome comparisons are descriptive label comparisons |
| Independence not established: adaptive sequential LOI design, 81 series, ≤9 runs/date, 193F001 collision, second timestamp cluster (R7 BLOCKED) | all p-values are reported as *conditional on an independence assumption*, with permutation and series-level sensitivity analyses |
| Clock domains unreconciled (R4 BLOCKED) | no time-resolved or telemetry analysis |
| Pressure/diluent confounded above 800 mmHg | no pressure effect claimed; pressure reported as observed distribution |
| Anomalies (0 mmHg C11M201; 8 zero-mm extinction diameters; 1 d_ext>d0) retained and flagged | as-reported and screened variants both reported; nothing imputed |
| Temperature/gravity known for 8/274 runs only (R8 partial) | cross-condition comparisons carry an unquantified temperature/g-level caveat |

## 2. Dataset and experimental method (as documented)

274 records (Methanol 157, Heptane 117), March 2009–December 2011, ISS/MDCA
(study PSI-69, DOI 10.60555/mbq8-0451). Documented method (EIRD/ERD/Test Plan):
fiber-supported or free droplets of 1.5–6 mm ignited in O2/N2/CO2/He mixtures
(0.1–0.4 O2, 0.5–3 atm) under a <10⁻⁴ m/s² microgravity requirement; droplet
diameters derived from back-lit imaging (30 µm resolution requirement); outcome
labels recorded per test. Measured variables: initial diameter, visible flame
extinction diameter, a recorded burning-rate scalar (**unit unresolved**),
burn time, plus nominal conditions. **The table records outcomes; it does not
record chemical extinction.**

## 3. Results

### 3.1 Outcome-label composition (descriptive, label-level)

| Outcome | Methanol (n=157) | Heptane (n=117) |
|---|---|---|
| Extinction | 126 (80.3%) | 60 (51.3%) |
| Disruption | 23 (14.6%) | 38 (32.5%) |
| Completion | 8 (5.1%) | 19 (16.2%) |

- Freeman–Halton exact test of the 2×3 table: **p = 1.75×10⁻⁶**;
  Cramér's V = **0.3099** (a large-vs-medium effect by the usual heuristics;
  the table is strongly imbalanced in sample size).
- Per-outcome Fisher (vs rest), Holm-adjusted across the three contrasts:
  Extinction **1.55×10⁻⁶**, Disruption **1.32×10⁻³**, Completion
  **3.46×10⁻³** (unadjusted 5.16×10⁻⁷, 6.62×10⁻⁴, 3.46×10⁻³).
- **Interpretation limit:** these are *recorded labels*. "Disruption" has no
  documented definition, and Extinction is a *visible flame* outcome, not
  chemical extinction. The difference is a property of the experimental
  programme (which iterated each fuel toward marginal conditions), not
  mechanistic proof.

### 3.2 Burn duration (strongest supported difference)

| Fuel | n used | missing | median (s) | IQR (s) |
|---|---|---|---|---|
| Methanol | 155 | 1 | 12.10 | 7.85–17.90 |
| Heptane | 111 | 5 | 7.50 | 3.30–11.25 |

(The two `~`-approximate records — 6 s, 9 s — are excluded from statistics and
listed verbatim.)

- Mann–Whitney U = 4838, asymptotic p = 1.17×10⁻⁹; permutation p = 5×10⁻⁶
  (200 000 draws).
- Effect size (rank-biserial) **r = 0.438** — a large rank separation.
- Median difference (heptane − methanol) **−4.6 s, 95% bootstrap CI −7.8 to
  −2.9 s** (20 000 resamples, seeded).
- By outcome, medians: methanol Extinction 11.1 s (n=124), Disruption 15.6 s
  (n=23), Completion 20.9 s (n=8); heptane Extinction 4.3 s (n=59),
  Disruption 11.6 s (n=34), Completion 8.9 s (n=18).
- **Interpretation limit:** duration is not a combustion-mechanism
  measurement; the difference is confounded with the design (different
  condition programmes per fuel) and conditional on independence.

### 3.3 Initial droplet diameter (sensitivity-dependent — not a confirmed difference)

| Fuel | n used | missing | median (mm) | IQR (mm) |
|---|---|---|---|---|
| Methanol | 154 | 3 | 3.05 | 2.645–3.553 |
| Heptane | 108 | 9 | 2.92 | 2.408–3.438 |

- As reported: MWU U = 7190, p = 0.0623; permutation p = 0.28; rank-biserial
  r = 0.135; median difference −0.13 mm (95% bootstrap CI −0.395 to +0.100).
- **193F001 collision:** removing *either* disputed record gives U = 7036,
  **p = 0.0450** (n=154/107). The comparison crosses the conventional
  threshold depending on how the colliding pair is handled — reported, not
  resolved by preferring either version.
- Anomaly screening (excluding the 10 flagged records) gives p = 0.123;
  duration remains p ≈ 2×10⁻⁹ under the same screening.
- **Series-level sensitivity** (per-series medians for the 4 of 81 series
  with ≥3 records of each fuel): p = 0.312, with the heptane series median
  larger in only 1 of 4 series — directionally inconclusive at the series
  level, and n_series is too small for inference.
- **Verdict: sensitivity-dependent, not a confirmed difference.**

### 3.4 Visible flame extinction diameter

- Measured for 197 of 274 records (missing 77 = 28.1%; methanol 40/157,
  heptane 37/117).
- Ratio (visible flame extinction diameter / initial diameter), as reported:
  methanol median 0.549 (n=117, IQR 0.466–0.793), heptane median 0.781
  (n=80, IQR 0.345–0.923); the heptane mean (0.633) sits below its median
  because the **eight recorded 0 mm records** are included in the as-reported
  variant.
- The eight 0 mm records (all Heptane; Disruption ×4, Completion ×4) are
  listed verbatim in `extinction_diameter_assessment.csv`. A recorded 0 is
  **not** an ordinary positive measurement and **not** proof of a physical
  zero: the Test Plan documents a measurement floor ("extinction droplet
  sizes … too small to either be observed or measured"), so a non-detection
  placeholder is plausible, but 4 of the 8 carry the Completion label and no
  source documents the coding convention.
- Screened variants (flagged records excluded) are reported alongside every
  as-reported row; missing values are never invented.
- The label is *visible flame* extinction throughout — chemical extinction is
  not claimed (R9 BLOCKED).

### 3.5 Condition comparisons (CO2 vs He substitution cells)

Of the 10 matched-O2 cells, **4 are fully comparable** — O2 = 0.16 (CO2 n=4 /
He n=3), 0.17 (11/10), 0.18 (19/10), 0.24 (16/3): identical reported N2
balances, shared pressure bands, ≥3 records per side. **3 are partial**
(O2 = 0.20, 0.21, 0.23: N2 balances differ across sides) and **3 are rejected**
(O2 = 0.14, 0.15, 0.19: a side has <3 records). Per-cell descriptive medians
of burn duration by fuel are in `condition_comparison.csv`; **no cells are
pooled** and no causal diluent claim is made. Rejected cells are excluded from
primary comparisons with reasons recorded.

### 3.6 Pressure (distribution only)

Bands (reported mmHg): <560: 104; 560–800: 161; 800–2100: 6; >2100: 3.
**All 9 records above 800 mmHg belong to the single family
O2=0.21/N2=0.09/CO2=0.70/He=0** — pressure and diluent composition are
confounded there, so **no independent pressure effect is claimed** anywhere in
this report. The 0 mmHg record (C11M201) is retained with its flag and
excluded from screened variants only.

## 4. Statistical integrity summary

- Effective sample size is reported with every statistic; denominators are
  explicit (157/117 for labels; 154/108 for diameters; 155/111 for durations).
- Tests: Mann–Whitney (tie- and continuity-corrected, asymptotic p reported
  alongside assumption-light permutation p), Fisher exact with Holm
  adjustment, Freeman–Halton for the 2×3 table, rank-biserial effect sizes,
  seeded percentile-bootstrap CIs, exact sign tests for series-level contrasts.
- **Independence is not established** (adaptive design, series clustering,
  identifier collision). Permutation tests assume exchangeability that the
  design does not guarantee; p-values are therefore conditional. The
  series-level analysis is the only comparison that does not assume record
  independence, and it covers 4 series only.
- Significance is not overstated: the diameter comparison is reported as
  sensitivity-dependent rather than as a difference; the outcome and duration
  differences are labelled descriptive.

## 5. Conclusions (bounded by the evidence)

1. **Supported:** recorded outcome-label composition differs strongly between
   fuels (FH p = 1.75×10⁻⁶, V = 0.31); burn duration distributions differ
   (median 12.1 vs 7.5 s; r = 0.44) — both as *descriptive* differences in
   the recorded quantities.
2. **Sensitivity-dependent:** initial diameter (p 0.0623 / 0.0450 / 0.123
   under the three record-handling rules) — **not confirmed**.
3. **Descriptive only:** visible-flame extinction diameters (missingness 28%;
   eight measurement-floor zeros flagged); condition-cell medians.
4. **Blocked:** burning-rate physics, pressure effects, chemical extinction,
   time-resolved analysis, temperature/gravity-conditioned comparisons.
5. **Every comparison remains conditional on an independence assumption the
   experimental design does not establish.**

## 6. Deliverables

`results_summary.csv` (headline comparisons with n, statistic, p, effect size,
CI, sensitivity, verdict); `outcome_comparison.csv`; `duration_comparison.csv`;
`diameter_comparison.csv`; `extinction_diameter_assessment.csv`;
`condition_comparison.csv`; `sensitivity_analysis.csv` (collision, screening,
permutation, series-level); `limitations_register.csv`; `figures/fig01–fig06`;
`run_manifest.json`; `tests/test_phase4a.py` (22 tests).
