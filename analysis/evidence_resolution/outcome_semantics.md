# Outcome Semantics — the "Disruption" Label (Phase 3.5)

**Status: `OUTCOME SEMANTICS UNVERIFIED`** (locally unrecoverable; originator
confirmation required for OQ-2)

## 1. What was searched

Full-text search (case-insensitive) for `disrupt` across **every** local
document that could plausibly define it:

| Source | Occurrences of "disrupt" |
|---|---|
| `docs/flex/FLEX_EIRD_v4.pdf` (82 pp) | 0 |
| `docs/flex/FLEX_Test_Plan.pdf` | 0 |
| `docs/flex/FLEX Engineering Requirements Document.pdf` | 0 |
| `docs/flex/FLEX Overall Ext File-2.pdf` | 0 |
| `docs/flex/FLEX DoD.docx` (complete extracted text) | 0 |
| `docs/flex/i_Investigation.txt` (full 136 lines) | 0 |

Related mechanistic terms (`breakup`, `microexplosion`, `micro-explosion`) are
also absent from the EIRD text.

## 2. What the documented procedure does establish (L3)

The Test Plan §5.3 / `i_Investigation.txt` Comment[Approach] (near-identical text)
documents an LOI-determination procedure with three observable end states:

- **burn to completion** — "droplets burning to completion (as opposed to
  extinguishing at a finite droplet size)" → plausibly the `Completion` label;
- **finite extinction diameter at flame extinction** → plausibly the
  `Extinction` label;
- **no ignition** — the sequence ends where "the droplet does not ignite".

The table's third label, **`Disruption`** (61 records), corresponds to none of
these three documented end states.

## 3. What can and cannot be said

- **Can be said (from the data alone, descriptive):** Disruption occurs in 61
  records (23 Methanol / 38 Heptane); 24 of them carry a measured extinction
  diameter and 37 do not; the label is mutually exclusive with the other two
  in the table's encoding.
- **Cannot be said (no evidence):** whether "Disruption" denotes droplet
  breakup, flame blow-off, fiber/droplet detachment, igniter interaction, or a
  re-classification of unclassifiable tests; whether it is visually or
  instrument-derived; whether its definition was stable across the 80 test
  dates / 81 series.
- **Explicitly not done:** no mechanistic interpretation was inferred from the
  label, and Phase 2's outcome analyses carry this caveat.

## 4. Consequences

- Any three-category outcome analysis (Phase 2 descriptive tables; future
  modelling) contains one undefined category.
- "Disruption" records cannot be pooled with, or separated from, Extinction on
  scientific grounds until defined; Phase 2 therefore reported per-outcome
  strata rather than pooling.

## 5. Originator question (OQ-2)

1. What is the operational definition of the `Test end = Disruption` label in
   the PSI-69 experimental table?
2. Which observation (visual color video, OH\*/LLLUV imaging, droplet backlit
   view, or operator judgement) assigns it?
3. Is it mutually exclusive with Extinction and Completion, and what happens
   to tests showing both disruption-like and extinction-like behaviour?
4. Did the definition or its usage change across the 2009–2011 series?
