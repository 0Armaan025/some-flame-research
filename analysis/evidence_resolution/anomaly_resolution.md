# Anomaly Resolution (Phase 3.5, R6)

Three anomaly classes are investigated. All records are **retained**; nothing
is deleted, imputed, or silently re-coded. Every quantity below is recomputed
in `resolution_checks.csv`.

## A. Pressure = 0 mmHg — C11M201 (test 114)

**Status: PARTIALLY RESOLVED (forensically characterised; true value locally
unrecoverable).**

| Attribute | Value (from raw) |
|---|---|
| Identifier / test | C11M201 / 114 |
| Fuel / date / time | Methanol / 9/6/2010 / 19:14:22 |
| Reported composition | O2=0.20 / N2=0.45 / CO2=0.35 |
| Reported measurements | d0=3.23 mm, d_ext=1.68 mm, rate=0.42, t=18.9 s, Extinction |
| C11 series pressures (siblings) | 531.1, 532.8, 534.6, 535.8, 536.3 mmHg (median 534.6) |

**Evidence gathered:**

1. The measurement set is otherwise entirely in-family with the C11 series
   (compare C11M101/301/401 at the same composition).
2. C11M201 was run on the same day as C11H101 (531.1) and C11H201 (532.8).
3. **C11M201's GMT timestamp (19:14:22) is identical to C11H201's** — one of
   only two duplicate date-time clusters in the whole table (the other being
   the 193F001 collision). Two different-fuel tests at the same second is not
   physically consistent with one MDCA dispense cycle, which points to a
   table-level transcription/export defect rather than an instrument event.
4. A pressure of 0 mmHg is not physically attainable for a facility specified
   at 0.5–3 atm and contradicts every sibling record.

**Classification of candidate explanations:**

| Explanation | Support |
|---|---|
| Table transcription/export defect on a real run | **strongest** (series coherence + timestamp collision) |
| Missing-value placeholder written as 0 | plausible; the file elsewhere uses blanks/`0x96` for missing, so 0 is not the file's missing convention |
| Instrument failure at charge | no supporting evidence; would not normally zero the reported value |
| Actual zero measurement | physically impossible |

**Not done:** the true pressure was **not imputed** (the series median is
recorded as context only). The record is retained with its flag and excluded
only in documented screened variants.

## B. Eight zero-mm extinction diameters

**Status: PARTIALLY RESOLVED (mechanism documented; per-record classification
unknown).**

Enumeration (independently reproduced; see `resolution_checks.csv` row
`zero_extinction_records`):

| Test | Identifier | Fuel | Date | O2/N2/CO2 | d0 (mm) | t (s) | Outcome |
|---|---|---|---|---|---|---|---|
| 39 | 224F001 | Heptane | 1/7/2010 | 0.34/0.66/0 | 2.91 | 9.9 | Disruption |
| 43 | 223F002 | Heptane | 1/8/2010 | 0.30/0.70/0 | 2.97 | 11.4 | Disruption |
| 51 | 209F005 | Heptane | 1/19/2010 | 0.21/0.79/0 | 2.41 | 8.2 | Completion |
| 52 | 210F002 | Heptane | 1/11/2010 | 0.30/0.70/0 | 3.53 | 18.3 | Disruption |
| 63 | 301F002 | Heptane | 3/11/2010 | 0.18/0.81/0 | 2.15 | 9.6 | Completion |
| 69 | 193R002 | Heptane | 3/23/2010 | 0.14/0.84/0 | 1.10 | 1.3 | Completion |
| 93 | 149F001 | Heptane | 6/15/2010 | 0.25/0.60/0.15 | 2.48 | 8.3 | Disruption |
| 135 | C21H501 | Heptane | 10/6/2010 | 0.24/0.56/0.20 | 2.78 | 10.8 | Completion |

**Verified facts (correction COR-01 records the Phase 1 split error):**

- All eight are **Heptane**; none is Methanol.
- Outcome split is **Disruption ×4, Completion ×4** (Phase 1's "×5/×3" was
  wrong; documented in `correction_register.csv`, frozen file unmodified).
- All eight have non-zero burn times (1.3–18.3 s) and mid-range initial
  diameters; none is air-He- diluted; pressures span 534.9–771.4 mmHg.

**Documented mechanism (L3):** the Test Plan §5.3 states that "there were
ambient conditions where the extinction droplet sizes … were too small to
either be observed or measured with the available diagnostics" — a
measurement floor exists, so a zero-read/non-detection placeholder is
plausible for droplets that burned down below measurability.

**Remaining ambiguity:**

- Four of the eight are labelled **Completion**, under which a meaningful
  extinction diameter would not normally be expected either — so a
  "too small to measure" reading and a "burned to completion ⇒ no finite
  extinction diameter" reading can explain different subsets; neither is
  stated anywhere as the coding convention.
- Four are **Disruption** (an undefined label, see `outcome_semantics.md`).
- No source documents a zero-coding convention, and no arithmetic pattern
  (e.g. d0 ≈ rate × t) reproduces the zeros.

**Not done:** zeros were not converted to missing; the as-reported and screened
variants are both preserved everywhere.

## C. Extinction diameter > initial diameter (C13H102, test 129)

**Status: RESOLVED (within documented measurement resolution).**

d0 = 3.33 mm, d_ext = 3.34 mm — an excess of **0.01 mm**, one third of the
documented 30 µm imaging resolution (EIRD §5.2.1). The observation is
consistent with measurement uncertainty at the resolution limit; no rejection
is warranted and the record is retained with its flag. Alternative
explanations (different measurement definitions for the two diameters, image
calibration differences) remain possible but are unnecessary to invoke given
the resolution allowance; calibration forensics are in
`calibration_assessment.md`.

## Summary

| Anomaly | Records | Status | Action |
|---|---|---|---|
| Pressure 0 mmHg | 1 (C11M201) | Partially resolved (transcription defect indicated; true value unknown) | retain, flag, screen; OQ-3 |
| Extinction diameter 0 mm | 8 (Heptane) | Partially resolved (measurement-floor mechanism documented; per-record meaning unknown) | retain, flag, screen; OQ-4 |
| d_ext > d0 | 1 (C13H102, +0.01 mm) | Resolved (within 30 µm resolution) | retain, flag |
