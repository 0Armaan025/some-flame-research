# References

**Project data and documentation (local files; the primary evidence base):**

- [R1] NASA PSI, *Study PSI-69 — Flame Extinguishment Experiment.*
  Investigation record; study DOI 10.60555/mbq8-0451; submitted and publicly
  released 31 July 2016. Local copy: `docs/flex/i_Investigation.txt`.
  Establishes: study identity, platform (ISS), hardware (CIR-FCF/MDCA),
  managing centre (NASA GRC), funding (NNX09AM33A), the LOI procedure text,
  the 51-publication list, and the investigator contacts.
- [R2] Williams, F. A., Hicks, M., Nayagam, V., Choi, M. Y., Dryer, F. L.,
  Shaw, B. D. (2005). *Droplet Flame Extinguishment in Microgravity (FLEX) —
  Research Requirements Document* (EIRD v4, 82 pp.). Local copy:
  `docs/flex/FLEX_EIRD_v4.pdf`. Establishes: diagnostic requirements (back-lit
  droplet imaging 30 µm, ≥30 fps), droplet-size range 2–6 mm, fuels and
  purity (>99.5%), chamber environment specifications, pressure/temperature
  accuracies, GMT ±0.03 s synchronisation requirement, microgravity <10⁻⁴
  m/s², and that burning rates/extinction diameters derive from droplet-size
  time evolution (§4.3).
- [R3] *FLEX Test Plan* (details extracted from the 4 November 2005 EIRD).
  Local copy: `docs/flex/FLEX_Test_Plan.pdf`. Establishes: the sequential,
  adaptive LOI procedure (§5.3), burn-to-completion vs finite-extinction vs
  no-ignition outcomes, and the measurement-floor statement for extinction
  droplet sizes.
- [R4] *FLEX-2 Engineering Requirements Document* (FLX-REQ-0001,
  4 February 2010). Local copy: `docs/flex/FLEX Engineering Requirements
  Document.pdf`. Establishes: droplet dispense tolerance ±0.25 mm and ±5%
  reproducibility (§4.1.12–4.1.13), pressure 0.5–3 atm ±0.05 atm and ±10%
  maintenance (§4.1.34–4.1.35), O₂ 0.1–0.4 ±0.005 (§4.1.36), temperature
  18–27 °C, RH <10%, g-level <10⁻⁴ m/s², GMT synchronisation ±0.03 s
  (§4.1.98), droplet imaging requirements, and the 235 mm / 79 µm
  silicon-carbide support fiber (§3.4.1.2.3).
- [R5] *Selections from Engineering Documents for the Flame Extinguishment
  Experiment.* Local copy: `docs/flex/FLEX Overall Ext File-2.pdf`.
  Establishes: FLEX-2 test-matrix context (550 planned points).
- [R6] *FLEX Declaration of Data / investigation description.* Local copy:
  `docs/flex/FLEX DoD.docx`. Establishes (unique content not in [R1]): the
  five FLEX experiment data records hosted in PSI — "FLEX – Calibration",
  "FLEX – LCTF Calibration", "FLEX – Radiometer Calibration", "FLEX – HEP",
  "FLEX – MeOH" — and the analysis/image download structure.

**Publications identified in the study record (cited by [R1]; not local
files):**

- [R7] Dietrich, D. L., Bryg, V. M., Ferkul, P. V., Williams, F. A., Dryer,
  F. L., Shaw, B. D., Choi, M. Y., Nayagam, M. V., Hicks, M. C., Avedisian,
  C. T. *Detailed results from the flame extinguishment experiment (FLEX) —
  March 2009 to December 2011.* NASA NTRS citation 20150023456. (Dataset
  paper; date span matches the analysed table.)
- [R8] Shaw, B. D. *ISS Droplet Combustion Experiments — Uncertainties in
  Droplet Sizes and Burning Rates.* Microgravity Science and Technology.
  DOI 10.1007/s12217-014-9377-x. (Burning-rate definition and uncertainty.)
- [R9] Dembia, C. L., Liu, Y. C., Avedisian, C. T. *Automated Data Analysis
  for Consecutive Images from Droplet Combustion Experiments.*
  DOI 10.5566/ias.v31.p137-148. (Image-reduction method.)
- [R10] Yu, F., Shaw, B. D. *Interpretation of Backlit Droplet Images from
  ISS Droplet Combustion Experiments.* DOI 10.2478/gsr-2014-0007.
  (Image scale/interpretation.)

**Canonical statistical-method references (standard literature):**

- Mann, H. B., Whitney, D. R. (1947). On a test of whether one of two random
  variables is stochastically larger than the other. *Annals of Mathematical
  Statistics* 18(1), 50–60.
- Holm, S. (1979). Simply sequential rejective multiple test procedures.
  *Scandinavian Journal of Statistics* 6(2), 65–70.
- Freeman, G. H., Halton, J. H. (1951). Note on an exact treatment of
  contingency, goodness of fit and other problems of significance.
  *Biometrika* 38, 141–149.

**Reproducible analysis artifacts (this project; numbers in the paper are
recomputed from these):**

- [P1] `analysis/audit/` — Phase 1 dataset audit.
- [P2] `analysis/exploratory/` — Phase 2 exploratory analysis.
- [P3] `analysis/validation/` — Phase 3 scientific validation.
- [P3.5] `analysis/evidence_resolution/` — Phase 3.5 evidence resolution.
- [P4a] `analysis/phase4a/` — Phase 4A comparative analysis (entry point
  `run_analysis.py`; manifest `run_manifest.json`).
