# Reproducibility

## Environment

- Python 3.14.9, numpy 2.5.4, matplotlib 3.11.2, in the project-local
  virtual environment `notebooks/.venv` (the only dependency installs made
  during the project were local to that environment).
- No Git repository, remotes, uploads, or external contact at any phase. All
  work is confined to the local project directory.

## Inputs (frozen)

| Input | SHA-256 |
|---|---|
| `data/raw/flex/PSI-69_Experimental table_FLEX.csv` | `37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96` |
| `data/raw/flex/s_PSI-69.txt` | `cb9374159b9b01a83bfe53a0b8ba1a602793df86f298e0ad222615c55d200135` |
| `schema/v1.2.0.sql` | `d03e0b1605a393d9f1f7273eae90a785a2c4f32c9eb9b79615312afe87965c35` |

Every file of Phases 1–4A is additionally fingerprinted in
`analysis/phase4a/tests/test_phase4a.py` (59 protected-file constants); the
Phase 4A suite re-verifies them on every run.

## Pipeline (how to reproduce every number in this paper)

```bash
notebooks/.venv/bin/python analysis/phase4a/run_analysis.py        # all results
notebooks/.venv/bin/python -m pytest analysis/phase4a/tests/ -v    # 22 tests
notebooks/.venv/bin/python -m pytest analysis/phase5/tests/ -v     # 20 manuscript checks
```

- `run_analysis.py` gates on the raw-file SHA-256 before any computation,
  loads the table byte-preservingly (Windows-1252; `0x96` = missing marker;
  `~` = approximate), and writes all eight result CSVs, six figures, and
  `run_manifest.json`.
- Monte Carlo permutation and bootstrap use fixed seeds (20261112);
  re-running reproduces every output byte-identically (asserted in tests).
- Every statistic in the paper is quoted from a generated CSV; the Phase 5
  test suite re-checks the manuscript's headline numbers against those CSVs.

## Prior phases (frozen evidence base)

| Phase | Path | Role in this paper |
|---|---|---|
| 1 audit | `analysis/audit/` | dataset inventory, missingness, anomaly flags |
| 2 exploratory | `analysis/exploratory/` | first descriptive statistics (superseded by Phase 4A's independent recomputation) |
| 3 validation | `analysis/validation/` | evidence register, validation matrix R1–R10 |
| 3.5 evidence resolution | `analysis/evidence_resolution/` | anomaly forensics, clock/archive/metadata recovery, originator questions OQ-1–OQ-8 |
| 4A comparative | `analysis/phase4a/` | all results reported here |

## Verification chain

1. Phase 4A statistics were validated against hand-computed reference values
   (Mann–Whitney U and asymptotic p; Fisher exact p for a classic 2×2;
   Holm monotonicity) in the Phase 4A test suite.
2. The Phase 4A suite also asserts the collision-sensitivity p-values, the
   condition-cell classification, effective-n bookkeeping, the absence of NaN
   or imputed values, the absence of unit assignment to the burning-rate
   column, and the absence of modelling code.
3. This paper's numbers were re-checked against the generated CSVs by the
   Phase 5 consistency suite (20 tests; `analysis/phase5/tests/`).
4. One frozen Phase 4A output (`condition_comparison.csv`) is byte-stable in
   content but not in bytes: its note strings interpolate Python set literals
   whose display order is hash-seed randomised. Documented as frozen-phase
   defect D-P4A-1 in `phase5_review.md`; the Phase 5 suite verifies that file
   by content re-derivation instead of by hash.
4. The protected-file constants cover the raw dataset, the schema, `src/`,
   the existing tests, and every deliverable of Phases 1–4A.
