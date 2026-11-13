# Image Archive Pilot (Phase 3.5, R3)

**Status: PARTIALLY RESOLVED — structure, run association and sequence
ordering are established; scale calibration is absent; no image-derived
measurement is claimed.**

Method: ZIP directory listings for all 23 archives + in-memory header reads of the
first frame of each archive (geometry census; first/middle/last spot-checked identical
for 20CAL08 during the pilot). **No bulk extraction was performed; 5.485 GB remain
compressed (16.121 GB uncompressed).**

## 1. Archive census (all 23 archives catalogued in `resolution_checks.csv`)

| Property | A series (TIFF) | B series (TIFF) | D series (BMP) |
|---|---|---|---|
| Archives | 7 | 8 | 8 |
| Frames per archive | 940–1290 | 800–1141 | 960–1160 |
| Dimensions | 512 × 512 | 512 × 512 | 640 × 480 |
| Bit depth | 16-bit uncompressed | 16-bit uncompressed | 24-bit uncompressed |
| Compression | 1 (none) | 1 (none) | 0 (none) |
| Frame size | 525,062 B | 525,062 B | 921,654 B |
| Total frames (census) | 7657 | 8069 | 8532 (24 258 total) |

Note: 20CAL13 has only B and D archives (no A; its Readme lists missing FCI frames), so
the A series has 7 archives. All counts above are from `resolution_checks.csv`.

## 2. Pilot findings (20CAL08, three series)

**Run association — RECOVERED.** Filenames embed the run and series
(`20CAL08A_00200.tif`, `20CAL08D_00000.bmp`); ZIP member timestamps
(2009-03-05 17:21:52–17:22:38 across the three series) bracket the table's Test GMT
(17:22:03) for the same run; each archive embeds a manifest whose reference timestamp matches the
loose manifest in `part-01/`.

**Sequence ordering — RECOVERABLE.** Sequential numeric suffixes; image
intervals in the manifests are 33–34 ms (≈30 fps, matching the EIRD ≥30 fps
requirement). Only 20CAL08D and 20CAL13D have fully contiguous numbering; the
other D archives carry internal gaps (20CAL10D: 2, 20CAL12D: 1, 30CAL02D: 3,
30CAL03D: 20, 30CAL06D: 4, 40CAL01D: 1), and A/B archives are partial captures
of the indexed sequences (20CAL08: index holds 4063/3966/4174 frames for
A/B/D vs 1261/1101/1141 archived). The index-to-archive cross-check shows
**every archived frame is present in the loose manifest** (no unindexed
frames).

**Timestamps — PARTIAL.** Per-frame timestamps exist only in the external
manifest (image-reference clock, whose timezone basis is explicitly unverified
in the prior-phase interim artifact). The TIFF files carry **no EXIF/embedded
timestamps**; their TIFF tags are geometry-only (14 baseline tags).

**Scale calibration — ABSENT.** TIFF XResolution/YResolution are 150.0 with
ResolutionUnit=2 (inches) — a scanner convention, not a physical pixel scale.
No module/fiber reference dimension was found in any inspected metadata.
**mm/pixel is therefore unknown**, and no droplet diameter can be computed
from these images today.

**Resolution adequacy — INDICATIVE ONLY.** At 512×512 (A/B) and the documented
30 µm requirement, the nominal field of view implied by the requirement
(≥3 cm, EIRD §5.2.1) would put 512 pixels across ≥3 cm ⇒ ≲59 µm/pixel; that is
a consistency inference, **not a measured scale**, and is recorded as such.

## 3. Feasibility verdicts

| Pilot question | Verdict | Basis |
|---|---|---|
| Images associate with an experimental run? | **Yes** | filename + zip member timestamps + embedded manifests |
| Sequence ordering recoverable? | **Yes** | sequential suffixes + manifest inter-frame deltas (~33 ms) |
| Image resolution sufficient? | **Indicative** | 512×512/640×480 consistent with the 30 µm requirement; actual scale unverified |
| Scale calibration available? | **No** | only nominal 150 dpi; no mm/pixel anywhere |
| Timestamps exist? | **External only** | per-frame timestamps in manifests; timezone unverified (see `clock_reconciliation.md`) |
| Synchronizable with telemetry? | **No** | image-reference clock unreconciled with AS/FCU/PIP domains |
| Droplet tracking / physical measurement? | **No — not attempted** | blocked by scale + clock gaps above |

## 4. Recommended pilot for any authorised follow-up

1. Extract **one run (20CAL08), D series first (BMP, contiguous 0–1140)** into
   a temporary workspace; verify frame count and hashes against the archive
   manifest.
2. Locate a scale reference: the deployed silicon-carbide fiber (79 µm
   diameter, ERD §4.2.1.x hardware description) appears in back-lit frames;
   measure its pixel width to derive mm/pixel. This is a *validated* path to
   scale that does not require external documents.
3. Cross-check a derived diameter against the table's d0/d_ext for that run
   (20CAL08: d0=1.69 mm, d_ext=0.89 mm) — a closed-loop validation before any
   batch work.
4. Only then (and only if authorized) consider frame-level extraction at scale.

## 5. Explicitly not done

No frames were written to disk; no tracking, segmentation, or measurement was
performed; no claim of image-derived physical quantities is made.
