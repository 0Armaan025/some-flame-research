# FLEX PSI-69 — Phase 3: Scientific Validation & Evidence Assessment

Final validation report. Phase 3 is **read-only with respect to all existing
artifacts**: raw data, `schema/`, `src/`, `tests/`, and the frozen Phase 1
(`analysis/audit/`) and Phase 2 (`analysis/exploratory/`) outputs are
SHA-256-fingerprinted and verified unchanged by every run of the pipeline and
by the test suite (30 protected files). No Git repository was created; nothing
was uploaded anywhere.

Run: `notebooks/.venv/bin/python analysis/validation/run_validation.py`
Tests: `notebooks/.venv/bin/python -m pytest analysis/validation/tests/ -v`

## 1. Central questions and answers

**Q1 — Are measurements traceable to documented procedures and units?**
Partly. Units of the four measurement columns and all condition columns are
verified at header level, and each has a documented method class (image- or
diagnostic-derived) in the FLEX requirements documents. But **no per-run
calibration evidence exists anywhere in the audited material**, the
**burning-rate column definition is missing entirely**, and the outcome label
**"Disruption" is undefined**. See `measurement_provenance.md`.

**Q2 — Are the statistical comparisons consistent with the experimental
design?** No. The Test Plan documents an **adaptive sequential LOI procedure**
(test conditions chosen from previous outcomes); 274 records form 81 campaign
series with up to 9 runs per session date; one identifier collision merges two
records under naive joins. Phase 2's p-values are arithmetically correct but
**conditional on an independence assumption the design does not support**.
See `experimental_independence.md`.

**Q3 — Are conditions sufficiently comparable?** Only in restricted cells.
Fuels share 31/52 mixture families; of the ten matched-O2 CO2/He cells only
**4 are fully comparable** (identical N2 balances, shared pressure bands,
n≥3 per side). Pressure effects are unidentifiable above 800 mmHg (all 9
records in one CO2 family). See `condition_comparability.md`.

**Q4 — What additional evidence is required before modelling?** A
unit-verified burning-rate definition, clock reconciliation across six
telemetry clock domains, a validated image-archive pilot, per-run condition
records (temperature, gravity, fiber), and resolution of the flagged
anomalies. See §6 below.

## 2. Methods

1. **Reconnaissance** of every local document (5 FLEX documents, 1
   investigation file, schema, raw data, 8-run telemetry, 23 archive
   listings) with full-text searches for measurement definitions.
2. **Independent recomputation**: `run_validation.py` carries its own
   byte-preserving loader (no Phase 2 imports) and re-derives every structural
   quantity cited in these documents into `validation_checks.csv`; the
   duplicate-sensitivity p-values and all ten diluent cells were re-derived
   from raw data and agree with the Phase 2 outputs.
3. **Evidence register**: every scientific claim is classified
   VERIFIED / DOCUMENTED_BUT_UNCONFIRMED / INFERRED / UNVERIFIED / CONTRADICTED
   / BLOCKED with source document, location, confidence, limitations and
   required follow-up. No reference or page number was fabricated; every cited
   file exists on disk (asserted by the test suite).
4. **Integrity gate**: the pipeline refuses to run if any protected file hash
   changes; tests independently re-verify all 30 hashes before and after a
   pipeline run.

## 3. Conclusions by evidential class

### Scientifically established
- The dataset contains 274 records (157 Methanol / 117 Heptane), 196 with all
  four core measurements; missingness and flags as reported in Phase 1 (77
  missing extinction diameters, 34 `0x96` artifacts, 2 approximate burn times,
  1 zero-pressure record, 8 zero-mm extinction diameters, 1 identifier
  collision, 29 non-unity composition sums) — all preserved, never imputed,
  never renormalised.
- Outcome-label composition differs by fuel (Extinction 80.3% vs 51.3%;
  Fisher p = 5.16e-07 raw, 1.55e-06 Holm-adjusted) — the **arithmetic is
  VERIFIED** (EV-026) and is a property of the **recorded labels only**;
  interpreting it as a fuel effect is exploratory (labels are
  design-generated and "Disruption" is undefined).
- Measured burn durations differ by fuel (medians 12.1 s vs 7.5 s; MWU
  U = 4838, p = 1.17e-09) — the **statistic is VERIFIED** (EV-027); the
  *inference* is conditional on independence and on the undocumented
  start/stop definition, so comparative claims are exploratory (matrix
  row 8).
- Pressure and diluent are confounded above 800 mmHg (9/9 records in one
  family); no independent pressure effect exists in that region.
- Only 4 of 10 matched-O2 CO2/He cells are fully comparable.
- Telemetry exists for 8/274 runs across at least six unreconciled clock
  domains; 23 image archives (TIFF/BMP, 800–1290 frames) are listed but not
  extracted.
- The initial-diameter fuel contrast is duplicate-sensitive: p 0.0623 →
  0.0449 when either 193F001 record is removed.

### Supported but conditional
- Initial diameter, extinction diameter, burn time, pressure and composition
  as measured quantities (documented method class; spec-level tolerances;
  no per-run calibration).
- Fuel comparisons **within shared mixture families** (115 MeOH / 106 Hep
  records) as descriptive associations.
- Diluent contrasts **within the 4 fully comparable cells only**, reported
  per cell.
- Extinction/Completion outcome labels as procedural categories (Test Plan
  §5.3 context).

### Exploratory
- Burning-rate scalar differences by fuel (medians 0.460 vs 0.540) —
  provisional because the unit is unresolved.
- Rank associations involving the burning-rate scalar (e.g. ρ = 0.038 with
  burn time, n = 257) — descriptive only; their p-values use a **normal-tail
  approximation through `erfc`, not an exact Student-t distribution**, and
  inherit the independence caveat.
- Diameter/outcome stratifications in `diameter_analysis.csv`.

### Unverified
- **Burning-rate unit and definition** — `UNIT UNVERIFIED — PHYSICAL
  INTERPRETATION BLOCKED` in every phase.
- **"Disruption" outcome label** — no definition in any inspected document.
- Table provenance beyond "PSI data system" (no DOI/version/export date).
- Interpretation of the 8 zero-mm extinction diameters and the 0 mmHg record.

### Blocked
- Any pressure-effect claim above 800 mmHg.
- Any d²-law constant, evaporation constant, regression rate or physically
  interpreted burning-rate quantity.
- Chemical-extinction claims (visible flame extinction ≠ chemical extinction;
  no radical/species measurements).
- Temperature- or gravity-effect claims (no per-run data).
- Merged telemetry timelines (six unreconciled clock domains).
- Image-derived measurements (archives not extracted/validated).
- Design-based confirmatory inference (adaptive series design; independence
  not established).

## 4. Confounding factors (consolidated)

Pressure ↔ diluent above 800 mmHg; fuel ↔ condition family (15 MeOH-only, 6
Hep-only families); unrecorded temperature (affects all rate/duration
comparisons); unrecorded gravity and fiber usage; adaptive condition
selection (design-generated outcome distribution); session/series clustering
(81 series, ≤9 runs/date); identifier collision 193F001; burning-rate unit
ambiguity propagates into every rate-related comparison.

## 5. Unresolved questions

1. Burning-rate column definition and unit (blocks all physical rate
   quantities).
2. Operational definitions of Extinction / Disruption / Completion.
3. Nature of the 8 zero-mm extinction diameters and the 0 mmHg record.
4. Identity behind the 193F001 collision.
5. Clock-offset map across the six telemetry domains.
6. Per-run temperature, gravity, fiber usage, fuel lot, gas-charge
   verification — all absent for 266+ records.
7. Provenance version of the PSI-69 table export.

## 6. Requirements for Phase 4 — Physical Modelling

Physical modelling (d²-law fitting, constants, extinction limits) must not
begin until **all** of the following exist and are validated:

| # | Requirement | Why | Current status |
|---|---|---|---|
| R1 | Documented definition + unit of the burning-rate column (PSI data dictionary or originator code) | without it, no physically interpreted rate quantity exists | **BLOCKED** |
| R2 | Validated pixel-scale and reduction procedure for image-derived diameters, plus the per-run analyzed diameter time series | d²-law needs D(t), not a single scalar | archives present but unextracted |
| R3 | Pilot extraction of one run's images with frame-count/timestamp verification against the manifests | establishes archive usability before bulk work | pilot defined, not executed |
| R4 | Clock-offset map across PIP / MAIN_COMPUTER / radiometer / FCU / camera / image-reference domains, validated to the ±0.03 s GMT requirement | any time-resolved fit requires a single timeline | **BLOCKED** |
| R5 | Per-run condition records: temperature, g-level, fiber usage, gas-charge verification | model inputs and confound control | absent for 266/274 runs |
| R6 | Resolution of flagged anomalies (0 mmHg, 8× 0 mm, d_ext>d0) and the 193F001 collision | prevents silent bias in fitted datasets | open with originator |
| R7 | Series/run structure metadata enabling series-respecting inference (permutation within series, or stratified fits) | the adaptive design invalidates exchangeability | inference rule defined, metadata needed |
| R8 | Uncertainty model per R1–R6 (spec-level values documented in `uncertainty_assessment.md` §3) | fitted parameters need uncertainty | spec-level only |
| R9 | If extinction limits are modelled: radical/species evidence (OH*/LLLUV extraction validated against the visible-flame label) | visible flame extinction ≠ chemical extinction | **BLOCKED** |
| R10 | Frozen input datasets with recorded hashes and a rerun-validated pipeline (as in Phases 2–3) | reproducibility of fitted results | pattern established |

Recommended order: R1 + R6 (originator metadata request) → R3/R4 (single-run
pilot + clock map) → R2/R5 → R7/R8 → only then R9/R10 and modelling.

## 7. Files created by Phase 3

| File | Contents |
|---|---|
| `README.md` | this report |
| `measurement_provenance.md` | per-variable provenance, 4-level evidence hierarchy, burning-rate block |
| `experimental_independence.md` | identity structure, adaptive design, statistical assessment, viable alternatives |
| `condition_comparability.md` | fuel overlap tiers, 10-cell diluent audit, pressure confounding |
| `telemetry_assessment.md` | linkage, six clock domains, sampling, archive structure, feasibility |
| `uncertainty_assessment.md` | uncertainty register by category, flagged-extreme handling, Phase 4 propagation stance |
| `evidence_register.csv` | 29 traceable evidence rows with classifications |
| `validation_matrix.csv` | 15 research questions vs required/available evidence, status, blocker, action |
| `validation_checks.csv` | every structural quantity cited above, independently recomputed |
| `run_validation.py`, `run_manifest.json` | pipeline + execution manifest (hashes, versions, integrity, limitations) |
| `tests/test_validation.py` | preservation, evidence integrity, no-unit-assignment, no-modelling and recomputation-agreement tests |
| `references/` | reserved for extracted citations in later phases (intentionally empty) |

## 8. Defects discovered in frozen phases (documented, not modified)

Phase 1 and Phase 2 are frozen; defects found during Phase 3 are recorded
here rather than corrected in place.

| # | Phase / file | Defect | Correct value | Effect |
|---|---|---|---|---|
| D1 | Phase 1 `analysis/audit/data_quality_report.md` §3 | states the eight 0-mm extinction diameters split as "Disruption×5, Completion×3" | **Disruption×4 (224F001, 223F002, 210F002, 149F001), Completion×4 (209F005, 301F002, 193R002, C21H501)** — verified by independent recomputation | none on any analysis (Phase 2 flagged records, not the split); the Phase 3 uncertainty register carries the corrected split |
Operational note: the Phase 3 test suite regenerates `validation_checks.csv`,
`evidence_register.csv` and `validation_matrix.csv` on each run, so tampering
with those *output* files is self-healing by design; tampering with the
pipeline **source** (`run_validation.py`), with protected files, or with
assertive claims in the documents is caught (verified by mutation testing
during the Phase 3 review). Output integrity is therefore guaranteed by
regeneration + independent recomputation of values, not by output hashes
alone (the manifest's output hashes record the current generation).

## 9. Reproducibility

```bash
notebooks/.venv/bin/python analysis/validation/run_validation.py
notebooks/.venv/bin/python -m pytest analysis/validation/tests/ -v
```

All paths are anchored to the script location (the raw-table lookup globs from
the repository root derived from `__file__`, never the CWD). The manifest
records input hashes, the documents inspected, recomputed quantities, output
hashes, environment versions and the integrity result. The test suite fails on
any change to a protected file, any fabricated or untraceable citation, any
assertive unit assignment for the burning rate, any imputation/renormalisation
claim, and any modelling code in the pipeline.
