# Metadata Recovery (Phase 3.5, R7/R8)

Status of every experimental-metadata item the Phase 3 matrix flagged as
missing. "Recoverable" means recovered **from a local file**, with the
coverage stated.

| Variable | Status | Where | Coverage | Evidence |
|---|---|---|---|---|
| Study identity / citation | **RESOLVED** | `i_Investigation.txt` | 274/274 | Study PSI-69, DOI 10.60555/mbq8-0451, released 31-Jul-2016, hardware CIR-FCF/MDCA, ISS, grant NNX09AM33A |
| Investigators / contacts | **RESOLVED** | `i_Investigation.txt` (Study contacts rows) | n/a | PI Williams (UCSD); Co-Is Shaw (UC Davis), Hicks (NASA GRC), Nayagam (CWRU), Choi (U. Missouri), Dryer (U. South Carolina); Project Scientist Dietrich (NASA GRC) |
| Authoritative publications | **RESOLVED (as citations)** | `i_Investigation.txt` | 51 works | incl. the dataset paper NTRS 20150023456 and Shaw 10.1007/s12217-014-9377-x |
| Fuel specification | DOCUMENTED_UNCONFIRMED (spec only) | EIRD §6.1.1 | 274/274 | n-heptane (sooting) / methanol (non-sooting), research grade, >99.5%, degassed, dry, 18–27 °C — spec text, no per-run lot certificates |
| Fiber support | **PARTIAL** | Testpoint settings `TP_PARAMETER_FIBER_USAGE_FLAG` | 8/274 | `No` for all 8 linked runs (soot sampler also `No`); unknown for the rest |
| Chamber ambient temperature | **PARTIAL** | `*_Chamber_Readings.txt` FCU TM1–TM4 | 8/274 | 23.57–26.06 °C (TM1) across the 8 linked runs — 5 full logs plus 3 single snapshots; **the experimental table itself has no temperature column** |
| Per-run gravity | **UNRECOVERABLE locally** | all inspected sources | 0/274 | only the requirement (<1×10⁻⁴ m/s²) and the measurement capability (1×10⁻⁶ m/s², 0.01–125 Hz, ERD §4.1.53) are documented; no ISS accelerometer data locally |
| Gas-charge verification | **UNRECOVERABLE locally** | all inspected sources | 0/274 | spec tolerance ±0.005 (O2) only |
| Igniter settings | PARTIAL | Testpoint settings | 8/274 | wattage 9.95 W, on-time 850–1400 ms, burn-to-completion timer 20–120 s |
| Image pixel scale | **UNRECOVERABLE locally** | all inspected images | 0 | only nominal 150 dpi in TIFF tags; see `image_archive_pilot.md` |
| Table export version | PARTIAL | file + study record | — | study-level provenance resolved (DOI); no CSV export date/version marker in the file |

## 1. Classification per the required categories

- **Never recorded (locally):** per-run gravity; gas-charge verification;
  image pixel scale; CSV export version.
- **Recorded in another local file:** fiber flag, chamber temperature,
  igniter settings, burn-to-completion timers — all in `part-01/` telemetry,
  all covering only the 8 linked runs.
- **Recorded but not linked:** same as above (the experimental table carries
  no join to these settings beyond the identifier).
- **Available only in an image/log (not yet extracted):** droplet-size time
  series (image archives); rim/soot-shell geometry.
- **Unrecoverable from available evidence:** per-run gravity, gas-charge
  verification, pixel scale, CSV export version.

## 2. Explicit non-inferences

- Per-run temperature was **not** inferred from the spec range (18–27 °C) or
  from the 8-run chamber values.
- Per-run gravity was **not** inferred from the <10⁻⁴ m/s² requirement.
- Nominal settings were **not** treated as measured values anywhere.
- Fiber usage for the 266 unlinked records was **not** extrapolated from the
  8 `No` flags.

## 3. Originator metadata requests (OQ-8)

1. Per-run chamber temperature (or the analyzed-data records containing it)
   for the 266 runs lacking telemetry.
2. Per-run ISS acceleration/g-level series or summary near each test.
3. Fiber-usage flag per run.
4. Gas-charge verification logs (analyzer readings) per run.
5. The image-analysis scale convention (mm/pixel derivation) and whether the
   table's diameters derive from the A/B (back-lit droplet) series.
