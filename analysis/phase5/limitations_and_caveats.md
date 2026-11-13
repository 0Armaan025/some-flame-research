# Limitations and Caveats

Ordered by how strongly they qualify the results. Each entry states the
limitation, the affected claim, and its source in the frozen phases.

1. **Experimental independence is not established (binds every p-value).**
   The documented LOI procedure is sequential and adaptive — each test's
   conditions follow from previous outcomes [Test Plan §5.3]. Records cluster
   into 81 identifier series (largest 13) with up to 9 records per test date;
   the identifier `193F001` is duplicated; a second duplicate-timestamp
   cluster exists (C11M201/C11H201). All Mann–Whitney, Fisher, and permutation
   results are therefore conditional on an independence/exchangeability
   assumption the design does not establish. The series-level sensitivity
   analysis is the only comparison that avoids this assumption, and it covers
   4 series only. *Affects: all comparisons.*

2. **Burning-rate column unresolved.** Definition, unit, and measurement
   equation are absent from all inspected documentation; the naive d²-law
   reading is contradicted by the data. No physical rate quantity is computed
   anywhere. *Affects: any rate-based claim (excluded by construction).*

3. **Outcome-label semantics.** "Disruption" is undefined in every inspected
   document; Extinction/Completion are only procedurally contextualised.
   "Extinction" denotes visible flame extinction, not chemical extinction.
   *Affects: §6.1 label statistics (reported as label-level only).*

4. **Missingness.** Extinction diameter 77/274 (28.1%); initial diameter 12;
   burn time 6; burning rate 16. Mechanism unknown — not assumed random;
   never imputed; effective n reported everywhere. *Affects: §6.4
   extinction-diameter comparisons.*

5. **Measurement-floor zeros.** Eight recorded 0 mm extinction diameters (all
   Heptane; Disruption ×4, Completion ×4). The Test Plan documents that
   extinction sizes could be too small to measure, but no source states the
   coding convention; zeros are retained as reported, flagged, and excluded
   only in documented screened variants. *Affects: §6.4 ratio statistics.*

6. **Condition confounding.** Pressure and diluent composition are
   inseparable above 800 mmHg (9 records, one CO₂ family). Per-run
   temperature is unknown for 266/274 records (spec range 18–27 °C only);
   per-run gravity is unavailable; fiber usage is known for 8 runs.
   *Affects: §6.5–6.6 condition and pressure statements.*

7. **No calibration records locally.** Instrument uncertainties are
   specification-level (±0.05 atm pressure, ±0.005 O₂, 30 µm imaging), with
   one indirect corroboration (chamber transducer vs table pressure within
   0.06–1.24 mmHg for the 8 linked runs). *Affects: absolute-accuracy claims
   (none made).*

8. **No time-resolved or image-derived analysis.** Six unreconciled telemetry
   clock domains (offsets 1.225–1.712 s with intra-run drift); no verified
   pixel scale in the image archives; archives inventoried but not measured.
   *Affects: any time-resolved claim (excluded).*

9. **Sparse comparison cells.** Four fully comparable diluent cells, with
   per-side fuel counts as low as 3; the series-level analysis covers 4
   series. *Affects: §6.5 power and generality.*

10. **Provenance granularity.** The study is identified (PSI-69, DOI
    10.60555/mbq8-0451) but the specific CSV export version of the table is
    undocumented. *Affects: citation precision only.*

**Standing caveat for reuse:** any re-analysis that pools all 274 records as
independent, interprets outcome labels as extinction physics, or infers a
burning rate from the unresolved column overstates what this release
supports.
