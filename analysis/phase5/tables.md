# Tables

All values are recomputed by `analysis/phase4a/run_analysis.py` from the raw
experimental table and are quoted from the Phase 4A CSV outputs (frozen).

## Table 1 — Recorded outcome labels by fuel

Source: `outcome_comparison.csv` (analysis A_outcome). Denominators are the
full fuel counts.

| Outcome | Methanol (n=157) | Heptane (n=117) |
|---|---|---|
| Extinction | 126 (80.3%) | 60 (51.3%) |
| Disruption | 23 (14.6%) | 38 (32.5%) |
| Completion | 8 (5.1%) | 19 (16.2%) |

## Table 2 — Outcome-label comparisons (two-sided Fisher, outcome vs rest)

Source: `outcome_comparison.csv` (A_outcome_fisher, A_outcome_fisher_holm,
A_outcome_table).

| Contrast | 2×2 counts (a,b,c,d) | Unadjusted p | Holm-adjusted p |
|---|---|---|---|
| Extinction | 126, 31, 60, 57 | 5.16×10⁻⁷ | **1.55×10⁻⁶** |
| Disruption | 23, 134, 38, 79 | 6.62×10⁻⁴ | **1.32×10⁻³** |
| Completion | 8, 149, 19, 98 | 3.46×10⁻³ | **3.46×10⁻³** |

Full 2×3 table: Freeman–Halton exact p = 1.75×10⁻⁶; Cramér's V = 0.3099;
χ² = 26.31. Label-level statistics only; not mechanism evidence.

## Table 3 — Burn duration by fuel

Source: `duration_comparison.csv` (B_duration). Exact values only; the two
`~`-approximate records are excluded from statistics and listed verbatim.

| Fuel | n used | missing | median (s) | IQR (s) |
|---|---|---|---|---|
| Methanol | 155 | 1 | 12.10 | 7.85–17.90 |
| Heptane | 111 | 5 | 7.50 | 3.30–11.25 |

Contrast: Mann–Whitney U = 4838; asymptotic p = 1.17×10⁻⁹ (Monte Carlo
permutation estimate 5×10⁻⁶, resolution ≈5×10⁻⁶); rank-biserial r = 0.438;
median difference (heptane − methanol) −4.6 s, 95% bootstrap CI −7.8 to
−2.9 s.

## Table 4 — Initial droplet diameter by fuel and sensitivity to record
handling

Source: `diameter_comparison.csv`, `sensitivity_analysis.csv`.

| Population | n (MeOH/Hep) | median MeOH | median Hep | U | p |
|---|---|---|---|---|---|
| As reported | 154/108 | 3.05 mm | 2.92 mm | 7190 | 0.0623 |
| Excluding 193F001 record 1 (test 70) | 154/107 | — | — | 7036 | 0.0450 |
| Excluding 193F001 record 2 (test 73) | 154/107 | — | — | 7036 | 0.0450 |
| Anomaly-screened (10 flagged records excluded) | 153/99 | — | — | 6700.5 | 0.123 |
| Series-level medians (4 of 81 series) | 4/4 | — | — | 4.0 | 0.312 |

Effect sizes (as reported / excluding a collision record): rank-biserial
r = 0.135 / 0.146; median difference −0.13 mm (95% bootstrap CI −0.395 to
+0.100 mm). **Verdict: sensitivity-dependent — not a confirmed difference.**

## Table 5 — Visible flame extinction diameter: availability and summaries

Source: `extinction_diameter_assessment.csv`.

| Group | measured (n) | missing | median (mm) |
|---|---|---|---|
| Methanol, all | 117 | 40 | — |
| Heptane, all | 80 | 37 | — |
| Methanol, Extinction | 103 | 23 | 1.67 |
| Heptane, Extinction | 56 | 4 | 2.77 |
| Methanol, Disruption | 9 | 14 | 1.53 |
| Heptane, Disruption | 15 | 23 | 0.47 |
| Methanol, Completion | 5 | 3 | 2.10 |
| Heptane, Completion | 9 | 10 | 0.12 |

Ratio to initial diameter (as reported, includes the eight recorded 0 mm):
methanol median 0.549 (n=117, IQR 0.466–0.793); heptane median 0.781
(n=80, IQR 0.345–0.923). The eight 0 mm records (all Heptane; Disruption ×4,
Completion ×4) are measurement-floor candidates, not physical zeros; visible
flame extinction only.

## Table 6 — Matched-oxygen CO₂/He substitution cells

Source: `condition_comparison.csv`.

| O₂ level | CO₂ side n | He side n | N₂ balance match | Shared band(s) | Class |
|---|---|---|---|---|---|
| 0.16 | 4 | 3 | yes | 560–800 mmHg | full |
| 0.17 | 11 | 10 | yes | 560–800; <560 | full |
| 0.18 | 19 | 10 | yes | 560–800; <560 | full |
| 0.24 | 16 | 3 | yes | 560–800; <560 | full |
| 0.20 | 18 | 7 | no ({0.44,0.45,0.75} vs {0.45,0.75}) | 560–800; <560 | partial |
| 0.21 | 18 | 7 | no | 560–800; <560 (CO₂ side spans high-pressure bands) | partial |
| 0.23 | 16 | 3 | no ({0.52,0.56} vs {0.52}) | <560 | partial |
| 0.14 | 2 | 2 | no ({0.5} vs {0.51}) | 560–800 | rejected (n<3) |
| 0.15 | 8 | 2 | no | 560–800 | rejected (n<3) |
| 0.19 | 5 | 2 | yes | 560–800 | rejected (n<3) |

Primary condition interpretation uses only the four full cells; partial and
rejected cells are reported with reasons and never pooled.

## Table 7 — Pressure distribution and confounding disclosure

Source: `condition_comparison.csv` (C_pressure). Reported mmHg bands:
<560: 104; 560–800: 161; 800–2100: 6; >2100: 3. All 9 records above 800 mmHg
belong to the single family O₂=0.21/N₂=0.09/CO₂=0.70/He=0 → pressure and
diluent confounded; no pressure effect claimed. The single 0 mmHg record
(C11M201; series siblings 531.1–536.3 mmHg) is retained with its flag.

## Table 8 — Burning-rate column status

Source: `burning_rate_analysis` evidence (Phases 3/3.5); 258/274 values
present. Definition/unit unresolved in all inspected documentation; the naive
d²-law-constant reading is contradicted (Spearman ρ vs d0²/t = −0.05 overall,
−0.40 heptane, +0.10 methanol). No physical rate quantity computed; the
column is treated as an unresolved recorded scalar.
