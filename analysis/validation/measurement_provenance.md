# FLEX PSI-69 — Measurement Provenance (Phase 3, P3-A)

Question answered: *Are the measurements traceable to sufficiently documented
measurement procedures and units?*

Documents inspected (full list in `run_manifest.json`): `docs/flex/FLEX_EIRD_v4.pdf`
(Research Requirements Document, Williams et al. line of documents, 82 PDF pages),
`docs/flex/FLEX_Test_Plan.pdf`, `docs/flex/FLEX Engineering Requirements Document.pdf`
(FLEX-2, FLX-REQ-0001), `docs/flex/FLEX DoD.docx`, `docs/flex/FLEX Overall Ext File-2.pdf`,
`docs/flex/i_Investigation.txt`, `schema/v1.2.0.sql`, and the raw data under
`data/raw/flex/` (experimental table, 8-run telemetry, 23 archive listings).

Evidence hierarchy used below (never promoting an inference into a fact):

| Level | Meaning |
|---|---|
| L1 | Directly documented measurement definition (source states what the quantity is and how it is obtained) |
| L2 | Definition confirmed by instrument/diagnostic documentation |
| L3 | Definition inferred from secondary documentation (context, requirements, related quantities) |
| L4 | Unverified assumption |

## 1. Variable-by-variable provenance

### 1.1 Droplet initial diameter (`Droplet initial diameter; mm`)

- **Column/unit:** header states mm — unit verified at header level.
- **Physical quantity:** initial diameter of the deployed droplet.
- **Measurement method:** L2 — dispensed and sized by back-lit droplet imaging
  (EIRD §5.2.1: back-lit view, ≥30 fps, 30 µm resolution over the FOV,
  "droplet size as a function of time … necessary to obtain droplet burning
  rates and extinction droplet diameters"). The dispenser spec (EIRD §5.1.2
  for the 2–6 mm range; FLEX-2 ERD §4.1.12–4.1.13 for the ±0.25 mm tolerance and
  ±5% reproducibility of the 1.5–5 mm FLEX-2 range:
  reproducibility ±5%) indicates the *nominal* size; the table value is
  presumably the measured/reduced value, but the reduction procedure for the
  single reported number is not documented.
- **Instrument/system:** droplet deployment needles + back-lit camera
  (IPSU camera series in telemetry).
- **Calibration reference:** none found in audited files.
- **Resolution:** 30 µm imaging requirement (EIRD §5.2.1).
- **Uncertainty:** spec-level only — ±0.25 mm dispense tolerance, ±5%
  reproducibility (requirements, not per-run measurements).
- **Approximation/rounding:** not documented; values reported to 0.01 mm.
- **Known limitations:** 12 records missing; one `d_ext > d0` flag (C13H102).
- **Status: DOCUMENTED_BUT_UNCONFIRMED (L2 for method, L4 for per-run
  reduction).**

### 1.2 Visible flame extinction diameter (`Visible flame extinction diameter; mm`)

- **Column/unit:** header states mm — unit verified at header level.
- **Physical quantity:** diameter at which the *visible flame* goes out,
  **not** a chemical extinction measurement.
- **Measurement method:** L2 — image-derived per EIRD §5.2.1 (same back-lit
  droplet sizing stream).
- **Instrument/system:** back-lit droplet camera.
- **Calibration reference:** none found.
- **Resolution:** 30 µm imaging requirement.
- **Uncertainty:** not documented for the table value.
- **Approximation/rounding:** not documented.
- **Known limitations:** 77 missing (28.1%); 8 Heptane records report exactly
  `0` mm (physically implausible as a flame-extinction diameter; retained and
  flagged; interpretation unresolved).
- **Status: DOCUMENTED_BUT_UNCONFIRMED (L2 for method). The label explicitly
  reads "visible flame"; no radical/emission measurement supports equating it
  with chemical extinction.**

### 1.3 Burning rate (`Burning rate; mm`) — **UNIT UNVERIFIED — PHYSICAL INTERPRETATION BLOCKED**

- **Column/unit:** the source header literally reads `Burning rate; mm`. A
  length unit alone is not a rate unit. No inspected document defines this
  column. Full-text searches for "burning rate", "burn rate", "mm/s",
  "mm²/s", "mm2/s", "regression rate" across all inspected PDFs/docx/txt
  found no definition of the table column.
- **What IS documented (adjacent evidence, L3):**
  - EIRD §5.2.1 states that droplet burning rates are obtained from back-lit
    droplet-size-versus-time imaging — i.e., the experiment's burning-rate
    quantity is image-derived.
  - EIRD §9 (p. 64) discusses the d²-law average burning rate constant in
    mm²/s ("assuming an average burning rate constant of 0.8 mm²/s") for
    n-heptane and methanol in air at 1 atm.
- **Why this does NOT verify the column:** those documents describe the
  *experiment's* burning-rate constant in a requirements/literature context.
  They do not state that the PSI-69 table column is that constant, nor its
  unit, nor its reduction (linear fit of D² vs t? average? regression rate?).
  Inferring mm²/s from the numeric range (0.05–1.06) is prohibited by the
  project's integrity rules and was not done in any phase.
- **Consequences enforced so far:** Phase 2 treats the column as a unitless
  recorded scalar: no unit is assigned, no d²-law or evaporation constant is
  computed, physically interpreted conclusions are marked provisional, and
  dimensionless rank associations (Spearman) are used where associations are
  reported at all.
- **Required to unblock:** the PSI-69 data dictionary, or the originator's
  reduction code/definition for this column.
- **Status: UNVERIFIED (L4). `UNIT UNVERIFIED — PHYSICAL INTERPRETATION
  BLOCKED`.**

### 1.4 Burn duration (`Burn time; s`)

- **Column/unit:** header states s — unit verified at header level.
- **Physical quantity:** per-test burn duration.
- **Measurement method:** L3 — per-test scalar; the telemetry `AS` event
  stream (igniter on/off, dispense, burn-to-completion timer) shows the
  experiment records these events with sub-second timestamps, but the exact
  start/stop pair used for the table value is not documented.
- **Instrument/system:** automated sequence (AS) event log; test-point setting
  `TP_PARAMETER_BURN_TO_COMPLETION_TIME` (20–120 s across linked runs).
- **Calibration reference:** none needed for a duration; clock accuracy
  documented as GMT ±0.03 s (EIRD §5.2.9 / ERD §4.1.98, Synchronization of
  Measurements).
- **Resolution:** not documented for the table value.
- **Uncertainty:** not documented; two values carry a `~` approximation
  marker (6 s, 9 s) preserved as approximate everywhere.
- **Known limitations:** 6 missing; approximate flags on 2.
- **Status: DOCUMENTED_BUT_UNCONFIRMED (L1 for unit, L3 for start/stop).**

### 1.5 Ambient pressure (`Ambient pressure; mmHg`)

- **Column/unit:** mmHg — verified by header. Cross-check: 757.7 mmHg ≈ 1 atm,
  consistent with the ERD 0.5–3 atm operating range and the chamber-readings
  PSIA telemetry (~14.7 PSIA) for the linked runs.
- **Measurement method:** L2 — chamber pressure measurement is a documented
  diagnostic (EIRD §5.2.8, "Ambient Pressure and Temperature Measurement").
- **Instrument/system:** chamber pressure transducers (FCU PT channels in
  telemetry).
- **Calibration reference:** none found (requirements only).
- **Resolution/uncertainty (spec level):** EIRD §5.2.8 accuracy ±0.01 atm over
  0.5–3 atm; ERD §4.1.34 range 0.5–3 atm ±0.05 atm; ERD §4.1.35 maintained
  within ±10% of initial during a test.
- **Known limitations:** one record reports 0 mmHg (C11M201) — retained,
  flagged, excluded only in screened variants.
- **Status: DOCUMENTED_BUT_UNCONFIRMED (L2 method; spec-level uncertainty;
  unit verified).**

### 1.6 Gas composition (O2/N2/CO2/He mole fractions)

- **Column/unit:** mole fraction — verified by headers.
- **Physical quantity:** initial (pre-ignition) chamber composition.
- **Measurement method:** L2 — chamber atmosphere preparation is a documented
  function (ERD §4.1.41–4.1.42 test sets; chamber purity requirements EIRD
  §5.1.x; "well-mixed chamber gases before ignition" ERD §4.1.38).
- **Instrument/system:** chamber gas supply/charge system; verification
  analyzer not identified in audited files.
- **Calibration reference:** none found.
- **Uncertainty (spec level):** ERD §4.1.36 O2 initial-charge tolerance
  ±0.005 mole fraction over 0.1–0.4.
- **Known limitations:** 29 records' reported components sum to 0.98–1.01
  rather than exactly 1.000 — **never renormalised**; reported verbatim.
- **Status: DOCUMENTED_BUT_UNCONFIRMED.**

### 1.7 Experimental outcome (`Test end`: Extinction / Disruption / Completion)

- **Physical quantity:** recorded end-of-test category.
- **Measurement method:** L3 for Extinction/Completion — the Test Plan §5.3
  LOI procedure documents "burn to completion" versus "extinguishing at a
  finite droplet size" versus no-ignition tests, which maps procedurally onto
  the Completion/Extinction labels.
- **Known limitations:** the label **"Disruption" (61 records) is not defined
  in any inspected document**; no operational definition for any of the three
  labels appears in the PSI table documentation available locally.
- **Status: DISRUPTION UNVERIFIED; Extinction/Completion CONDITIONAL.**
  Under no circumstances is the Extinction label treated as chemical
  extinction.

### 1.8 The experimental table itself

- Provenance: NASA PSI data system (psi.nasa.gov) per
  `docs/flex/i_Investigation.txt`; the file carries no DOI, version, or
  export date. sha256 `37c88ce8…e1b96` frozen in all three phases.
- **Status: DOCUMENTED_BUT_UNCONFIRMED (source system identified; version
  not recorded).**

## 2. Summary table

| Variable | Unit verified | Method level | Calibration | Status |
|---|---|---|---|---|
| Initial diameter | mm (header) | L2 image-derived | none found | DOCUMENTED_BUT_UNCONFIRMED |
| Extinction diameter (visible flame) | mm (header) | L2 image-derived | none found | DOCUMENTED_BUT_UNCONFIRMED |
| Burning rate | **NO** | L3 (adjacent evidence only) | none found | **UNVERIFIED — PHYSICAL INTERPRETATION BLOCKED** |
| Burn time | s (header) | L3 event-derived | clock spec only | DOCUMENTED_BUT_UNCONFIRMED |
| Pressure | mmHg (header) | L2 diagnostic | none found | DOCUMENTED_BUT_UNCONFIRMED |
| Composition | mole fraction (header) | L2 charge system | none found | DOCUMENTED_BUT_UNCONFIRMED |
| Outcome labels | n/a | L3 procedure context | n/a | Disruption UNVERIFIED; others CONDITIONAL |

**Overall P3-A verdict:** the units of the four measurement columns and all
condition columns are verified at header level, and every quantity has a
plausible documented method class (image- or diagnostic-derived). What is
**absent throughout** is per-run calibration evidence, the burning-rate column
definition, and the Disruption label definition. No calibration certificate,
analyzer log, or reduction code was found in any audited location.
