# Phase 5 Review — Manuscript Consistency and Compliance

## A. Required consistency checks (all verified against the frozen Phase 4A outputs)

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Methanol/heptane outcome counts and denominators | **PASS** | 157 / 117; Extinction 126 vs 60, Disruption 23 vs 38, Completion 8 vs 19 (`outcome_comparison.csv`) |
| 2 | Outcome percentages and Freeman–Halton | **PASS** | 80.3/14.6/5.1% and 51.3/32.5/16.2%; FH p = 1.75×10⁻⁶; V = 0.3099; χ² = 26.31 |
| 3 | Holm-adjusted p-values and their outcomes | **PASS** | Extinction 1.55×10⁻⁶; Disruption 1.32×10⁻³; Completion 3.46×10⁻³ |
| 4 | Duration n, medians, IQRs, U, effect size, CI | **PASS** | 155/111 (missing 1/5, approx 1/1); 12.10 vs 7.50 s; IQRs 7.85–17.90 / 3.30–11.25; U=4838; r=0.4376; −4.6 s (CI −7.8 to −2.9) |
| 5 | Direction of the duration difference | **PASS — stated explicitly** | the −4.6 s difference is **heptane minus methanol** (7.50 − 12.10); stated in §6.2, Table 3, Figure 2 caption, abstract |
| 6 | Permutation p-value characterised | **PASS** | described as a 200 000-draw Monte Carlo estimate with resolution 1/(N+1) ≈ 5×10⁻⁶ (paper §5, §6.2) |
| 7 | Initial-diameter 193F001 sensitivity retained | **PASS** | p = 0.0623 as reported; 0.0450 with either colliding record removed; 0.123 screened; series-level 0.312; verdict "sensitivity-dependent" (paper §6.3, Table 4, Fig. 3) |
| 8 | Extinction-diameter missingness and measurement-floor records | **PASS** | 77 missing (28.1%); eight recorded 0 mm retained and flagged (all Heptane; Disruption ×4, Completion ×4) |
| 9 | Four fully comparable cells; partial/rejected identified | **PASS** | full: O₂ 0.16/0.17/0.18/0.24; partial: 0.20/0.21/0.23 (N₂ differs); rejected: 0.14/0.15/0.19 (n<3) |
| 10 | Pressure confounding and independence | **PASS** | all 9 records >800 mmHg in the single CO₂ family; independence explicitly not established (sequential adaptive design, 81 series, collision) |

## B. Manuscript integrity rules applied

- Every headline number quoted from a generated CSV; the Phase 5 test suite re-parses `research_paper.md` and asserts the numbers against the CSVs (see `tests/test_manuscript_consistency.py`).
- No claim of causation; no unit or physical interpretation assigned to the burning-rate column; no burning/evaporation constant, d²-law parameter, chemical-extinction limit, or extinction threshold claimed (verified by absence tests in `analysis/phase4a/tests/` and by explicit status text here).
- All ten limitations are present in the paper (§8) and in `limitations_and_caveats.md`; none is buried.
- Citations are only those documented in the project's source registers ([R1]–[R10] from the PSI-69 record's publication table and the local document set) plus canonical statistical-method references; no page numbers or identifiers were invented.

## C. Consistency across sections

- Abstract ↔ Results ↔ Discussion ↔ Conclusions: identical headline values (verified by the consistency tests); abstract adds no number absent from the results.
- Figure captions (`figure_captions.md`) state what each figure demonstrates and what it does not; each references its source CSV.
- Tables (`tables.md`) reproduce the CSVs exactly, including denominators and exclusion-rule labels.

## D. Frozen-state confirmation

- `analysis/phase4a` outputs are referenced (relative paths), not modified; their bytes and hashes are asserted unchanged by the Phase 5 suite.
- Phases 1–3.5, raw data, schema, `src/`, and existing tests: unchanged (59-file hash constants in `analysis/phase4a/tests/test_phase4a.py`; re-verified on each run).

## E. Frozen-phase reproducibility defect discovered during final checks (documented, not modified)

**D-P4A-1 — non-deterministic display order in one frozen output.**
`analysis/phase4a/condition_comparison.csv` is reproducible in *content* but
not in *bytes*: its comparability-verdict note strings interpolate Python
`set` objects (e.g. `identical N2 balance {'0.42', '0.67'}`), and set
iteration order is randomised per process by the interpreter's hash seed. Two
consecutive runs therefore differ only in the ordering inside those set
literals; every count, median, IQR and verdict string is identical (verified
by diffing consecutive runs). The other seven Phase 4A CSVs are byte-identical
across runs.

- **Why not fixed in place:** Phases 1–4A are frozen deliverables; the defect
  has no numeric effect (display only), so it is recorded here as a
  frozen-phase finding rather than silently rewritten.
- **How it is handled in this package:** the Phase 5 integrity checks compare
  `condition_comparison.csv` against the Phase 4A manifest hash with the set
  literals normalised (sorted), so the verification remains exact for all
  numeric content and deterministic across runs.
- **Recommended follow-up (Phase 4B or later, authorisation required):**
  format those note strings with `sorted(...)` in `run_analysis.py` and bump
  the manifest; this would restore byte-level reproducibility for all outputs.
- **Consequence for the test suites:** the frozen Phase 4A suite's
  `test_rerun_byte_identical` is therefore intermittently failing (21/22
  stable; the failing assertion is display-only). The Phase 5 suite verifies
  the same guarantee deterministically by content re-derivation for that file
  and by hash for the other seven CSVs; the paper's reproducibility section
  states the exception explicitly.

## F. Unresolved manuscript issues

None outstanding. All manuscript numbers verify against the frozen CSV
outputs; the single residual qualification is the display-order caveat
documented in E, which affects no claim, table or figure in the paper. Known residual qualifications (not manuscript defects): the
Monte Carlo permutation estimate's finite resolution (§5 of the paper); the
heptane extinction-diameter mean being pulled below its median by the eight
retained zeros (stated); and the partial cells' per-side N₂ differences
(tabulated, not pooled).
