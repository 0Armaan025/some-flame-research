# Executive Summary

**Question.** What measurable differences between methanol and n-heptane are
supported by the 274 FLEX-PSI69 droplet-combustion records (2009–2011, ISS),
and what are the limitations of those comparisons?

**Answer in one paragraph.** Two descriptive differences are supported: the
composition of recorded outcome labels (Extinction 80.3% of methanol records
vs 51.3% of heptane; Freeman–Halton p = 1.75×10⁻⁶, Cramér's V = 0.3099) and
burn duration (medians 12.10 s vs 7.50 s; U = 4838, p = 1.17×10⁻⁹, effect
size r = 0.438, heptane-minus-methanol median difference −4.6 s with 95% CI
−7.8 to −2.9 s). Initial droplet diameter is **not** a confirmed difference
(p 0.0623–0.123 across documented record-handling rules, including p = 0.0450
when either duplicated `193F001` record is removed). Visible flame extinction
diameter is limited by 28% missingness and eight recorded 0 mm
measurement-floor candidates. Diluent comparisons survive only in four
fully comparable oxygen-matched CO₂/He cells; all nine records above 800 mmHg
lie in one CO₂ family, so no pressure effect is claimed. The burning-rate
column is an unresolved scalar — no definition or unit exists in the
documentation and the naive d²-law reading is contradicted by the data — so
no physical rate quantity is computed. Every p-value is conditional on an
independence assumption the sequential experimental design does not
establish.

**What is new here.** The project converted a public experimental table into
a validated, reproducible comparison: a full data audit (missingness,
encoding artifacts, anomalous records), an evidence-resolution phase that
established exactly which measurements are definable and which are blocked,
and a comparative analysis that reports effect sizes, bootstrap intervals,
permutation and series-level sensitivity, and per-cell condition
comparability rather than a single headline p-value.

**What is explicitly not claimed.** No burning constant, regression rate,
evaporation constant, d²-law parameter, chemical-extinction limit, or
physical extinction threshold; no causal or mechanistic explanation of the
duration or outcome differences; no temperature-, gravity-, or
calibration-conditioned claim; no time-resolved or image-derived measurement;
no pressure effect above 800 mmHg.

**Readiness.** Physical modelling of this release remains blocked until the
burning-rate definition, outcome-label semantics, per-run condition metadata,
calibration records, and the experimental series structure are resolved with
the data originators (eight prioritised clarification questions, prepared but
not sent).
