# FLEX PSI-69 Data Quality Report (Phase 1 audit)

Scope: `data/raw/flex/PSI-69_Experimental table_FLEX.csv` (274 records) and the
`data/raw/flex/part-01/` per-run files. Read-only audit; raw data untouched.
All numbers below are reproducible via `analysis/audit/audit_flex_psi69.py`.

Counts are reported per variable in `missing_data_report.csv`; this document
records the *qualitative* findings and the rules proposed for handling them.

## 1. Summary counts

| Metric | Value |
|---|---|
| Total records | 274 (Methanol 157, Heptane 117) |
| Records with all four core measurements (initial diameter, extinction diameter, burning rate, burn time) | 196 (116 MeOH, 80 Heptane) |
| Records with 1–3 of four core measurements | 74 |
| Records with none of the four | 4 (all Heptane) |
| Records with any missing value in the 15 columns | 78 (Methanol 41, Heptane 37; see missing_data_report.csv) |
| Test dates span | 2009-03-05 to 2011-12-08 |

## 2. Encoding and missing-value markers

- The file is Windows-1252 (extended ASCII), not UTF-8. Reading it as UTF-8
  fails; the audit read it byte-preserving.
- **34 fields carry the byte `0x96`** (Windows-1252 en-dash), a spreadsheet
  artifact used as a *blank marker* in the diameter, extinction-diameter and
  burning-rate columns. It is not a number and not a measured zero. The audit
  treats it as "not reported".
- Missing values also appear as empty fields. In both cases nothing was
  imputed, interpolated, or carried forward.
- Two burn-time values (`~6` s, `~9` s; H01M104, H01H102) carry a tilde
  approximation marker. They are **kept as reported values with an
  approximate flag** (matching the `*_approx` fields in `schema/v1.2.0.sql`),
  not dropped and not re-rounded.

## 3. Physically implausible values (flagged, not corrected)

| Finding | Records | Proposed handling rule |
|---|---|---|
| Ambient pressure reported as `0` mmHg | 1 (`C11M201`, Methanol, 2010-09-06) | Exclude from pressure analysis; keep the record for all other variables; source correction needed |
| Extinction diameter reported as exactly `0` mm | 8 (all Heptane: 224F001, 223F002, 209F005, 210F002, 301F002, 193R002, 149F001, C21H501; outcomes Disruption×5, Completion×3) | Treat as not-measured placeholder pending source confirmation; a true 0 mm visible-flame diameter is not a physical flame-extinction measurement |
| Extinction diameter > initial diameter | 1 (`C13H102`, Heptane, 3.33 → 3.34 mm) | Likely measurement noise near equality; flag for sensitivity analysis |
| Ambient composition does not sum to 1.000 | 22 records sum to 0.990, 6 to 0.980, 1 to 1.010 (245 sum exactly to 1.000) | Do not renormalise silently; treat as `composition_completeness = 'partial'` per schema contract and report the reported sum |

## 4. Consistency between outcome labels and measurements

| Category | Count | Comment |
|---|---|---|
| Outcome "Extinction" **with** recorded extinction diameter | 159 | usable for d_ext analyses |
| Outcome "Extinction" **without** recorded extinction diameter | 27 | the label exists but the measurement does not — never imputed |
| Outcome "Disruption" with extinction diameter recorded | 24 | value present but labelled disruption |
| Outcome "Completion" with extinction diameter recorded | 14 | value present but labelled completion |

The `Test end` label and `Visible flame extinction diameter` are **distinct
fields**: a record may carry the label without the measurement. Definitions of
Disruption vs Completion vs Extinction per the FLEX test plan should be
recorded in metadata before using `Test end` as a modelling target (the
existing `src/prediction/predictor.py` uses these labels as a classification
target without recording the definition).

## 5. Duplicates

- **0 exact duplicate rows**, 0 duplicate `FLEX Test #` values.
- **1 duplicated `FLEX Identifier`**: `193F001` appears twice (tests 70 and 73,
  both Heptane, 2010-03-23 07:25:43, 761 mmHg, O2=0.15/N2=0.84) with slightly
  different measurements (d0 4.67 vs 4.64 mm; burn rate 0.41 vs 0.56 mm*). Two
  physically distinct runs share one identifier — an identifier collision, not
  a duplicated record. Downstream joins keyed on `FLEX Identifier` alone would
  silently merge or pick one arbitrarily; key on (`FLEX Test #`) or on the pair.
- 0 repeated full condition+measurement signatures, so no systematic
  double-entry was found beyond the identifier collision.

## 6. Provenance and integrity checks performed

- Byte-level scan of the CSV (encoding, CRLF, marker bytes).
- Per-variable missingness split by marker type (empty vs `0x96`).
- Filename-level linkage of the 274 identifiers against `data/raw/flex/` and
  `part-01/`.
- No values altered; no units converted; no derived quantities introduced.

## 7. Confounding variables and structural limitations

1. **Pressure is confounded with diluent composition at high pressure.**
   All 9 records above 800 mmHg occur only in the O2=0.21/N2=0.09/CO2=0.70
   family; no high-pressure He-diluted or air-baseline run exists. "Effect of
   pressure" and "effect of CO2 dilution at fixed pressure" cannot be
   separated with this table.
2. **Ambient temperature is never reported** anywhere (experimental table or
   telemetry headers show velocity/position channels only). Burning rate
   depends on gas temperature and vapour pressure; cross-condition comparisons
   carry an unquantified temperature confound.
3. **Gravity regime is not a field in the table.** FLEX flew on the ISS and
   documentation describes microgravity droplet tests, but per-run gravity
   metadata is absent, so any gravity claim must be sourced from the test
   documents and stated with its provenance, not inferred from the CSV.
4. **Fuel purity/specification is unreported** for both fuels (methanol and
   "Heptane" with no isomer confirmation in the table).
5. **Burning rate is a single scalar per run** with questionable units
   (header reads `Burning rate; mm`). It must not be read as combustion
   efficiency, and no d²-law constant can be derived without the underlying
   diameter-time trajectory.
6. **Extinction diameter is the visible flame extinction diameter.** Visible
   flame-out is not, by itself, evidence of complete chemical extinction
   (residual radical chemistry can persist); no OH*/CH* emission or
   gas-sampling measurement exists in the available files to support that
   distinction.
7. **Cell sizes are small and unbalanced.** After the missingness in §1–3,
   most O2 × diluent × fuel cells contain only 1–5 records (see
   `condition_coverage.csv`; e.g. the 800–2100 mmHg band has 5 MeOH + 1 Heptane
   records in a single mixture). Fuel-comparison tests on sparse cells will be
   underpowered and sensitive to the flagged records.
8. **Telemetry linkage covers only 8/274 runs**, all in one condition family
   (2009, ~760 mmHg, ambient air), so time-resolved analysis inherits that
   selection bias.
9. **Three clock domains** exist across per-run files (AS/PIP event clock,
   FCU chamber clock, PIP radiometer clock); offsets are non-trivial per the
   `notebooks/audit_flex_*` work, so timestamps cannot be merged naively.
10. **Mixed date formats** (`M/D/YYYY` and `M/D/YY`) and one missing `Test GMT`
    (30CAL07) require explicit parsing rules; the audit parses both formats
    without reformatting the stored originals.

## 8. Recommendation — investigable vs. blocked questions

**Investigable with the available data (with stated caveats):**

| Question | Basis | Caveat |
|---|---|---|
| How does initial droplet diameter vary with test outcome (Extinction/Disruption/Completion) per fuel? | d0 present for 262/274 | Describe, don't infer mechanism |
| Is reported burning rate systematically different between methanol and n-heptane within the same nominal condition family? | 151 MeOH / 107 Heptane rates | Unit ambiguity (DQ-3); temperature unreported |
| How does burn duration vary with initial diameter and O2 mole fraction, per fuel? | 268 times, O2 274/274 | Observational only; small cells |
| What is the distribution of visible-flame extinction diameter relative to initial diameter, per fuel and outcome? | 197 d_ext values | "Visible flame" only; 8 flagged zeros excluded per §3 |
| Which condition families (O2 × diluent × pressure band) exist, and where are the coverage gaps? | 274 records | See `condition_coverage.csv` |
| Can per-run telemetry be linked to experimental-table records at all? | 8 identifiers | Requires clock-sync work |

**Blocked pending additional measurements or metadata:**

| Question | What is missing |
|---|---|
| Effect of pressure at fixed diluent composition | No high-pressure non-CO2 runs (DQ-7.1) |
| Temperature/pressure dependence of burning rate | Ambient temperature never reported |
| Chemical extinction vs visible flame extinction | No radical/emission/gas-phase composition measurements |
| Combustion efficiency, heat of combustion, soot yield | No calorimetric or soot-sampler data in available files |
| d²-law burning-rate constant or instantaneous regression rate | Only a single per-run scalar exists; no diameter-time trajectory |
| Gravity-level effects | No per-run gravity metadata in the table (document-sourced only) |
| Any time-resolved flame behaviour (flicker, radiation, oscillation) | Image/FCI archives (5.4 GB zips) unextracted and clock domains unreconciled |
| Diluent-specific suppression at matched pressure beyond the 8-run telemetry set | Telemetry only for 8 ambient-air runs |

**Immediate next steps before any modelling:** (1) obtain the FLEX test-plan
definition of `Test end` categories and the burning-rate unit; (2) confirm the
`0` mmHg and `0` mm entries with the data originator; (3) resolve the 193F001
identifier collision upstream; (4) extract and reconcile the 5.4 GB image
archives with a documented clock-domain mapping before using them.
