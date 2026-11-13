# FLEX PSI-69 — Measurement Uncertainty Assessment (Phase 3, §8)

Purpose: a measurement-uncertainty register that separates **quantified**
uncertainty (documented, with a source) from **unknown** uncertainty. No
uncertainty value is manufactured; spec-level values are labelled as such.

## 1. Uncertainty register by category

| Variable / aspect | Category | Quantified? | Value / statement | Source & level |
|---|---|---|---|---|
| Droplet initial diameter — dispense | Instrument/spec | **Quantified (spec level)** | tolerance ±0.25 mm; reproducibility ±5%; ranges 1.5–5 mm (FLEX-2), 2–6 mm (EIRD) | EIRD §6.1.1; ERD §4.1.33 (requirements) |
| Droplet initial diameter — imaging resolution | Resolution | **Quantified (spec level)** | 30 µm over FOV, ≥30 fps | EIRD §5.2.1 |
| Droplet initial diameter — table reduction | Data transcription | Unknown | reduction procedure for the single table value undocumented; no scale factor found | no source |
| Extinction diameter — imaging | Resolution | **Quantified (spec level)** | 30 µm | EIRD §5.2.1 |
| Extinction diameter — table reduction | Data transcription | Unknown | undocumented; 8 records report 0 mm (interpretation unresolved) | no source |
| Burning rate — unit & method | All categories | **Unknown — blocked** | column definition not found in any inspected document | full-text search, all docs |
| Burning rate — transcription | Encoding | Partially known | 16 records missing (8 empty, 8 `0x96` artifact bytes); no value corruption found | Phase 1 audit |
| Burn time — definition | Data transcription | Unknown | start/stop events not documented for the table value | no source |
| Burn time — clock | Instrument | **Quantified (spec level)** | GMT synchronisation ±0.03 s required | EIRD §5.2.9; ERD §4.1.98 |
| Burn time — approximation flag | Data transcription | **Quantified** | 2 values (`~6`, `~9`) are approximations; preserved and excluded from statistics | source table |
| Pressure — accuracy | Instrument/calibration | **Quantified (spec level)** | ±0.01 atm over 0.5–3 atm (EIRD); ±0.05 atm (ERD); ±10% maintenance during test | EIRD §5.2.8; ERD §4.1.34–4.1.35 |
| Pressure — anomaly | Data transcription | Flagged | 1 record = 0 mmHg (C11M201); retained both as-reported and screened | Phase 1 audit |
| Composition — initial charge | Instrument | **Quantified (spec level)** | O2 ±0.005 mole fraction over 0.1–0.4 | ERD §4.1.36 |
| Composition — reported sums | Data transcription | Quantified deviation | 29 records sum to 0.98–1.01 (never renormalised) | Phase 1 audit |
| Temperature — ambient | Experimental condition | Unknown per run | spec range 18–27 °C, accuracy ±0.5 °C (EIRD); no per-run value | EIRD §5.2.8; ERD §4.1.37 |
| Gravity | Experimental condition | Unknown per run | spec < 1e-4 m/s²; measurement capability 1e-6 m/s²; no per-run data | EIRD §5.1.8; ERD §4.1.52–4.1.53 |
| Fuel purity | Experimental condition | **Quantified (spec level)** | research grade >99.5%, degassed, dry | EIRD §6.1.1 |
| Chamber purity | Experimental condition | **Quantified (spec level)** | fuel vapour <0.005; products <0.02 per species | EIRD §5.1.x |
| Humidity | Experimental condition | **Quantified (spec level)** | RH <10% | ERD §4.1.40 |
| Fiber support | Experimental condition | Known for 8/274 runs | FIBER_USAGE_FLAG = No (8 linked runs); unknown elsewhere | telemetry testpoint settings |
| Ignition energy | Experimental condition | Partially known | igniter wattage 9.95 W, on-time 0.85–1.2 s (8 runs) | telemetry testpoint settings |
| Missingness mechanism | Missingness | Unknown | 77 missing extinction diameters etc.; MCAR/MAR/MNAR undetermined; never imputed | Phase 1/2 |
| Encoding integrity | Encoding | **Quantified** | 34 `0x96` artifact bytes; all treated as missing markers; file otherwise Latin-1 clean | Phase 1 audit |
| Outcome-label semantics | Data transcription | Unknown | "Disruption" undefined; labels ≠ chemical extinction | Phase 3 provenance |
| Table provenance | Data transcription | Partially known | PSI source system identified; no DOI/version/export date | i_Investigation.txt |

## 2. Consequences of the flagged extremes

**Pressure-zero record (C11M201, methanol, 2010-09-06).** Reported pressure
0 mmHg is not physically attainable for a chamber experiment specified at
0.5–3 atm. Handled by: retention in all `as_reported` results; exclusion in
`screened` results (documented rule); no pressure analysis quoting a minimum
without noting the flag. Both interpretations preserved.

**Eight 0-mm extinction diameters (all Heptane; outcomes Disruption ×4,
Completion ×4).** A 0 mm *visible flame extinction diameter* is not a physical
measurement of a flame that extinguished at zero size; most likely a
placeholder. Handled by: retention with the flag
`extinction_diameter_reported_zero`; exclusion in screened variants; the
d_ext/d0 ratio rows report both as-reported (heptane mean 0.633) and screened
(mean 0.699) values; figures mark them with a distinct symbol. Whether they
encode "flame never established" or "not measured" is unconfirmed — recorded
as an open item, not resolved by assumption.

## 3. Propagation stance for Phase 4

No uncertainty propagation is performed in Phase 3. When modelling becomes
defensible, the minimum defensible uncertainty model is:

- initial diameter: spec-level ±0.25 mm (or ±5%, whichever is larger) plus an
  unknown reduction term;
- pressure: ±0.01 atm (EIRD, tighter of the two spec values) + the 0 mmHg
  anomaly rule;
- composition: ±0.005 mole fraction (O2) + the reported-sum deviation;
- burn time: ±0.03 s clock + undefined start/stop semantics (dominant term,
  likely seconds-scale);
- extinction diameter: 30 µm resolution + unknown reduction term + the
  0 mm placeholder rule;
- burning rate: **no uncertainty can be stated — the quantity itself is
  unverified**;
- plus a shared, currently unquantifiable condition uncertainty (temperature,
  gravity, fiber) that affects all cross-condition comparisons.

Until per-run calibration and condition records exist, model-based
uncertainty claims would be manufactured and are prohibited.
