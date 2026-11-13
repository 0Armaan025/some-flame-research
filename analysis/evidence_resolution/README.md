# FLEX PSI-69 — Phase 3.5: Evidence Resolution & Experimental Recovery

Final report. Phase 3.5 investigated every outstanding evidence gap from
`analysis/validation/` with a strict evidence-based stopping rule: every
plausible local source was examined before anything was declared locally
unrecoverable. All work is confined to `analysis/evidence_resolution/`;
Phases 1–3, raw data, schema, src and tests are frozen. Integrity enforcement:
the raw dataset's SHA-256 is gated on every pipeline run, and the test suite
carries frozen SHA-256 constants for the 30 Phase-1/2 hashable files plus
content-normalised digests for the Phase 3 outputs (42 protected files
covered; `analysis/validation/run_manifest.json` is compared with its
`executed_utc` field normalised, because Phase 3's own suite regenerates that
field).

Run: `notebooks/.venv/bin/python analysis/evidence_resolution/run_resolution.py`
Tests: `notebooks/.venv/bin/python -m pytest analysis/evidence_resolution/tests/ -v`

## 1. Investigation order and coverage (reproducible)

| Stage | Scope | Artifacts inspected |
|---|---|---|
| 1 Reconnaissance | all Phase 3 deliverables + previously unexamined files | `reports/` (JAXA GC manifests — out of scope), `notebooks/` (10 scripts), `data/interim/flex/` (8 artifacts — **previously never inspected**), `data/processed/` (0-byte placeholders), `docs/jaxa/`, `docs/tnf/`, all 5 FLEX documents in full |
| 2 Critical evidence | R1, R6 | full-text searches for burning-rate/disruption/calibration terms across all documents + docx extraction; burning-rate hypothesis forensics; zero-anomaly enumeration; duplicate-timestamp cluster analysis |
| 3 Instrument/temporal | R3, R4, R7/R8 | 23-archive census + in-memory frame-header pilot; per-run clock offsets and drift; one-row chamber-log forensics; Testpont typo content check; metadata recovery |
| 4 Consolidation | R2 + registers | Disruption semantics across 6 documents; registers; corrections; readiness |
| 5 Review | independent | hash verification, claim/evidence consistency, test mutation checks |

Every quantity cited in the documents is recomputed by `run_resolution.py`
into `resolution_checks.csv` from the raw table, raw telemetry, and archive
metadata (no extraction).

## 2. Final classification of the ten known unresolved issues

| # | Issue | Classification | One-line basis |
|---|---|---|---|
| 1 | Burning-rate definition/units | **Locally unrecoverable — `UNIT UNVERIFIED — PHYSICAL INTERPRETATION BLOCKED`** | no local definition; d²-law-constant reading contradicted by the data itself (ρ≈0; −0.40 heptane); resolving publications identified (NTRS 20150023456, DOI 10.1007/s12217-014-9377-x) but not local |
| 2 | "Disruption" semantics | **Locally unrecoverable — `OUTCOME SEMANTICS UNVERIFIED`** | zero occurrences of "disrupt" in all six inspected documents |
| 3 | 0 mmHg (C11M201) | **Partially resolved** | series-coherent run with corrupted pressure cell, indicated by the C11M201/C11H201 timestamp collision; true value unknowable, not imputed |
| 4 | Eight 0 mm extinction diameters | **Partially resolved** | documented measurement-floor mechanism (Test Plan); per-record classification unknown; all Heptane; split Disruption×4/Completion×4 |
| 5 | 193F001 identity | **Partially resolved** | same identifier + same second + near-identical diameters + differing reductions ⇒ best reading "one run, two reduction passes"; either removal moves d0 contrast p 0.0623→0.0450 |
| 6 | Clock offsets (six domains) | **Blocked (quantified)** | PIP–MAIN medians 1.226–1.714 s per run with intra-run drift ≈+6.9 ms/1000 samples; no synchronization event; one-row chamber logs explained as ignition snapshots; typo file structurally normal |
| 7 | Per-run temperature/gravity/fiber | **Partially resolved** | temperature + fiber recoverable for the 8 linked runs only; gravity unrecoverable locally |
| 8 | Table version provenance | **Resolved** | PSI-69 study DOI 10.60555/mbq8-0451, released 31-Jul-2016, CIR-FCF/MDCA on ISS; dataset paper identified |
| 9 | Image archive usability | **Partially resolved** | structure/run-association/ordering established; scale absent (nominal 150 dpi only); anchor path for scale identified (79 µm SiC fiber) |
| 10 | Calibration / uncertainty | **Partially resolved** | spec-level accuracies consolidated + indirect pressure cross-check (0.06–1.24 mmHg, ≤0.164%, 8 runs); no calibration records locally |

## 2b. Requirement-ID mapping (Phase 3 → Phase 3.5)

Phase 3's readiness list and this phase's evidence register use different
numbering schemes; both are preserved and mapped explicitly:

| Phase 3 requirement | Phase 3 ID | Phase 3.5 register IDs |
|---|---|---|
| Burning-rate unit validity | R1 | R1 (ER-01…ER-04) |
| Image pixel-scale / reduction procedure | R2 | R3 (ER-15) |
| Single-run image pilot | R3 | R3 (ER-15) |
| Clock-offset map | R4 | R4 (ER-11…ER-13) |
| Per-run condition records (temp/gravity/fiber) | R5 | R7 (ER-16…ER-18) |
| Anomaly + 193F001 resolution | R6 | R5/R6 (ER-07…ER-10) |
| Series metadata for inference | R7 | R5 (ER-10) |
| Uncertainty model | R8 | R10 (ER-14) |
| Chemical-extinction evidence | R9 | R9 (blocked; radiometer/OH* archives unextracted) |
| Frozen input datasets | R10 | this phase's integrity gate |
| (not in Phase 3's list) outcome-label definitions | — | R2 (ER-06) |
| (not in Phase 3's list) pressure/composition validity | — | R4-adjacent (ER-14 cross-check) |
| (not in Phase 3's list) table provenance | — | R8 (ER-05) |

`phase4_readiness.md` evaluates Phase 3's R1–R10 (the frozen list); this
register's IDs resolve to them via the table above.

## 3. New evidence discovered this phase

1. **`data/interim/flex/`** — 8 prior-phase artifacts (20CAL13 manifests,
   ignition-aligned frames) that already flagged image-timestamp timezone as
   unverified; not previously inspected in Phases 1–3.
2. **Study DOI and 51 DOI-aligned publications** from `i_Investigation.txt`,
   including the dataset paper matching the table's exact date span.
3. **Second duplicate-timestamp cluster** (C11M201/C11H201, 9/6/2010
   19:14:22) — corroborates the C11M201 pressure-zero transcription reading.
4. **Chamber pressure cross-validation** of the table for all 8 linked runs.
5. **Clock drift quantification** (per-run offsets + ≈7 ms/1000 samples).
6. **One-row chamber logs** are ignition snapshots (Δ = −(AS fractional
   second)).
7. **TIFF/BMP geometry census** and the 150-dpi (non-physical) resolution tag.
8. **The reported rate column is not d0²/t** (forensic negative result).

## 4. Originator clarification package (prepared, NOT sent)

No email or external contact was made. Prioritised questions, each with the
evidence already inspected:

**OQ-1 (CRITICAL — R1).** What physical quantity, unit and measurement
equation define the table column `Burning rate; mm`? (Inspected: all 5 FLEX
documents, investigation record, telemetry, archives; hypothesis forensics
rule out the d²-law constant as d0²/t.) Why it matters: every rate-based
scientific claim is blocked without it. Requested: the column definition and
its derivation pipeline.

**OQ-2 — R2 (Disruption semantics).** What is the operational definition of
`Test end = Disruption`; which diagnostic assigns it; is it mutually exclusive
with Extinction/Completion; stable across 2009–2011? *Inspected:* all five FLEX
documents + investigation record, full-text — "disrupt" has zero occurrences.
*Why it matters:* 61 records (24% of the table) carry an undefined category
that Phase 2 outcome analyses must stratify rather than pool.

**OQ-3 — R6 (pressure zero).** Is C11M201's reported 0 mmHg a transcription
defect, and what was the true chamber pressure? *Inspected:* the C11 series
(siblings 531.1–536.3 mmHg), its own in-family measurements, and the duplicate
19:14:22 timestamp shared with C11H201. *Why it matters:* the record's
pressure is used (flagged) or excluded (screened) in every pressure-stratified
result; the true value cannot be imputed locally.

**OQ-4 — R6 (zero extinction diameters).** What do the eight 0 mm values mean —
non-detection placeholder, burned-to-completion convention, or another code?
*Inspected:* the eight records (all Heptane; Disruption×4/Completion×4), the
Test Plan's documented measurement floor, and all arithmetic patterns.
*Why it matters:* these eight drive the entire as-reported vs screened
difference in the heptane extinction-diameter distribution (mean ratio
0.633 vs 0.699).

**OQ-5 — R5/R7 (193F001 + series structure).** Are tests 70 and 73 one run
reduced twice or two deployments? What do the F/R identifier letters denote?
Is per-run series/campaign metadata available? *Inspected:* both records
(same identifier, same second, near-identical diameters, differing
reductions), the 193 series context, and the sensitivity of the
initial-diameter contrast (p 0.0623→0.0450). *Why it matters:* identifier-only
joins silently merge these rows, and design-based inference needs the series
structure.

**OQ-6 — R4 (clocks).** Which documented synchronization event ties PIP,
MAIN_COMPUTER, the radiometer 100 Hz frame clock, FCU, the camera clocks and
the image-reference clock, and what clock model applies per run? *Inspected:*
per-run offsets (PIP−MAIN medians 1.225–1.712 s, net drift −2.9 to +6.9 s per
1000 samples), the whole-second FCU ignition snapshots, and the GMT ±0.03 s
requirement that the files demonstrably do not meet. *Why it matters:* no
merged time-resolved product — telemetry, events or images — is defensible
without it.

**OQ-7 — R10 (calibration).** Are the PSI "FLEX – Calibration", "LCTF
Calibration" and "Radiometer Calibration" experiment data records available,
and which measurements do they calibrate? *Inspected:* every local document
(only the DoD.docx mentions them) plus the FCU PT16↔table pressure agreement
(0.06–1.24 mmHg, 8 runs) as an indirect check. *Why it matters:* absolute
accuracy of every measured quantity is currently unquantified; the Phase 4
uncertainty model needs calibration, not specification, values.

**OQ-8 — R5/R7 (per-run metadata).** Per-run chamber temperature, ISS g-level,
fiber-usage flag and gas-charge verification for the 266 runs lacking
telemetry; plus the image-analysis scale convention (mm/pixel). *Inspected:*
the 8 linked runs (temperature 23.57–26.06 °C, fiber flag No, igniter
settings) and all image headers (only nominal 150 dpi). *Why it matters:*
temperature and gravity are confounders in every cross-condition comparison,
and the pixel scale gates every image-derived measurement.

Contacts for routing: investigation record lists PI F. Williams (UCSD),
Co-Is B. Shaw (UC Davis), M. Hicks and D. Dietrich (NASA GRC), V. Nayagam
(CWRU), M. Choi (U. Missouri), F. Dryer (U. South Carolina); email addresses
are recorded in `docs/flex/i_Investigation.txt` study-contact rows.

## 5. Corrections to prior phases (documented, frozen files untouched)

`correction_register.csv`: COR-01 (Phase 1 zero-mm split ×5/×3 → ×4/×4),
COR-02/03 (Phase 3 section-number citations), COR-04 (Phase 3 telemetry
row-count ranges, now including the one-row-log explanation).

## 6. Integrity

- 42 protected files (raw data, schema, src, tests, Phases 1–3) hash-verified
  unchanged by the pipeline gate and by the test suite on every run.
- No Git repo created; nothing uploaded; no external contact.
- No archive extraction beyond in-memory header reads; no imputation; no unit
  assignment; no modelling; no composition renormalisation.

## 7. Files

| File | Contents |
|---|---|
| `README.md` | this report |
| `burning_rate_investigation.md` | R1 complete investigation + blocked status + OQ-1 |
| `outcome_semantics.md` | Disruption search results + OQ-2 |
| `anomaly_resolution.md` | 0 mmHg, 8×0 mm, d_ext>d0 forensics + OQ-3/OQ-4 |
| `identifier_reconciliation.md` | 193F001 candidates, reconciliation table, sensitivity + OQ-5 |
| `calibration_assessment.md` | calibration search, spec accuracies, PSIA cross-check, mapping + OQ-7 |
| `image_archive_pilot.md` | archive census, pilot findings, scale/feasibility verdicts |
| `clock_reconciliation.md` | six domains quantified, drift, one-row logs, typo + OQ-6 |
| `metadata_recovery.md` | metadata status per variable + OQ-8 |
| `phase4_readiness.md` | R1–R10 status, what is defensible, P4-1..P4-7 blockers |
| `evidence_resolution_register.csv` | 18 evidence rows (levels L1–L4, statuses) |
| `source_document_register.csv` | 15 sources with hashes and what each establishes |
| `correction_register.csv` | 4 corrections to prior phases |
| `resolution_checks.csv` | 23 recomputed forensic quantities |
| `run_resolution.py`, `run_manifest.json` | pipeline + manifest |
| `tests/test_resolution.py` | integrity, evidence, no-forbidden-inference tests |

## 8. Phase 4 readiness

**Not authorised; not begun.** The critical path is P4-1 + P4-6 (originator
metadata) → P4-3 (authorised single-run image pilot) → P4-4/P4-5 → P4-7.
Awaiting explicit authorisation.
