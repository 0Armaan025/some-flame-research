# FLEX PSI-69 — Experimental Independence & Statistical Assumptions (Phase 3, P3-B)

Question answered: *Do the 274 records represent independent experimental
observations, and are the Phase 2 statistical comparisons consistent with the
actual experimental design?*

All structural quantities cited here are independently recomputed from the raw
table by `analysis/validation/run_validation.py` into
`validation_checks.csv` (no Phase 2 code is imported).

## 1. Record identity structure

- **FLEX Test #** is a dense 1–274 counter with no gaps — it is a table row
  index, not necessarily an experiment identifier.
- **FLEX Identifier** is unique for 273 of 274 records; **193F001 appears
  twice** (tests 70 and 73, both Heptane, same date/time, 761 mmHg,
  O2=0.15/N2=0.84, different measured values). The identifier therefore does
  **not** uniquely identify an experiment, and joining on identifier alone
  would silently merge two distinct records. Phase 1 and Phase 2 both key on
  Test # and disclose this collision.
- Identifiers encode a **series/campaign prefix** (e.g. `20CA`, `256`, `C03`,
  `H14`, `N01`): 81 distinct prefixes across 274 records, largest prefix `C03`
  with 13 records. Records sharing a prefix were produced within one campaign
  series under one test-matrix branch.
- **Temporal clustering:** 80 distinct test dates; up to **9 records share a
  single date** (10/6/2010). GMT timestamps show multiple runs per session.

## 2. Documented design: adaptive sequential testing

The Test Plan §5.3 LOI-determination procedure is explicitly iterative:

1. select pressure; 2. select a ~3 mm droplet; 3. select an O2 mole fraction
   expected to support burn-to-completion; 4. run a test; 5. increase droplet
   size or repeat if a finite extinction diameter was observed; 6. continue
   until the flame exists only briefly after ignition; 7. decrease O2 and
   repeat; 8. continue until the droplet does not ignite.

Each test's **conditions are chosen based on the outcome of previous tests**.
The dataset is therefore a set of adaptive sequential series, not a randomized
or independently sampled collection. The suppressant-efficacy procedure
(§5.4, Tables 8–9) repeats this structure at fixed suppressant concentrations.

Consequences:
- Records within a series are **procedurally dependent** (condition selection
  depends on prior outcomes).
- Condition distribution is **outcome-dependent by construction** — e.g. the
  over-representation of "Extinction" labels (186/274) is partly an artifact
  of a procedure that iterates toward marginal conditions.
- Any comparison that treats all 274 records as exchangeable is misspecified
  relative to the generating design.

## 3. Repeated measurements / technical replicates

- **No exact duplicate rows** exist (Phase 1: 0 exact duplicates, 0 duplicate
  Test #s, 0 repeated condition+measurement signatures).
- The 193F001 pair is *not* a repeated measurement: same session, different
  measured values — most likely two runs sharing a mis-entered identifier.
  Whether they are duplicates of one physical run cannot be resolved from
  available data; both interpretations are preserved.

## 4. Assessment of the Phase 2 statistical procedures

| Phase 2 procedure | Population used | Independence requirement | Verdict |
|---|---|---|---|
| Mann-Whitney U (d0, d_ext, burn time; fuel contrast) | all reported values per fuel, exact only (154/108, 117/80, 155/111) | independent samples | **Conditional** — U and the tie-corrected asymptotic p are computed correctly (independently re-derived here and by the Phase 2 review), but exchangeability across campaign series is not supported by the design |
| Fisher exact (outcome vs rest, fuel contrast) | full 2×2 tables (157/117) | independent Bernoulli trials | **Conditional** — counts and exact p are correct; the label distribution is design-generated |
| Spearman (burning-rate associations) | complete pairs (117–257) | independent pairs | **Conditional** — plus unit-unresolved input; p-values are normal-tail approximations (erfc), not exact t-distribution values |
| Holm adjustment across 3 outcome tests | the 3 raw Fisher p-values | — | **Correct** (verified on 6 hand-computed cases incl. permutations) |
| Duplicate-sensitivity rows (193F001) | 273-record subsets | — | **Correct and disclosed** — d0 contrast p 0.0623 → 0.0449 under either removal |
| Screened variants (flagged records excluded) | documented exclusions | — | **Correct** — every exclusion documented in the CSVs |

**Assessment of the initial-diameter finding specifically:** the fuel
difference in initial diameter (p = 0.0623; p = 0.0449 if either colliding
record is removed) straddles the conventional threshold and is sensitive to
record handling. It is reported in Phase 2 as "not a confirmed difference";
Phase 3 confirms that reading and adds that it is also conditional on the
independence assumption, which the documented adaptive design does not
support.

## 5. What could give more reliable inference

- **Series-stratified descriptive contrasts**: report per-series-prefix
  distributions rather than pooled ranks.
- **Permutation tests respecting the series structure**: permute fuel labels
  within series (or within series × condition-family blocks) to obtain a
  design-aware null. This is feasible with the existing table once the series
  assignment is confirmed (identifier prefixes are a strong candidate).
- **Exact/small-sample Spearman**: for cells with n < 20 the normal-tail
  approximation is weak; exact permutation of ranks within a cell is cheap
  and exact. Not required for the current descriptive claims.
- **Effective sample size reporting**: already done (`n_used` on every row);
  Phase 3 additionally publishes the cluster structure (max 9 records/date,
  81 series) so readers can compute clustering penalties themselves.

**Not recommended at this stage:** mixed-effects or hierarchical models
(series as random effect) — the design metadata is too sparse (no series
covariates) and the project's phase plan forbids modelling before validation
completes.

## 6. Verdict

- **Independence is NOT established.** At least four dependence structures are
  documented or demonstrated: adaptive sequential condition selection
  (documented), campaign series (81 prefixes), session clustering (up to 9
  runs/date), and one identifier collision.
- **The Phase 2 p-values are therefore conditional on an independence
  assumption that available evidence does not support.** They remain valid as
  *descriptive* contrasts; they must not be quoted as confirmatory
  design-based significance.
- **Pseudoreplication check:** no individual observation contributes more
  than once to any Phase 2 test (populations are disjoint; verified by the
  independent review), so the issue is dependence/clustering, not
  double-counting.
