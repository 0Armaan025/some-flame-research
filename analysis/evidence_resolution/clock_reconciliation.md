# Clock Reconciliation (Phase 3.5, R4)

**Status: BLOCKED for any merged time-resolved product. Offsets are quantified
per run; no synchronization reference exists locally — OQ-6.**

## 1. The six clock domains (as identified in Phase 3, now quantified)

| Domain | Where | Resolution | Sampling |
|---|---|---|---|
| PIP | Testpoint settings, Radiometer readings, MDCA camera settings | 100 µs | ~1 Hz rows |
| MAIN_COMPUTER (GMT) | `MAIN_COMPUTER_TIME(GMT)` + ms field | 1 ms | paired with PIP rows |
| RADIOMETER_100HZ frame | `RADIOMETER_100HZ_FRAME_TIME(GMT)` + ms | 10 ms nominal | 100 Hz frames, ~1 Hz rows |
| FCU | Chamber readings `FCU TimeStamp` | whole-second in the 3 snapshots; microsecond strings in full logs | ~1 Hz |
| Camera IPSU1/2/4 | HIBMS / LLLUV / Color camera settings | per-settings rows | event rows |
| Image reference | frame manifests (`Reference Time Stamp` + per-frame ms) | 1 ms | ~30 fps frames |

## 2. Quantified relationships (`resolution_checks.csv`, `clock_offsets`)

PIP minus MAIN_COMPUTER, per linked run:

| Run | n pairs | median (s) | min (s) | max (s) | net drift (s per 1000 samples, least-squares) |
|---|---|---|---|---|---|
| 20CAL08 | 147 | +1.272 | +1.061 | +2.061 | +6.888 |
| 20CAL10 | 146 | +1.712 | +1.503 | +1.922 | -2.887 |
| 20CAL12 | 148 | +1.386 | +1.172 | +1.597 | -2.894 |
| 20CAL13 | 136 | +1.349 | +1.155 | +1.544 | -2.886 |
| 30CAL02 | 147 | +1.605 | +1.395 | +1.816 | -2.888 |
| 30CAL03 | 130 | +1.525 | +1.339 | +1.712 | -2.878 |
| 30CAL06 | 142 | +1.225 | +1.021 | +1.428 | -2.885 |
| 40CAL01 | 143 | +1.308 | +1.103 | +1.514 | -2.884 |

Key facts:

1. **No constant offset exists.** The PIP–MAIN median ranges 1.226–1.714 s
   across runs; the offsets drift monotonically within each run (e.g.
   20CAL08: 1.315 → 1.922 s over 147 samples, ≈ +6.9 ms per 1000 samples —
   a relative *rate* difference, not a fixed lag).
2. The radiometer 100 Hz frame clock trails MAIN_COMPUTER by ≈1.0 s
   consistently in the first pairs observed, so PIP↔radiometer-frame
   separation is ≈2.3–2.7 s.
3. FCU chamber logs begin 55.6–61.7 s before ignition and are referenced to their
   own clock; camera settings rows are event-logged on camera-local clocks.
4. The three single-row chamber logs are whole-second stamps 0.41–0.61 s
   **before** the AS igniter-on event — consistent with the FCU second-boundary
   truncating the AS sub-second event (see `anomaly_resolution.md` and
   `calibration_assessment.md`).

## 3. What the specification says vs what the files show

- EIRD §5.2.9 / ERD §4.1.98 require all measurements to be GMT-referenced and
  synchronised to within **±0.03 s**.
- The delivered files are **not** synchronised to that tolerance: pairwise
  offsets of 1–2.6 s with intra-run drift of ~1 s. Column *names* saying
  "(GMT)" do not establish GMT (the offsets themselves show these clocks
  disagree), and no timezone/DST assumption can be validated from the files.
- The prior-phase interim artifact
  (`data/interim/flex/20CAL13_timestamped_image_manifest.csv`) already flags
  its image timestamps `camera_index_timestamp_timezone_unverified` — an
  earlier, independent acknowledgement of the same problem.

## 4. The three one-row chamber logs — resolved

| Run | FCU row stamp | AS igniter-on | Δ (s) |
|---|---|---|---|
| 30CAL02 | 2009-03-31 17:16:18.000000 | 17:16:18.610 | −0.610 |
| 30CAL03 | 2009-03-31 19:00:48.000000 | 19:00:48.541 | −0.541 |
| 40CAL01 | 2009-03-31 20:05:50.000000 | 20:05:50.412 | −0.412 |

Each single row is the fractional part of the igniter-on event truncated to
the whole second — i.e. an **event-triggered at-ignition snapshot**, not an
incomplete or corrupt log. Phase 3's "chamber telemetry effectively absent"
concern is resolved for these three runs (each still provides one pressure/
temperature sample that cross-validates the table pressure).

## 5. The `40CAL01_Testpont_Settings.txt` filename typo — resolved

The file is structurally normal (62 columns, 1 data row; fiber flag `No`;
burn-to-completion 20000 ms) and matches the other seven runs' schema. The
typo is in the **filename only**. Rules: the raw file is **not renamed**; any
future join logic must use a tolerant pattern (e.g. `40CAL01*Test*Settings*`),
and the alias is recorded here.

## 6. Consequence

Until a per-run clock model (offset + rate) is validated against a documented
synchronization event — which no local file provides — **no telemetry stream
may be merged with another, with the AS timeline, or with image manifests**.
All time-resolved analysis remains blocked.
