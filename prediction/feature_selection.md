# Feature Selection — Rules, Decisions, and Justification

## B1. Selection rules (applied in order)

A raw column may become a model feature only if it is:

1. **Available before the outcome** (no post-outcome measurement);
2. **Documented** in the source table header or a project document, with an
   unambiguous meaning;
3. **Sufficiently populated** (missingness below ~5%, or missingness handled
   with an explicit indicator);
4. **Not derived from the outcome** in any way.

## C. Decisions

| Column | Decision | Rule(s) engaged | Justification |
|---|---|---|---|
| `Fuel` | **INCLUDED** | — | 274/274 populated; the primary scientific question is a fuel comparison |
| `Droplet initial diameter; mm` | **INCLUDED** | rule 3 (missingness indicator) | 262/274 populated; documented (mm) with spec-level tolerances; the 12 missing rows are modelled with a missingness indicator + median imputation *inside the fitted pipeline* (no raw data modified) |
| `Ambient pressure; mmHg` | **INCLUDED** | rules 1, 3 | 273/274 usable. The single 0 mmHg record (C11M201) is a **documented corrupted transcription** (Phase 3.5) and is treated as missing, never as 0 and never imputed from the series median |
| `O/N/CO/He initial mole fractions` | **INCLUDED** | — | 274/274 populated; pre-outcome conditions; reported values used verbatim (never renormalised; 29 records with reported sums ≠ 1.000 keep their reported values) |
| `diluent_type` (recoded) | **INCLUDED** | rules 1, 2 | deterministic recode of the CO2/He columns into the diluent identity (CO2 / He / both / none); physically meaningful and pre-outcome; adds no information beyond its parents |
| `Burn time; s` | **EXCLUDED** | rules 1, 4 | post-outcome measurement |
| `Visible flame extinction diameter; mm` | **EXCLUDED** | rules 1, 4 | post-outcome measurement (and the label's definition) |
| `Burning rate; mm` | **EXCLUDED** | rule 2 | **unit and definition unresolved in all available documentation (R1 BLOCKED)**; the project's integrity rules forbid using it as a physical quantity |
| `Test end` | **TARGET** | — | the prediction target; never a feature |
| `FLEX Test #`, `FLEX Identifier` | **EXCLUDED as features** | rule 4 (session proxies) | available pre-outcome but not physical conditions; including them would let the model memorise run identity |
| `Test Date`, `Test GMT` | **EXCLUDED as features** | rule 4 (series proxies) | timestamps proxy the experimental series/campaign; a model using them would learn "which campaign occurred when" rather than condition physics (the campaign is the grouping variable for validation, so it must not also be an input) |
| Per-run telemetry | **EXCLUDED** | rule 1 | post-outcome streams; clock domains unreconciled (R4 BLOCKED) |
| Derived pressures/composition renormalisations | **EXCLUDED** | rule 2 | renormalising would alter reported values; prohibited |

## Series grouping

The identifier prefix (e.g. `193`, `C03`, `20CA`) is used **only** as the
grouping variable for validation (81 groups). This prevents (a) related runs
in a series crossing the train/test boundary and (b) the duplicated `193F001`
pair being split across folds (asserted in the test suite).

## Missing-value handling (modelling-time only)

- `d0_mm`: 12 missing → median imputation **inside the CV folds** (fitted on
  the training part only) plus a missingness indicator column.
- `pressure_mmHg`: 1 missing (the corrupted record) → same mechanism.
- No raw data is altered; all statistics of missingness are reported.

## Class imbalance

The target is 186/61/27. Both plain and `class_weight="balanced"` logistic
regression were trained and the choice was made **on grouped out-of-fold
performance** (documented selection rule: highest grouped-OOF balanced
accuracy, macro-F1 as tie-break). Per-class precision/recall are reported so
the imbalance penalty is visible.
