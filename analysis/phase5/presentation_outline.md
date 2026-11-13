# Presentation Outline (7 slides)

Each slide lists its message, the evidence to display, and the exact numbers.
All figures referenced are the frozen Phase 4A figures
(`analysis/phase4a/figures/`).

## Slide 1 — Research problem
- **Message:** microgravity droplet combustion underpins spacecraft fire
  safety; the public FLEX-PSI69 table is widely compared but rarely validated.
- **On screen:** the research question verbatim; a one-line dataset summary
  (274 records; methanol 157 / heptane 117; 2009–2011; ISS/MDCA).
- **Key framing:** "What is *supported* — and what is *not* — by this release?"

## Slide 2 — Dataset and experimental setup
- **Message:** what was measured, and how, per the engineering record.
- **On screen:** table of recorded quantities; method facts from the
  requirements documents (1.5–6 mm droplets; O₂/N₂/CO₂/He mixtures; 0.5–3 atm;
  <10⁻⁴ m/s² requirement; back-lit droplet imaging at 30 µm / ≥30 fps).
- **One honest red flag up front:** the burning-rate column's unit is
  unresolved.

## Slide 3 — Data-quality and validation process
- **Message:** we validated before comparing.
- **On screen:** the phase chain (audit → exploratory → validation → evidence
  resolution → comparative) as a pipeline graphic; the audit numbers:
  77 missing extinction diameters, 12 missing diameters, 34 encoding-artifact
  fields, 2 approximate burn times, 1 pressure-zero record, 8 zero-mm records,
  1 duplicated identifier (`193F001`).
- **Validation outcomes:** burning-rate unit unresolved; "Disruption"
  undefined; independence not established; clocks unreconciled.

## Slide 4 — Outcome comparison
- **Message:** recorded outcome-label composition differs strongly by fuel.
- **On screen:** Figure 1.
- **Numbers:** 80.3% vs 51.3% Extinction; 14.6% vs 32.5% Disruption; 5.1% vs
  16.2% Completion; Freeman–Halton p = 1.75×10⁻⁶; V = 0.3099.
- **Caveat banner:** recorded labels, not mechanism; visible flame ≠ chemical
  extinction.

## Slide 5 — Duration and diameter findings
- **Message:** one strong, one inconclusive, both reported with uncertainty.
- **On screen:** Figure 2 (left) and Figure 3 (right).
- **Numbers:** duration medians 12.10 s vs 7.50 s; U = 4838; p = 1.17×10⁻⁹;
  r = 0.438; heptane−methanol −4.6 s (CI −7.8 to −2.9). Diameter: p = 0.0623
  → **0.0450** under either `193F001` removal → sensitivity-dependent.
- **Caveat banner:** all p-values conditional on independence (adaptive
  design; 81 series).

## Slide 6 — Limitations and scientific interpretation
- **Message:** what the data cannot say is part of the result.
- **On screen:** Figures 4–6 (extinction floor, 4 comparable cells, pressure
  confounding) beside a limitations list.
- **Numbers:** extinction diameter 28% missing + 8 measurement-floor zeros;
  4 of 10 diluent cells fully comparable; all 9 records >800 mmHg in one CO₂
  family; independence not established.

## Slide 7 — Conclusions and future research
- **Message:** two descriptive differences supported; diameter not confirmed;
  physical modelling blocked by definition gaps.
- **On screen:** the three verdicts (supported / sensitivity-dependent /
  blocked) and the eight prioritised originator questions (OQ-1–OQ-8) as a
  readiness checklist.
- **Closing line:** this is comparative experimental analysis, not validated
  physical modelling.
