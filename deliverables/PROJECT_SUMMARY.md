# FLEX-PSI69 — Project Summary

**One paragraph.** FLEX-PSI69 is a microgravity droplet-combustion dataset of
274 ISS experiments (methanol and n-heptane, 2009–2011). Over six validated
research phases we audited the data, resolved every identifiable evidence gap,
and produced a defensible comparative analysis: recorded outcome labels differ
strongly between the fuels, burn durations differ substantially, and the
apparent initial-diameter difference proves sensitive to how a duplicated
record is handled — so it is not claimed. The project ships a research paper,
a validated prediction engine for *recorded outcome labels* with honest
explanations and uncertainty, and a complete handoff for the frontend team.

**The problem.** Public experimental tables are widely compared and rarely
validated. We set out to compare two fuels from the FLEX-PSI69 release
without overclaiming anything the data cannot support.

**The data.** 274 records (157 methanol / 117 heptane): outcome label,
pressure, O₂/N₂/CO₂/He composition, initial diameter, visible flame
extinction diameter, a burning-rate value, and burn time; per-run telemetry
for 8 runs.

**The discoveries.**
- Outcome labels differ: Extinction 80.3% vs 51.3% (Freeman–Halton p = 1.75×10⁻⁶).
- Durations differ: medians 12.10 s vs 7.50 s (p = 1.17×10⁻⁹; effect size r = 0.438).
- Initial diameter: p = 0.0623, **but 0.0450** if either duplicated `193F001`
  record is removed — reported as sensitivity-dependent, not confirmed.
- The burning-rate column's unit is **unresolved in all documentation**; the
  naive d²-law reading is contradicted by the data itself.
- Nine records above 800 mmHg all belong to one CO₂-diluted family → pressure
  effects are not identifiable.
- Experimental independence is **not established** (adaptive test design).

**The platform (planned).** A frontend on top of a validated prediction
service: enter experimental conditions → predicted recorded outcome with
probabilities, contributing features, and out-of-distribution warnings;
browse the frozen comparison tables and figures; limitations always visible.

**The platform.** A deterministic *evidence intelligence engine*
(`intelligence/`) answers seven scientific questions over the frozen research
artifacts — outcome differences, duration, oxygen evidence, comparability,
pressure confounding, data-quality sensitivity, and missing information — each
answer carrying supporting experiments, numbers with denominators, a
four-dimension interpretable evidence ranking, and limitations. No LLM, no
invented values; the tests re-verify every number against the frozen CSVs.

**The prediction component.** An optional, separately validated classifier:
multinomial logistic regression on pre-outcome conditions only with
**series-grouped** cross-validation (balanced accuracy 0.530 vs a 0.333
majority baseline, macro-F1 0.504 vs 0.270, every fold above baseline), exact
linear explanations, and OOD warnings. It predicts **recorded labels**, not
combustion physics.

**The limitations.** Label semantics ("Disruption" is undefined), 28% missing
extinction diameters, an unresolved burning-rate column, unreconciled clocks,
per-run metadata for 8 of 274 runs, and unestablished independence — all
documented and all visible wherever results are shown.

**The future direction.** Eight prioritised questions await the data
originators (burning-rate definition, label semantics, metadata, calibration,
series structure). Physical modelling stays blocked until those are answered.

**Status.** Analysis complete and frozen; prediction engine validated
(20 tests); paper PDF built (18 pages); all artifacts local.
