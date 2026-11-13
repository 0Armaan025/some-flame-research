# FLEX PSI-69 — Experimental Condition Comparability (Phase 3, P3-C)

Question answered: *Are the experimental conditions sufficiently comparable to
support the intended comparisons?*

All quantities are independently recomputed from the raw table
(`validation_checks.csv`). Mole fractions are always the **reported** values;
nothing is renormalised.

## 1. Condition coverage recap

- **Pressure bands (reported mmHg):** <560 mmHg: 104 records (65 MeOH / 39 Hep);
  560–800: 161 (85/76); 800–2100: 6 (5/1); >2100: 3 (2/1).
- **O2 mole fraction:** 15 distinct levels (0.12–0.34); methanol occupies all
  15, heptane 14; 14 shared.
- **Mixture families (O2/N2/CO2/He as reported):** 52 distinct families;
  methanol 46, heptane 37, **shared 31**. Records inside shared families:
  115 methanol / 106 heptane. 15 families are methanol-only, 6 heptane-only.

## 2. Fuel comparisons: three tiers

| Tier | Population | Assessment |
|---|---|---|
| Overall (all 274) | MeOH 157 / Hep 117 | **Confounded** — differing mixtures, pressures and diluents; any overall fuel difference is also a condition difference |
| Within shared families | 115 / 106 records | **Usable for descriptive contrasts** — still conditional on independence (P3-B) and on label/unit limitations |
| Within matched cells (fuel × family × band) | see §3 | **Usable only where n is adequate** |

Fuel imbalance is substantial in sparse cells: many shared families hold
1–5 records per fuel, so fuel contrasts at cell level are underpowered and
sensitive to the flagged records (see `diameter_analysis.csv` screened vs
as-reported rows).

## 3. CO2 vs He substitution cells (the ten matched-O2 cells)

A cell is defined by an O2 level at which both a CO2-substituted and a
He-substituted family exist. **O2 agreement alone does not make a cell
matched.** Each cell is evaluated on three independent criteria:
(a) reported N2 balance agreement, (b) shared pressure bands, (c) per-side
sample size (≥3 required).

| O2 | n CO2-side | n He-side | N2 CO2-side | N2 He-side | Bands shared | Verdict |
|---|---|---|---|---|---|---|
| 0.14 | 2 | 2 | {0.50} | {0.51} | 560–800 | **Not comparable** — both sides n=2, N2 differs |
| 0.15 | 8 | 2 | {0.35,0.53,0.54} | {0.55} | 560–800 | **Not comparable** — He side n=2, N2 differs |
| 0.16 | 4 | 3 | {0.59} | {0.59} | 560–800 | **Comparable** (N2 matched, shared band, n≥3) |
| 0.17 | 11 | 10 | {0.38,0.63} | {0.38,0.63} | 560–800; <560 | **Comparable** |
| 0.18 | 19 | 10 | {0.42,0.67} | {0.42,0.67} | 560–800; <560 | **Comparable** |
| 0.19 | 5 | 2 | {0.71} | {0.71} | 560–800 | **Not comparable** — He side n=2 (N2 matched) |
| 0.20 | 18 | 7 | {0.44,0.45,0.75} | {0.45,0.75} | 560–800; <560 | **Partially comparable** — N2 sets differ (CO2 side has an extra 0.44 family); only N2=0.45/0.75 sub-cells align |
| 0.21 | 18 | 7 | {0.09,0.49,0.64} | {0.49,0.64} | 560–800; <560 (CO2 side also spans >800 bands) | **Partially comparable** — N2 sets differ; CO2 side additionally spans the high-pressure family |
| 0.23 | 16 | 3 | {0.52,0.56} | {0.52} | <560 | **Partially comparable** — N2 sets differ; only the 0.52 sub-cell aligns |
| 0.24 | 16 | 3 | {0.56} | {0.56} | 560–800; <560 | **Comparable** |

**Result: 4 cells fully comparable (O2 = 0.16, 0.17, 0.18, 0.24); 3 partially
comparable at sub-cell level (0.20, 0.21, 0.23); 3 not comparable (0.14, 0.15,
0.19).** No pooled diluent-type estimate may be formed by combining cells:
each defensible contrast is within one O2 × N2 × pressure-band cell.

(Phase 2's `condition_analysis.csv` carries the same verdicts with the
per-side counts; Phase 3 recomputes them independently — counts agree.)

## 4. Pressure effects

- **Above 800 mmHg (9 records): all belong to the single family
  O2=0.21/N2=0.09/CO2=0.70/He=0.** Pressure and diluent are inseparable
  there; **no independently identified pressure effect exists in this
  region.**
- **Within-family pressure variation:** the high-pressure family has no runs
  outside 800–2100/>2100 mmHg, so even within-family cross-band comparison is
  impossible for it. Other families are band-constrained too (each family
  appears in only 1–2 bands; e.g. the air baseline 560–800 only).
- **Defensible pressure statement:** none beyond "the dataset contains
  observations at the reported pressures" — the design confounds pressure
  with campaign series throughout, not only above 800 mmHg.

## 5. Other comparability limits

- **Temperature:** not recorded per run anywhere; spec requires 18–27 °C. All
  cross-condition comparisons carry an unquantified temperature confound.
- **Fuel temperature/purity:** spec-level only (purity >99.5%, degassed).
- **Gravity:** not recorded per run; spec < 1e-4 m/s².
- **Fiber support:** known only for the 8 telemetry-linked runs (all
  `FIBER_USAGE_FLAG = No`); unknown for 266 records.
- **Session/procedural dependence:** see P3-B — condition selection was
  adaptive, so the marginal condition distribution is design-generated.
