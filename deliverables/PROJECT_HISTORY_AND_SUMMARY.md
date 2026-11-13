# FLEX-PSI69 — Project History and Summary

*A complete, readable account of the project: what we investigated, what we
found, what went wrong along the way, and where things stand. Written for a
technically curious student who knows programming but should not need to read
every research artifact.*

---

## 1. Original objective

The **Flame Extinguishment Experiment (FLEX)** burned single droplets of fuel
in carefully controlled gas mixtures aboard the International Space Station.
Because there is no buoyancy in microgravity, the burning is dominated by
diffusion — the cleanest regime for studying how droplets burn and how flames
go out. The experiment's public data release (**study PSI-69**, NASA's
Physical Science Informatics system, DOI 10.60555/mbq8-0451) contains one
table of 274 test records with two fuels: **methanol** (a non-sooting alcohol)
and **n-heptane** (a sooting hydrocarbon).

Our scientific question, fixed from the start and carried through every phase:

> **What measurable differences between methanol and n-heptane are supported
> by the FLEX-PSI69 records, and what are the limitations of those
> comparisons?**

Everything in this project exists to answer that question *defensibly* — no
overclaiming, no invented physics, no hidden assumptions.

## 2. The dataset

- **274 records**: Methanol 157, Heptane 117; test dates 5 March 2009 –
  8 December 2011.
- **Per record**: an outcome label (Extinction / Disruption / Completion),
  nominal pressure (mmHg), initial mole fractions of O₂/N₂/CO₂/He, initial
  droplet diameter (mm), visible flame extinction diameter (mm), a recorded
  burning-rate value, and burn time (s).
- **Per-run telemetry** (chamber conditions, radiometer, event logs, image
  archives) exists for only **8 of the 274 runs**.

## 3. Phase-by-phase history

### Phase 1 — Dataset audit (`analysis/audit/`)
- **What:** inventory every file; count records; find missing values, encoding
  artifacts, and anomalies.
- **Why:** you cannot compare data you have not validated.
- **Found:** 77 extinction diameters missing; 12 diameters missing; 34 fields
  carrying a Windows-1252 "blank marker" byte (0x96); 2 approximate burn
  times; a 0 mmHg pressure record; eight 0 mm extinction diameters; a
  duplicated identifier (193F001); 29 composition sums ≠ 1.000.
- **Produced:** dataset inventory, missing-data report, quality report, audit
  script.

### Phase 2 — Exploratory analysis (`analysis/exploratory/`)
- **What:** first descriptive statistics, distributions, and comparisons, with
  an independent test suite.
- **Why:** establish the measurable facts before interpretation.
- **Found:** outcome composition differs by fuel; burn durations differ;
  initial-diameter difference is borderline (p ≈ 0.062).
- **Produced:** six analysis CSVs, seven figures, manifest, 34 tests (a
  later independent review found and fixed a Spearman p-value bug here —
  documented in the correction register).

### Phase 3 — Scientific validation (`analysis/validation/`)
- **What:** an evidence register and a validation matrix: for every important
  claim, what evidence exists, at what level, and is it verified?
- **Why:** separate what the data *show* from what we *assume*.
- **Found:** the burning-rate column's definition/unit is **unresolved**
  (nothing in the documentation defines it); "Disruption" is an **undefined
  label**; experimental independence is **not established** (the test
  procedure is sequential and adaptive); telemetry clocks are unreconciled;
  per-run temperature/gravity exist for 8 runs only.
- **Produced:** measurement-provenance, independence, comparability,
  telemetry, and uncertainty assessments; evidence register; validation
  matrix R1–R10.

### Phase 3.5 — Evidence resolution (`analysis/evidence_resolution/`)
- **What:** forensic investigation of every unresolved item before conceding
  it: version archaeology across five engineering documents, reduction-code
  archaeology, identifier forensics, an image-archive census, clock-offset
  quantification, metadata recovery.
- **Found:** the study DOI and the dataset paper (NTRS 20150023456); the
  0 mmHg record is a corrupted transcription (its series siblings run at
  ~535 mmHg and it shares a timestamp with another record); the eight 0 mm
  values align with a documented measurement floor but their meaning is
  unconfirmed; 193F001 is two reductions of one run (or two deployments — not
  resolvable locally); six clock domains with ~1.2–1.7 s offsets and drift;
  the one-row chamber logs are at-ignition snapshots; a pressure cross-check
  against chamber telemetry within 0.06–1.24 mmHg for 8 runs.
- **Produced:** nine forensic reports, three registers, 23 tests, and eight
  prioritised originator questions (OQ-1…OQ-8) — prepared, never sent.

### Phase 4A — Comparative experimental analysis (`analysis/phase4a/`)
- **What:** the actual scientific results, computed independently of Phase 2
  with effect sizes, uncertainty intervals, and sensitivity analyses.
- **Found:** outcome-label composition differs strongly (Freeman–Halton
  p = 1.75×10⁻⁶, V = 0.3099); durations differ strongly (medians 12.10 vs
  7.50 s, U = 4838, p = 1.17×10⁻⁹, r = 0.438, −4.6 s CI [−7.8, −2.9]);
  initial diameter is **sensitivity-dependent** (p 0.0623 / 0.0450 / 0.123);
  4 of 10 diluent cells fully comparable; pressure effects confounded.
- **Produced:** eight result CSVs, six figures, sensitivity register,
  limitations register, 22 tests.

### Phase 5 — Research manuscript (`analysis/phase5/`)
- **What:** a full scientific paper, standalone abstract, tables, captions,
  limitations, reproducibility, references, a 7-slide outline, and a
  manuscript-consistency test suite (20 tests) that re-checks every headline
  number against the CSVs.
- **Produced:** `research_paper.md` (≈3 500 words) plus nine companion files.

### Phase 6 — Evidence intelligence engine & handoff (`intelligence/`, `prediction/`, `deliverables/`)
- **What:** first a validated recorded-outcome predictor (explanations,
  series-grouped validation, OOD warnings, API), then — after the platform
  pivoted to the NASA Space Apps objective — a deterministic
  question-to-evidence engine (`intelligence/`): seven supported scientific
  questions answered with traceable numbers, four-dimension interpretable
  evidence ranking, and explicit limitations, exposed through a documented
  API.
- **Found/exposed:** the evidence engine reproduces every frozen Phase 4A
  number (counts, p-values, cell verdicts, missingness) as cross-checks;
  comparability, confounding and sensitivity are first-class answer types
  rather than footnotes.
- **Produced:** `intelligence/` (engine, ranking, API, catalog, schema,
  21 tests) and the handoff documentation.

## 4. Main scientific findings (exact, verified numbers)

| Finding | Numbers | Strength |
|---|---|---|
| Outcome-label composition | Extinction 80.3% (126/157) vs 51.3% (60/117); FH p = 1.75×10⁻⁶; V = 0.3099 | descriptive difference in **recorded labels** |
| Burn duration | medians 12.10 s vs 7.50 s; U = 4838; p = 1.17×10⁻⁹; r = 0.438; median difference −4.6 s (95% CI −7.8 to −2.9) | strongest supported difference |
| Initial diameter | medians 3.05 vs 2.92 mm; p = 0.0623, **0.0450** if either 193F001 record is removed, 0.123 screened | **sensitivity-dependent — not confirmed** |
| Extinction diameter | 197/274 measured; medians of the ratio 0.549 vs 0.781; 8 zero-mm floor records | interpretation-limited |
| Conditions | 4/10 cells fully comparable; all 9 records >800 mmHg in one CO₂ family | diluent comparisons restricted; pressure blocked |
| Burning rate | 258 values; definition/unit unresolved; naive d²-law reading contradicted (ρ ≈ 0) | blocked |
| Independence | adaptive design; 81 series; duplicates | all p-values conditional |

## 5. Important problems discovered

1. **193F001 collision** — two records share one identifier, same timestamp,
   near-identical diameters, different reductions; deleting either changes the
   initial-diameter conclusion.
2. **Corrupted pressure record** — C11M201 reports 0 mmHg; its series runs at
   ~535 mmHg; never imputed, always flagged.
3. **Measurement-floor zeros** — eight extinction diameters of 0 mm (all
   Heptane); consistent with the documented "too small to measure" floor, but
   the coding convention is undocumented.
4. **77 missing extinction diameters** (28%) — mechanism unknown; never
   imputed.
5. **Unknown burning-rate unit** — no document defines the column; using it
   physically is prohibited.
6. **Unresolved "Disruption" semantics** — the word appears in none of the six
   inspected documents.
7. **Clock synchronisation** — six clock domains, offsets of 1.2–1.7 s with
   drift; no time-resolved analysis possible.
8. **Missing per-run metadata** — temperature/gravity/fiber for 8 of 274 runs.
9. **Experimental independence** — the adaptive LOI procedure means records
   are not independent draws.

## 6. Prediction system

- **Target:** the recorded outcome label (3 classes) — not combustion
  physics.
- **Features:** fuel, initial diameter, pressure, O₂/N₂/CO₂/He fractions,
  recoded diluent type — all pre-outcome, documented, populated. Excluded:
  burn time, extinction diameter, the unresolved burning-rate column, dates
  (series proxies), telemetry.
- **Validation:** out-of-fold predictions with **series-grouped** cross-
  validation (5 folds × 3 seeds, 81 groups); the 193F001 pair is guaranteed
  to share a fold (tested).
- **Result:** multinomial logistic regression (class-balanced): grouped-OOF
  balanced accuracy **0.530** vs baseline 0.333; macro-F1 0.504 vs 0.270;
  fold BA 0.573 ± 0.073. A model is serialised only if it beats the baseline
  in *every* fold — it does, so the model is usable but must be described as
  **moderate**.
- **Explanations:** coefficients, exact log-odds contributions, exact linear
  SHAP (verified to reconstruct the logits), permutation importance on
  held-out data. OOD warnings for out-of-range inputs, unseen categories,
  sparse combinations, and missing inputs.
- **Implemented vs planned:** implemented = training, grouped evaluation,
  explanations, OOD checks, Python inference, FastAPI service, tests. Planned
  (needs authorisation) = recalibration, richer models *if* the data grows,
  series-aware probabilistic models.

## 7. Current project status

- **Complete and frozen:** Phases 1, 2, 3, 3.5, 4A, 5 (hash-verified
  unchanged), the prediction engine (20 tests), the paper PDF (18 pages), and
  this documentation set.
- **Blocked (needs the data originators):** burning-rate definition,
  "Disruption" semantics, per-run metadata, calibration records, series
  structure, clock reconciliation (OQ-1…OQ-8).
- **Future work:** Phase 7 (if authorised) would answer the originator
  questions, then re-run the comparison with resolved definitions; physical
  modelling remains prohibited until then.

## 8. What the human developer should do next

The frontend is yours to build. The backend contract is ready:

1. `notebooks/.venv/bin/pip install -r prediction/requirements.txt`
2. `notebooks/.venv/bin/python -m uvicorn prediction.api:app --port 8000`
3. Read `deliverables/FRONTEND_INTEGRATION_GUIDE.md` for endpoints, schemas,
   example requests/responses, and how to render explanations and warnings
   honestly (never without the model's limitations).

Recommended frontend pages: a **condition → predicted outcome** explorer with
probability bars and explanation lists; a **comparison dashboard** reading the
frozen Phase 4A CSVs; a **limitations panel** that is always visible; and a
**provenance page** citing the paper and the phase history.

## 9. Reproducibility

```bash
# analysis results (Phases 4A/5 outputs regenerate deterministically)
notebooks/.venv/bin/python analysis/phase4a/run_analysis.py
notebooks/.venv/bin/python -m pytest analysis/phase4a/tests/ analysis/phase5/tests/ -q

# prediction engine
notebooks/.venv/bin/python prediction/train.py
notebooks/.venv/bin/python prediction/evaluate.py
notebooks/.venv/bin/python -m pytest prediction/tests/ -v

# research paper PDF (originals untouched; build copy in deliverables/_build/)
notebooks/.venv/bin/python deliverables/build_paper.py
```

Every pipeline gates on the raw dataset's SHA-256
(`37c88ce8…e1b96`); the test suites re-verify all 59 protected files (raw
data, schema, src, tests, Phases 1–5). Everything is local: no Git
repository, no uploads, no external contact.
