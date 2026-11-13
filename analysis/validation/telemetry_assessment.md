# FLEX PSI-69 — Telemetry & Image Archive Assessment (Phase 3, P3-D)

Question answered: *Can the existing telemetry and image archives support
time-resolved analysis, and what blocks it?*

## 1. Linkage status

- **8 of 274 runs** have per-run telemetry in `data/raw/flex/part-01/`:
  20CAL08, 20CAL10, 20CAL12, 20CAL13, 30CAL02, 30CAL03, 30CAL06, 40CAL01.
- All 8 are March–April 2009 ambient-air runs (O2/N2 = 0.21/0.79,
  757.8–764.2 mmHg) — 3 methanol, 5 heptane. Coverage is a **biased
  subset**: no diluted-mixture or high-pressure run has telemetry.
- File inventory per run: main test file (AS/PIP event timeline), chamber
  readings, chamber gases note, radiometer readings, testpoint settings, four
  camera-settings files, three image manifests (A/B/D), plus zip archives.
- Naming defect found: `40CAL01_Testpont_Settings.txt` ("Testpont" typo) —
  identifier-prefix matching still works, but literal filename joins fail.

## 2. Clock domains (at least six)

| Domain | Where it appears | Observed behaviour |
|---|---|---|
| PIP | `PIP TimeStamp` (testpoint settings, radiometer readings, MDCA camera settings) | ~1 Hz sampling; runs ahead of the radiometer frame clock in 20CAL13 by 2.1–2.5 s (offset drifts within the file) |
| MAIN_COMPUTER (GMT) | `MAIN_COMPUTER_TIME(GMT)` + milliseconds | separate computer clock |
| RADIOMETER 100 Hz frame | `RADIOMETER_100HZ_FRAME_TIME(GMT)` | 100 Hz frame counter, integer-second + millisecond fields |
| FCU | `FCU TimeStamp` (chamber readings) | ~1 Hz chamber logging; different absolute offset from AS events |
| Camera clocks | `IPSU1/2/4 TimeStamp` (HIBMS/LLLUV/Color settings) | independent per camera |
| Image reference clock | manifest header `Reference Time Stamp` + `Milliseconds` | per-series reference; A/B/D have different series start references |

Additional structural detail: the main test file documents that HIBMS and
Color images start 2 s before AS dispense while LLLUV images start 2 s before
igniter-on — image series are referenced to **different physical events**, so
even within one run the A/B/D manifests share no common zero.

Requirements-level evidence (EIRD §5.2.9 / ERD §4.1.98): all measurements
shall be GMT-referenced to ±0.03 s. The delivered files are **not**
synchronised to that tolerance by default.

**Consequence: no merged timeline is defensible until a validated clock-offset
map exists. Phase 3 produces no merged time-series product.**

## 3. Sampling and content summary (observed)

| Stream | Sampling | Notes |
|---|---|---|
| Chamber readings (FCU) | ~1 Hz | 376–388 rows per run (20CAL08/10/12/13, 30CAL06); **30CAL02, 30CAL03 and 40CAL01 contain header + exactly 1 data row** — chamber telemetry effectively absent for those 3 runs; PSIA pressures, 4 temperatures (Deg C) |
| Radiometer (PIP) | ~1 Hz rows | 130–148 rows; narrow/wide band radiometer samples, igniter status |
| Testpoint settings (PIP) | event rows | 60+ channels incl. fiber/soot-sampler flags, igniter wattage (9.95 W), dispenser telemetry |
| Image manifests A/B/D | per-frame | 33–34 ms frame deltas (≈30 fps); per-frame timestamps and filenames |

Per-run test-point settings observed for the 8 linked runs: igniter on
0.85–1.2 s, burn-to-completion timer 20–120 s, fiber usage **No**, soot
sampler **No**.

## 4. Image archives

- **23 archives**, ~5.34 GB total: A/B series = TIFF (~525 KB/frame),
  D series = BMP (~922 KB/frame); 800–1290 frames per archive.
- Each archive embeds a manifest `.txt` (image number, disk/file indices,
  millisecond offsets, timestamp, filename) matching the loose manifest files.
- **Known gaps:** 20CAL13 has no A archive; `20CAL13_Readme.txt` lists
  specific missing LLLUV FCI files and image frames.
- Formats: TIFF (uncompressed bit depth to be verified on extraction) and
  BMP; no calibration or pixel-scale metadata was found in the listings.

## 5. Feasibility verdict

| Analysis | Feasible now? | Blocker |
|---|---|---|
| Merge telemetry streams into one run timeline | **No** | six unreconciled clock domains; different series references |
| Relate telemetry events to the table's scalar burn time | **No** | same clock issue + undocumented start/stop definition |
| Extract images for the 8 linked runs | **Yes (pilot)** | extraction itself is trivial; validation against manifests required |
| Image-derived diameter time series / burning rates | **No** | pixel-scale/metadata unverified; burning-rate unit unresolved (P3-A) |
| Chemical-extinction assessment from OH*/LLLUV frames | **No** | frames not extracted or validated; radical-species inference unsupported |

**Recommended pilot (single run, e.g. 20CAL08):** extract one A/B/D series,
verify frame count and timestamps against the manifest, measure the
pixel scale from the dispenser/fiber geometry if any, and only then decide
whether a diameter-time series can be reconstructed. Do not bulk-extract the
5.34 GB archives before this pilot succeeds.
