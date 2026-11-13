# Phase 4 Readiness (Phase 3.5)

Evaluation of the original R1–R10 requirements from the Phase 3 report after
the Phase 3.5 forensic investigation. Physical modelling remains prohibited
in this phase; this document only states what would become defensible.

| Req | Requirement | Status after Phase 3.5 | What changed since Phase 3 | Still blocking |
|---|---|---|---|---|
| R1 | Burning-rate definition + unit | **UNRESOLVED** | d²-law-constant hypothesis definitively contradicted by the data (ρ≈0, −0.40 heptane); the four resolving publications identified with DOIs/NTRS | column definition still unavailable; publications not local |
| R2 | Outcome-label definitions | **UNRESOLVED (Disruption) / DOCUMENTED_UNCONFIRMED (Extinction, Completion)** | exhaustive search of 6 local documents; LOI procedure text mapped to Completion/Extinction | Disruption definition absent everywhere |
| R3 | Image archive usability | **PARTIALLY RESOLVED** | full structure established (formats, dimensions, counts, gaps, manifests, run association, sequence ordering); scale calibration shown absent; anchor path identified (79 µm SiC fiber) | mm/pixel scale; timezone of image manifests |
| R4 | Clock synchronization | **BLOCKED** | offsets quantified per run + intra-run drift rate; 3 one-row chamber logs explained; typo file explained | no documented synchronization event; no validated per-run clock model |
| R5 | Pressure measurement validity | **SUPPORTED_BUT_CONDITIONAL (upgraded)** | new indirect corroboration: FCU PT16 vs table within 0.06–1.24 mmHg (≤0.164%) for 8 runs | true transducer calibration records |
| R6 | Composition measurement validity | unchanged | — | charge verification logs; 29 non-unity reported sums |
| R7 | Independence | **BLOCKED (design-based inference)** | quantified what the collision does (p 0.0623→0.0450); second duplicate-timestamp cluster found (C11M201/C11H201) | series metadata; resolution of both clusters |
| R8 | Temperature / gravity / fiber metadata | **PARTIALLY RESOLVED (temp, fiber for 8 runs)** | temperature and fiber recovered for the 8 linked runs from telemetry | 266-run coverage; per-run gravity unrecoverable locally |
| R9 | Chemical extinction identifiability | **BLOCKED** | unchanged | OH*/species measurements not extracted or validated |
| R10 | Uncertainty model | **PARTIALLY RESOLVED** | spec-level accuracies consolidated; one indirect pressure cross-check; zero/d_ext>d0 anomalies characterised | calibration records; per-run conditions |

## 1. What is now defensible (post Phase 3.5)

1. **Descriptive statistics and stratifications** of the table exactly as in
   Phase 2 (verified data, disclosed flags, effective n everywhere).
2. **The pressure column as absolute chamber pressure in mmHg**, with an
   explicit statement that 8/274 records are cross-checked against chamber
   telemetry within ≤0.15% and none is independently calibrated.
3. **Condition-coverage and comparability analysis** (shared families, the
   four fully matched CO2/He cells).
4. **Forensic statements** about what the dataset is not (d²-law constant
   column; independent-observation inference; synchronised timelines).
5. **A single-run image pilot** (D-series extraction, fiber-width scale
   derivation, closed-loop diameter validation against the table) — this is
   the only time-resolved work that does not require clock reconciliation,
   because frame *ordering* (not absolute time) suffices for a diameter-time
   curve.

## 2. What remains prohibited (explicit)

- Fitting d²-law models or computing any evaporation/burning constant.
- Estimating chemical extinction from visible-flame labels.
- Time-resolved analysis on merged telemetry timelines.
- Predictive machine-learning models.
- Any physically interpreted burning-rate quantity.

## 3. Exact requirements still preventing Phase 4

| # | Requirement | Blocking req | Resolution path |
|---|---|---|---|
| P4-1 | Burning-rate column definition (physical quantity, unit, equation, uncertainty) | R1 | originator (OQ-1) or NTRS 20150023456 / DOI 10.1007/s12217-014-9377-x |
| P4-2 | Disruption outcome definition | R2 | originator (OQ-2) |
| P4-3 | Image pixel scale + image-timestamp timezone | R3/R4 | fiber-width derivation (pilot, authorized) + clock model (OQ-6) |
| P4-4 | Per-run condition metadata (temperature, gravity, fiber) | R7/R8 | originator (OQ-8) |
| P4-5 | Calibration records for diameter, rate, radiometer | R10 | originator / PSI calibration experiment records (OQ-7) |
| P4-6 | Resolution of 193F001 and C11M201/C11H201 clusters | R6/R7 | originator (OQ-3, OQ-5) |
| P4-7 | Series structure metadata for design-respecting inference | R7 | originator (OQ-5) or documented identifier-convention key |

**Critical path:** P4-1 + P4-6 (originator metadata request) → P4-3 (authorized
single-run image pilot) → P4-4/P4-5 → P4-7 → then, and only then, modelling.
