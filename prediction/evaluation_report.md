# Prediction Engine — Evaluation Report

**Model:** `logreg_balanced` (version 6.0.0), trained on 274 records in 81 experimental-series groups.

**Validation scheme:** GroupKFold(n_splits=5) over experimental-series prefixes, 3 seeds; out-of-fold pooling

## Independent recomputation

The numbers below were recomputed by `evaluate.py` from the stored out-of-fold predictions (`artifacts/oof_predictions.csv`), not copied from the training log. Discrepancies vs the training metrics: **none**.

## Grouped out-of-fold metrics (pooled over all folds)

| Metric | Selected model | Majority baseline |
|---|---|---|
| Accuracy | 0.6095 | 0.6788 |
| Balanced accuracy | **0.5297** | 0.3333 |
| Macro-F1 | **0.5040** | 0.2696 |
| Log loss | 0.8492 | n/a (hard labels) |

Per-fold variability across the 15 grouped folds (3 seeds × 5 folds): balanced accuracy 0.5733 ± 0.0733, macro-F1 0.5327 ± 0.0622.

## Per-class performance (out-of-fold)

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Completion | 0.137 | 0.370 | 0.200 | 27 |
| Disruption | 0.557 | 0.557 | 0.557 | 61 |
| Extinction | 0.879 | 0.661 | 0.755 | 186 |

## Confusion matrix (out-of-fold, rows = true, cols = predicted)

| true \ predicted | Completion | Disruption | Extinction |
|---|---|---|---|
| Completion | 10 | 7 | 10 |
| Disruption | 20 | 34 | 7 |
| Extinction | 43 | 20 | 123 |

## Interpretation

- The model **outperforms the majority-class baseline** on grouped out-of-fold data (balanced accuracy 0.530 vs 0.333; macro-F1 0.504 vs 0.270); every validation fold exceeds the baseline's balanced accuracy.
- Performance is **moderate, not strong**: balanced accuracy ≈ 0.53 and macro-F1 ≈ 0.50 mean the model separates the classes markedly better than chance but with substantial error, concentrated in the minority classes (Completion: 27 records).
- All results are **conditional on an independence assumption the experimental design does not establish** (sequential/adaptive LOI procedure, series clustering, duplicated identifier). Grouped CV mitigates but does not remove this.
- The target is the **recorded outcome label**. 'Disruption' is an undefined label, and Extinction is visible-flame extinction. These predictions are label predictions, not combustion physics.

## Reproduce

```bash
notebooks/.venv/bin/python prediction/train.py
notebooks/.venv/bin/python prediction/evaluate.py
notebooks/.venv/bin/python -m pytest prediction/tests/ -v
```
