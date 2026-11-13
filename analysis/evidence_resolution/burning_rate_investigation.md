# R1 — Burning-Rate Investigation (Phase 3.5)

**Status: `UNIT UNVERIFIED — PHYSICAL INTERPRETATION BLOCKED`**
(locally unrecoverable; originator confirmation required)

## 1. What was asked

Establish, for the experimental-table column literally headed `Burning rate; mm`:
exact variable name, physical quantity, mathematical definition, original unit,
dimensional vs dimensionless, measured vs derived, method, instrument/resolution,
calibration relationship, uncertainty, and version stability.

## 2. Sources searched (complete list — see `source_document_register.csv`)

| ID | Source | Result |
|---|---|---|
| SRC-01 | raw experimental table (header + 274 values) | header reads `Burning rate; mm` — a length unit, not a rate unit; no footnote or dictionary row in the file |
| SRC-05 | PSI investigation record (`i_Investigation.txt`, full 136 lines incl. the tab-separated publication table) | no column definition; **new evidence: 51 DOI-aligned citations** (see §4) |
| SRC-06 | EIRD v4, full 82-page text search ("burning rate", "burn rate", "regression", "mm/s", "mm2/s", "k0") | experiment-level narrative only; no table-column definition (see §3) |
| SRC-07 | Test Plan (full text) | no definition |
| SRC-08 | FLEX-2 ERD (full text) | no definition; ERD contains no measurement-equation section |
| SRC-09 | DoD.docx (entire extracted text, 1465 chars) | no definition |
| SRC-10 | Overall Ext File-2 (full text) | no definition |
| SRC-11 | notebooks/ (all 10 scripts) | no definition; scripts analyse other quantities |
| SRC-12 | data/interim/flex/ (8 artifacts) | no definition |
| SRC-13 | data/processed/ | empty (0 bytes) |
| SRC-14/15 | reports/, docs/jaxa, tnf | other experiments; out of scope, no FLEX definition |

No calibration record, data dictionary, or reduction code defining this column
exists in any local file.

## 3. Strongest local evidence (experiment level, L1/L2)

- **EIRD §4.3 (PDF p. 30):** "The primary diagnostic is a backlit view of the
  droplet which allows the determination of the droplet size as a function of
  time. **The time evolution of the droplet size yields the droplet burning
  rate (heat release), and extinction droplet size** … the droplet burning rate
  (**instantaneous as well as average**) … may be accurately determined."
- **EIRD §5.2.1 (PDF p. 41):** droplet imaging requirement (30 µm resolution,
  ≥30 fps) is justified as necessary "to obtain droplet burning rates and
  extinction droplet diameters".
- **EIRD §9 (PDF p. 64):** discusses the "D² average burning rate constant (k)"
  and quotes **0.8 mm²/s** for n-heptane/methanol in air at 1 atm as an assumed
  literature value.

These establish: the *experiment's* burning-rate quantity is image-derived and
has instantaneous and average forms; mm²/s is the unit of the *d²-law constant*
in the requirements literature. **None of them names, defines, dimensions, or
units the PSI-69 table column.**

## 4. Consistency forensics — what the column is NOT

Recomputed in `resolution_checks.csv` (rows `burnrate_hypothesis_*`) on the 257
records with all of d0, burn time and rate:

| Fuel | n | Spearman(rate, d0²/t) | Spearman(rate, d0/t) | median rate | median d0²/t |
|---|---|---|---|---|---|
| Methanol | 150 | +0.104 | +0.018 | 0.460 | 0.664 |
| Heptane | 107 | **−0.395** | **−0.417** | 0.540 | 0.960 |
| All | 257 | −0.049 | −0.056 | 0.500 | 0.708 |

The column is uncorrelated with — and for heptane strongly negatively
correlated with — the naive d²-law constant d0²/t. The "average d²-law burning
rate constant" reading is therefore **contradicted by the data itself**. This
is a negative forensic result: it rules out candidates without supplying the
definition. No unit was inferred from these magnitudes.

## 5. Publications that would resolve R1 (identified, not local)

From the PSI-69 publication table (`i_Investigation.txt`, title↔DOI alignment
by column index):

| Publication | Identifier | Why it matters |
|---|---|---|
| "Detailed results from the flame extinguishment experiment (FLEX) — March 2009 to December 2011" (Dietrich et al.) | NTRS 20150023456 | the dataset paper; its date span exactly matches the table |
| "ISS Droplet Combustion Experiments — Uncertainties in Droplet Sizes and Burning Rates" (Shaw) | DOI 10.1007/s12217-014-9377-x | the burning-rate definition and its uncertainty |
| "AUTOMATED DATA ANALYSIS FOR CONSECUTIVE IMAGES FROM DROPLET COMBUSTION EXPERIMENTS" (Dembia, Liu, Avedisian) | DOI 10.5566/ias.v31.p137-148 | the automated reduction method likely behind the table values |
| "Interpretation of Backlit Droplet Images from ISS Droplet Combustion Experiments" (Yu, Shaw) | DOI 10.2478/gsr-2014-0007 | image scale/interpretation |

These are citations, not local evidence (L3). Downloading them is outside the
local-only constraint, so they are named as the resolution path rather than
inspected.

## 6. Final classification and questions for the originator

**Locally unrecoverable; `UNIT UNVERIFIED — PHYSICAL INTERPRETATION BLOCKED`.**
No physical burning-rate constant, regression rate, evaporation constant, or
heat-release quantity may be computed from this column. Dimensionless
rank-based associations remain permissible (and were the only form used in
Phase 2).

Questions for the originator (OQ-1), with the evidence already inspected:

1. What physical quantity does the PSI-69 experimental table column
   `Burning rate; mm` encode — average d²-law burning rate constant, average
   regression rate, instantaneous value, mass/heat-release rate, or something
   else?
2. What is its unit and is the column dimensional? If the "mm" in the header
   is a units artifact, what was intended?
3. What is the measurement equation (e.g. slope of D² vs t over what
   interval), and is it computed per test from the image-derived diameter
   series?
4. Which instrument/analysis pipeline produced it (cf. Dembia et al. 2014
   automated analysis)?
5. What uncertainty or rounding convention applies, and did the definition
   change between the March 2009–December 2011 series?
