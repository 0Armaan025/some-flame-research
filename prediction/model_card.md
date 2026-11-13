# Model Card — FLEX PSI-69 Recorded-Outcome Predictor

**Model version:** 6.0.0 · **Selected model:** multinomial logistic
regression with `class_weight="balanced"` · **Training data:** 274 FLEX-PSI69
records (157 Methanol / 117 Heptane), March 2009–December 2011 · **Target:**
the recorded `Test end` label (Extinction / Disruption / Completion).

## Intended use

- **Intended:** exploratory/decision-support estimation of which outcome label
  was *recorded* for a given set of pre-outcome conditions, with explicit
  input-validation and out-of-distribution warnings and linear explanations.
- **Not intended:** physical combustion prediction; extinction-limit
  estimation; suppression-efficiency estimation; safety decisions; any use of
  the unresolved burning-rate quantity; any causal claim.

## Performance (grouped out-of-fold; series-grouped 5-fold CV × 3 seeds)

| Metric | Model | Majority baseline |
|---|---|---|
| Balanced accuracy | 0.530 | 0.333 |
| Macro-F1 | 0.504 | 0.270 |
| Fold balanced accuracy (mean ± SD) | 0.573 ± 0.073 | — |
| Multiclass log loss | 0.849 | — |

Per class (OOF): Completion P 0.137 / R 0.370 / F1 0.200 (27),
Disruption P 0.557 / R 0.557 / F1 0.557 (61), Extinction P 0.879 / R 0.661 /
F1 0.755 (186). Brier scores: Completion 0.155, Disruption 0.130,
Extinction 0.212. The model reliably beats the majority baseline in
every fold, but absolute performance is **moderate**.

## Features

Fuel; initial droplet diameter (mm); ambient pressure (mmHg; corrupted 0 mmHg
record treated as missing); O₂/N₂/CO₂/He initial mole fractions; substituted
diluent type (recoded). See `feature_dictionary.csv` and `feature_selection.md`.

## Explanation method

- Coefficients in the standardised/one-hot design space (log-odds per class).
- Per-prediction additive log-odds contributions that exactly reconstruct the
  logits (asserted in tests).
- Exact linear-model SHAP values (`φ = w·(z − mean z)`, exact because the model
  is linear; verified to reconstruct logits on the full training matrix).
- Permutation importance computed on out-of-fold predictions.

**Interpretation rule (enforced in the response payload):** these are
statistical associations of the fitted model with recorded labels — **not
causal effects**.

## Limitations (must be presented with any prediction)

1. Label, not physics: Extinction = *visible flame* extinction; "Disruption" is
   undefined in all available documentation.
2. Experimental independence is not established (adaptive sequential LOI
   design); grouped CV mitigates but does not remove this — all metrics are
   conditional on the grouping being an adequate proxy.
3. Severe class imbalance; minority-class performance is weak.
4. Unquantified confounding: per-run temperature unknown for 266/274 records;
   pressure↔diluent confounded above 800 mmHg.
5. The training distribution is the entire released table; inputs outside it
   trigger OOD warnings and the model must not be used to extrapolate.
6. Calibration is reported per class (Brier scores) but sample sizes limit
   reliability estimates for the minority classes.

## Fairness / misuse

Equal-error behaviour across the two fuels is not guaranteed: per-class recall
is reported for transparency. Any deployment that presents predicted
"extinction" as physical flame extinction would be a misuse of this model.
