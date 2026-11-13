# Calibration Assessment (Phase 3.5, R10)

**Status: calibration records are locally absent; only spec-level accuracies
and one indirect consistency check exist — ORIGINATOR_CONFIRMATION_REQUIRED
(OQ-7). No calibration correction was applied; no corrected derivative was
created.**

## 1. What was searched

Full-text search for `calibrat*` across all local documents (EIRD v4, Test
Plan, FLEX-2 ERD, Overall Ext File-2, DoD.docx, i_Investigation.txt) and all
raw/interim/processed data files. Result: **no calibration certificate,
transducer calibration record, analyzer log, scale-factor file, or correction
table exists in any inspected location.**

The only calibration-related local evidence:

1. `i_Investigation.txt` documents that the PSI data system hosts five FLEX
   experiment data records including **"FLEX – Calibration", "FLEX – LCTF
   Calibration", "FLEX – Radiometer Calibration"** — i.e. calibration data
   records exist upstream in PSI but are **not part of the local dataset**
   (our table covers the HEP and MeOH records only).
2. Requirement-level accuracies in the FLEX-2 ERD and EIRD (see §2).
3. An indirect cross-check against delivered chamber telemetry (§3).

## 2. Spec-level accuracies (L1 requirements, NOT verification records)

| Quantity | Documented accuracy | Source |
|---|---|---|
| Chamber pressure | ±0.01 atm over 0.5–3 atm (EIRD §5.2.8); ±0.05 atm (ERD §4.1.34); ±10% during test (ERD §4.1.35) | SRC-06, SRC-08 |
| Oxygen charge | ±0.005 mole fraction over 0.1–0.4 (ERD §4.1.36) | SRC-08 |
| Chamber temperature | ±0.5 °C over 18–27 °C (EIRD §5.2.8) | SRC-06 |
| Time reference | GMT ±0.03 s (EIRD §5.2.9 / ERD §4.1.98) | SRC-06, SRC-08 |
| Droplet dispense | ±0.25 mm, ±5% reproducibility (ERD §4.1.12/4.1.13) | SRC-08 |
| Droplet imaging | 30 µm resolution, ≥30 fps (EIRD §5.2.1) | SRC-06 |
| Microgravity measurement capability | 1×10⁻⁶ m/s² (ERD §4.1.53) | SRC-08 |

These are **requirements** (what the hardware shall provide), not measured
calibration performance.

## 3. The one indirect consistency check (chamber pressure)

For all 8 telemetry-linked runs the chamber FCU PT16 transducer reading
(PSIA) converts to mmHg and compares with the table's pressure
(`resolution_checks.csv`, `chamber_pressure_crosscheck`):

| Run | FCU PT16 (PSIA) | → mmHg | Table (mmHg) | \|diff\| |
|---|---|---|---|---|
| 20CAL08 | 14.64 | 757.1 | 757.7 | 0.59 |
| 20CAL10 | 14.72 | 761.2 | 762.0 | 0.76 |
| 20CAL12 | 14.77 | 763.8 | 764.2 | 0.37 |
| 20CAL13 | 14.72 | 761.2 | 761.3 | 0.06 |
| 30CAL02 | 14.72 | 761.2 | 760.0 | 1.24 |
| 30CAL03 | 14.72 | 761.2 | 760.0 | 1.24 |
| 30CAL06 | 14.74 | 762.3 | 762.4 | 0.12 |
| 40CAL01 | 14.72 | 761.2 | 760.0 | 1.24 |

Agreement within 0.06–1.24 mmHg (≤0.16%; the three single-snapshot runs account for the larger differences) corroborates the table's pressure
column as absolute chamber pressure in mmHg and shows both values descend
from the same physical quantity. **This is a consistency check, not a
calibration**: it bounds relative error between the two sources but cannot
establish either's absolute accuracy.

## 4. Could calibration explain the flagged anomalies?

- **Pressure 0 mmHg (C11M201):** no calibration scenario produces a true zero;
the record is not among the 8 linked runs, so no chamber value exists to
cross-check it. See `anomaly_resolution.md` A.
- **Eight 0 mm extinction diameters:** a scale calibration error would shift
values systematically, not produce exact zeros on eight non-contiguous
records; the documented measurement-floor mechanism (`anomaly_resolution.md`
B) is a better-supported explanation. No local calibration data exists to
test either further.
- **d_ext > d0 (C13H102, +0.01 mm):** within the 30 µm imaging resolution;
no calibration explanation needed.

## 5. Measurement → instrument → calibration mapping (as required)

| Measurement | Instrument / system | Calibration document | Validity | Uncertainty | Applicable runs |
|---|---|---|---|---|---|
| Chamber pressure | FCU pressure transducers (PT16/17/28/29, PSIA) | **none local** | — | spec ±0.01 atm | 8 linked (5 full logs + 3 snapshots) |
| Chamber temperature | FCU thermometers TM1–4 | **none local** | — | spec ±0.5 °C | 8 linked |
| Gas composition | chamber charge system (+ unverified analyzer) | **none local** | — | spec ±0.005 (O2) | 274 (table only) |
| Droplet diameters | back-lit droplet imaging (A/B series, 512×512 16-bit) | **none local**; TIFF tags carry only nominal 150 dpi | — | spec 30 µm resolution | 274 (table only); images for 7 runs' A/B + 8 runs' D |
| Burning rate | derived from image series | **none local** | — | **unknown — unit unverified** | 274 (table only) |
| Radiometer signal | radiometer (narrow/wide band) | **none local** (PSI hosts a Radiometer Calibration record — not local) | — | unknown | 8 linked |
| Image scale (mm/pixel) | — | **absent from all inspected images** | — | — | — |

## 6. Rules applied

- No calibration correction was applied to any measurement.
- No corrected/derived dataset was created (would require explicit
  authorization; not given).
- All original measurements remain verbatim in the frozen phases.
