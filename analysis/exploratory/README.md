# FLEX PSI-69 — Phase 2 Exploratory Scientific Analysis

Read-only, reproducible exploratory analysis of the FLEX (Flame Extinguishment
Experiment) PSI-69 experimental table, built on top of the completed Phase 1
audit (`analysis/audit/`). Nothing under `data/raw/`, `schema/`, `src/`, or
`tests/` was modified, and no audit deliverable was regenerated.

**Run:** `notebooks/.venv/bin/python analysis/exploratory/run_analysis.py`
**Tests:** `notebooks/.venv/bin/python -m pytest analysis/exploratory/tests/ -v` (34 passed)
**Environment:** project-local `notebooks/.venv` (numpy, matplotlib, pytest installed there for this phase; no remote repository was created).

## 1. Research questions

Phase 2 is **descriptive and exploratory by design**. The questions it can
address with the audited data:

1. How are the measured quantities — initial droplet diameter, visible flame
   extinction diameter, the recorded burning-rate scalar, burn duration —
   distributed, and how do those distributions differ between methanol and
   n-heptane ("Heptane" as labelled in the source)?
2. How do measured quantities relate to the *recorded outcome labels*
   (Extinction / Disruption / Completion)?
3. What experimental conditions (O2, N2, CO2, He, pressure, mixture families)
   exist, in what combinations, and which comparisons are confounded?
4. Where is data missing, and in what pattern?

Questions requiring modelling, causal inference, or unit-resolved physics are
deliberately **blocked** (see §8).

## 2. Available measurements (as established by the Phase 1 audit)

274 records: Methanol 157, Heptane 117; dates 2009-03-05 → 2011-12-08.
196 records carry all four core measurements. Per-run telemetry exists for
8/274 runs only.

| Variable | Present | Missing | Unit status |
|---|---|---|---|
| Ambient pressure | 274 | 0 | **verified** mmHg (column header) |
| O2 / N2 / CO2 / He mole fractions | 274 | 0 | **verified** mole fraction (headers) |
| Droplet initial diameter | 262 | 12 | **verified** mm (header) |
| Visible flame extinction diameter | 197 | 77 | **verified** mm; *visible-flame basis only* — not chemical extinction |
| Burning rate | 258 | 16 | **UNRESOLVED** — source header "Burning rate; mm" is not a valid rate unit; treated strictly as a recorded scalar |
| Burn time | 268 (266 exact + 2 approximate) | 6 | **verified** s; 2 values carry the `~` approximation marker |
| Test end (outcome label) | 274 | 0 | categorical label, not a measured quantity |

No temperature, no gravity field, no fuel purity, no time-resolved
diameter/radiation data are present in the experimental table.

**Flagged observations (retained, never silently dropped):** pressure 0 mmHg
(C11M201), 8 Heptane extinction diameters of exactly 0 mm, 1 extinction
diameter > initial diameter (C13H102), 29 composition sums ≠ 1.000 (not
renormalised), 2 approximate burn times, identifier collision 193F001
(2 records), 27 "Extinction" labels without a measured extinction diameter.
39 records carry at least one flag.

## 3. Methods

- **Loading** (`flex_core.py`): the source CSV is read byte-preserving as
  latin-1 (identical to Windows-1252 for every byte present here), exactly as in
  the Phase 1 audit; the 0x96 byte is the Windows-1252 en-dash artifact. Empty fields and the `0x96`
  artifact byte are "not reported"; they are never imputed, zero-filled, or
  carried forward. `~`-prefixed values keep their number with an
  `approx` flag (mirroring `measurement_approx` in `schema/v1.2.0.sql`).
- **Validation**: input sha256 must equal the Phase 1-recorded digest
  (`37c88ce8…e1b96`); record counts, fuel counts, flag counts and the
  duplicate identifier must match the audit. The pipeline refuses to run
  otherwise.
- **Two result modes everywhere**: `as_reported` (all reported values,
  including flagged ones) and `screened` (records with value-integrity flags
  excluded). Every exclusion is a documented row/column in the CSVs; the
  screened numbers never replace the as-reported ones.
- **Statistics** (`flex_core.py`): count, mean, sample SD (ddof=1), min, Q1,
  median, Q3, max, IQR. Quartiles use numpy's default linear interpolation
  (inclusive, "method 7") — stated in every CSV and in `run_manifest.json` so
  results are reproducible. Descriptive statistics are computed on **exact
  values only**; approximate values are counted (`n_approx_excluded`) and
  reported separately.
- **Comparison tests** (implemented in-repo without scipy, validated against
  hand/published reference values in `tests/`): two-sided Mann-Whitney U
  (tie- and continuity-corrected normal approximation), Spearman rank
  correlation (dimensionless, therefore unit-invariant), two-sided Fisher
  exact with Holm-Bonferroni adjustment. All are used as **exploratory
  descriptive contrasts**; p-values are reported with sample sizes and
  caveats and are not treated as confirmatory evidence.
- **Figures** (matplotlib, Agg backend, 150 dpi): consistent conventions —
  fuel colours blue (Methanol) / red (Heptane); count axes start at zero;
  every panel carries axis labels, units only where verified, and n in
  labels/legends; flagged and approximate points are drawn with distinct
  markers; fixed random seed for jitter (`20241112` / `19700305`).

## 4. Outputs

| File | Contents |
|---|---|
| `descriptive_statistics.csv` | 5 variables × 3 strata × 2 modes: n, mean, SD, min, Q1, median, Q3, max, IQR, missing and approx counts |
| `diameter_analysis.csv` | diameter distributions by fuel and outcome, IQR outlier fences (labels only), d_ext/d0 ratios, Mann-Whitney fuel contrasts |
| `burning_rate_analysis.csv` | recorded-scalar statistics by fuel/outcome + Spearman associations; every row marked unit-unresolved |
| `duration_analysis.csv` | burn-time statistics by fuel/outcome (exact only), the two approximate records listed separately, Mann-Whitney fuel contrast |
| `outcome_analysis.csv` | outcome counts/proportions, measurement availability within outcomes, Fisher exact + Holm-adjusted fuel contrasts |
| `condition_analysis.csv` | 52 mixture families with coverage and confounding flags; 10 matched-O2 CO2-vs-He substitution cells with comparability verdicts |
| `figures/fig01…fig07*.png` | diameter distributions, fuel comparison, duration, outcomes, condition coverage, missingness, extinction diameter by outcome |
| `run_manifest.json` | input path + sha256, validation results, script version, UTC timestamp, dependency versions, output hashes, integrity rules, limitations |
| `tests/test_exploratory.py` | 34 tests: loading, hash preservation, missing/approx handling, flags, statistics reference values (incl. Spearman p tail), output generation, manifest-hash verification, duplicate-sensitivity and cell-guard checks |

## 5. Findings

### Established (directly verifiable from the data)

- **Counts and coverage.** 274 records (157/117); 196 with all four core
  measurements; extinction diameter missing for 77 records (28.1% of all;
  25.5% methanol, 31.6% heptane).
- **Fuel outcome composition differs.** Recorded labels: methanol 126/23/8
  (Extinction/Disruption/Completion), heptane 60/38/19. Fisher exact,
  outcome vs rest: Extinction p<0.00001, Disruption p=0.00066,
  Completion p=0.0035; Holm-adjusted 1.55e-06 / 0.00132 / 0.00346.
  This is a property of the *recorded labels*; it is not evidence about
  chemical extinction.
- **Burn durations differ between fuels** (exact values): methanol median
  12.1 s (IQR 7.9–17.9, n=155), heptane 7.5 s (IQR 3.3–11.25, n=111);
  Mann-Whitney U=4838, p≈1.2×10⁻⁹.
- **Initial diameters**: methanol median 3.05 mm (n=154), heptane 2.92 mm
  (n=108); Mann-Whitney p=0.062 (exploratory contrast, not a confirmed
  difference).
- **Visible flame extinction diameter relative to initial diameter**
  (as reported): median ratio 0.549 methanol (n=117), 0.781 heptane
  (n=80). Screened variants (flagged records excluded) shift to
  **mean** 0.611 methanol / 0.699 heptane — note the as-reported figures
  above are **medians**; comparing a screened mean against an as-reported
  median would invert the apparent effect (screened medians are 0.552 /
  0.799).
- **Duplicate-sensitivity disclosure (193F001).** Initial-diameter fuel
  contrast p = 0.0623 as reported; excluding *either* of the two colliding
  193F001 records moves p to 0.0450 (d_ext 0.2915→0.3607; burn time
  1.17×10⁻⁹→1.94×10⁻⁹). Both sensitivity rows are in
  `diameter_analysis.csv` / `duration_analysis.csv`. The "not a confirmed
  difference" reading of the initial-diameter contrast is therefore
  duplicate-sensitive and is reported as such.
- **Condition coverage.** 52 mixture families. O2 spans 0.12–0.34 mole
  fraction; inert diluents CO2 (up to 0.70) and He (up to 0.45) substituted
  against N2. Pressure bands: <560 mmHg 104 records, 560–800 mmHg 161,
  800–2100 mmHg 6, >2100 mmHg 3 (9 above 800 mmHg total, all in the single
  family O2=0.21/N2=0.09/CO2=0.70/He=0).
- **Missingness pattern.** Missingness is concentrated in the measurement
  columns (extinction diameter worst), not in condition columns; 27 records
  labelled Extinction have no measured extinction diameter. The mechanism
  (MCAR/MAR/MNAR) cannot be established from this table.

### Exploratory observations (require confirmation; no causal reading)

- Within recorded outcome labels, heptane records show a wider spread of
  visible flame extinction diameters (IQR 0.71–3.00 across outcomes vs
  methanol 1.29–2.32), partly driven by the eight 0 mm placeholders that are
  flagged, not dropped (screened ratios above).
- The recorded burning-rate scalar is larger for heptane than methanol in
  median terms (0.540 vs 0.460; SD 0.161 vs 0.109) — **provisional only**,
  because the unit is unresolved and gas temperatures are unrecorded.
- Spearman association between the recorded burning-rate scalar and burn
  time: ρ=0.038, n=257 — essentially no monotone association, which is itself
  unsurprising for a per-run scalar and warns against treating the scalar as
  an instantaneous rate.
- Ten matched-O2 diluent-substitution cells exist (O2 = 0.14…0.24) where
  CO2-substituted and He-substituted families co-occur. Per-cell
  `n_co2_substituted` / `n_he_substituted` counts, reported N2 balances per
  side, shared-pressure-band analysis and a comparability verdict are in
  `condition_analysis.csv`. The verdict is only affirmative when both sides
  have n ≥ 3, share at least one pressure band, and have identical reported
  N2 balances; N2 balances match in 5 of the 10 cells and three cells have a
  side with n < 3, so only a subset of these contrasts is defensible. These
  are the only diluent-type contrasts the design supports.

### Blocked (data are insufficient)

- Any **pressure effect** claim: the 9 records above 800 mmHg all belong to
  one CO2-diluted family; pressure and diluent are inseparable there.
- Any **burning-rate constant (d²-law)** or physically interpreted rate: the
  unit is unresolved and only a single per-run scalar exists.
- **Chemical vs visible flame extinction**: no radical, emission, or
  gas-phase composition measurements exist.
- **Temperature, gravity, purity effects**: those variables are not
  recorded anywhere in the audited sources.
- **Time-resolved flame behaviour**: telemetry exists for 8 runs (all 2009
  ambient air, ~760 mmHg) across three unreconciled clock domains.

## 6. Confounding factors and limitations

1. Pressure ↔ diluent composition confounding above 800 mmHg (single family).
2. Ambient temperature never recorded; burning behaviour depends on it.
3. Gravity regime is not a table field; document-sourced only.
4. Fuel purity/specification unreported for both fuels.
5. Missingness mechanism unknown — patterns reported, never used to justify
   imputation.
6. `Burning rate; mm` header is not a valid unit; everything derived from it
   is provisional and dimensionless where possible.
7. Identifier collision 193F001 (two records share one identifier) weakens
   the independence assumption of the rank-sum tests.
8. Small, unbalanced cells (many families have 1–5 records per fuel) make
   stratum-specific contrasts fragile.
9. Outcome labels are operator/instrument-defined categories whose
   definitions are not in the audited files; they are kept strictly distinct
   from measurements.
10. Telemetry coverage (8/274 runs) is not representative of the condition
    matrix; three clock domains unreconciled.

## 7. Unresolved scientific questions

- Definition of `Test end` categories (Extinction/Disruption/Completion) per
  the FLEX test plan, and its relationship to visible flame extinction.
- The burning-rate unit and measurement method.
- Origin of the 0 mmHg and 0 mm placeholder values; identity behind the
  193F001 identifier collision.
- Whether the two `~`-approximate burn times are rounded or estimated values.

## 8. Recommended next steps

1. Resolve §7 metadata (test plan, data originator) before any modelling.
2. Extract and clock-reconcile the 5.4 GB image/FCI archives for the 8
   telemetry-linked runs, then assess time-resolved analyses there only.
3. For any future modelling: pre-register exclusion rules for flagged
   records, use screened datasets, and treat Phase 2 outputs as hypothesis
   generators, not as findings.

## 9. Reproducibility

```bash
notebooks/.venv/bin/python analysis/exploratory/run_analysis.py   # CSVs + figures + manifest
notebooks/.venv/bin/python -m pytest analysis/exploratory/tests/ -v
```

Entry point records input filename and sha256, script version, execution
timestamp (UTC), dependency versions, output hashes and row counts in
`run_manifest.json`. Statistical primitives are validated in
`tests/test_exploratory.py` against hand-computed and published reference
values (Mann-Whitney U and asymptotic p, Spearman ρ, Fisher exact p for the
classic [[3,0],[0,3]] → 0.1 table, Holm adjustment monotonicity). The raw
dataset's sha256 is asserted in the test suite; Phase 2 never writes to
`data/raw/`, `schema/`, `src/`, `tests/`, or `analysis/audit/`.

## 10. Independent review and fixes applied

An independent reviewer (dispatched per the `requesting-code-review` skill, with its own parser recomputing every statistic from the raw CSV in a scratch directory) verified the seven requested points. Verdicts after fixes: CSV/raw agreement **PASS** (0 mismatches at 1e-9 across all statistic CSVs, plus byte-identical re-run of the whole pipeline); test populations **PASS**; Holm correction **PASS** (6 hand-computed cases); missing/approximate handling **PASS**; matched-condition cells **PASS-with-caveats** (n≥3 guard, per-side N2 reporting, 5/10 cells N2-matched); manifest hashes **PASS** (13/13, now also asserted in the suite); dependence/pseudoreplication **PASS-with-caveats** (sensitivity rows added).

Fixes made from that review: Spearman p-value tail inversion (`flex_core.py` — previously every delivered p was exactly 1.0); ratio-row n-identity in `diameter_analysis.csv`; duplicate-sensitivity rows for every fuel contrast (193F001); cell guard `min(n per side) ≥ 3` plus per-side N2 sets and explicit columns `n_co2_substituted` / `n_he_substituted` (no more CO2 counts in a column named `n_methanol`); README median-vs-mean wording and duplicate-sensitivity disclosure; figure 02 y-axis now genuinely zero-based with a matching title; figure 05 plots the flagged 0 mmHg placeholder with a distinct marker; CSV path resolution no longer depends on the working directory; tests now cover Spearman p reference values, an independent-parser recomputation of burning-rate statistics, and manifest-hash verification.
