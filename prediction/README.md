# Prediction Engine — FLEX PSI-69 Recorded-Outcome Predictor

**What this is.** A small, validated prediction pipeline that estimates the
**recorded experimental outcome label** (Extinction / Disruption / Completion)
from **pre-outcome experimental conditions** (fuel, initial diameter, pressure,
gas composition) for the 274-record FLEX-PSI69 table.

**What this is not.** It is not a physical combustion model. It does not use,
interpret, or predict the unresolved burning-rate column; it does not fit d²-law
or evaporation constants; "Extinction" is a recorded label denoting *visible
flame* extinction and **not** chemical extinction; "Disruption" is an
empirically undefined label. Model contributions are **statistical
associations, never causal effects**.

## Quick start

```bash
# from the repository root
notebooks/.venv/bin/python prediction/train.py      # group-aware CV training + serialisation
notebooks/.venv/bin/python prediction/evaluate.py   # independent recomputation + report
notebooks/.venv/bin/python -m pytest prediction/tests/ -v   # 20 tests

# direct Python inference
notebooks/.venv/bin/python -c "
import sys; sys.path.insert(0, 'prediction')
from predict import predict_outcome
print(predict_outcome({'fuel': 'Methanol', 'd0_mm': 3.0, 'pressure_mmHg': 760,
                       'o2_mf': 0.21, 'n2_mf': 0.79, 'co2_mf': 0.0, 'he_mf': 0.0})
      ['predicted_class'])"

# API (documented contract for the frontend developer)
notebooks/.venv/bin/python -m uvicorn prediction.api:app --port 8000
# then GET /health, /features, /model-info and POST /predict
```

## Files

| File | Contents |
|---|---|
| `flex_features.py` | byte-preserving loader, feature engineering, integrity rules |
| `train.py` | group-aware cross-validation training, model selection, serialisation |
| `evaluate.py` | independent metric recomputation from stored OOF predictions → `evaluation_report.md` |
| `explain.py` | coefficients, per-prediction log-odds contributions, exact linear SHAP, permutation importance, OOD detection |
| `predict.py` | direct Python inference (`predict_outcome`, `model_info`, `feature_spec`) |
| `api.py` | FastAPI service (`/health`, `/model-info`, `/features`, `/predict`) |
| `feature_dictionary.csv` | every raw column: population, role, and inclusion/exclusion reason |
| `feature_selection.md` | the selection rules and their justification |
| `model_card.md` | intended use, performance, limitations, ethical/scientific caveats |
| `evaluation_report.md` | generated evaluation report (recomputed) |
| `artifacts/model_manifest.json` | model version, features, validation scheme, metrics, hashes |
| `artifacts/train_stats.json` | training design-matrix mean (SHAP) + raw ranges (OOD) |
| `artifacts/outcome_model.joblib` | serialised selected model |
| `artifacts/oof_predictions.csv` | every record's out-of-fold predictions and probabilities |
| `artifacts/evaluation_metrics.json` | full metrics per candidate model |
| `tests/test_prediction.py` | 20 tests: features, leakage, explanations, contract, API, integrity |

## Headline results (grouped out-of-fold; full details in `evaluation_report.md`)

Selected model: **multinomial logistic regression (class_weight='balanced')**,
version 6.0.0.

| Metric | Model | Majority baseline |
|---|---|---|
| Balanced accuracy | **0.530** | 0.333 |
| Macro-F1 | **0.504** | 0.270 |
| Fold balanced accuracy | 0.573 ± 0.073 (15 folds) | — |

Log loss 0.849; per-class (out-of-fold): Completion P 0.137 / R 0.370 /
F1 0.200 (support 27), Disruption P 0.557 / R 0.557 / F1 0.557 (61),
Extinction P 0.879 / R 0.661 / F1 0.755 (186). The class-balanced model
trades minority-class precision for better average recall; Completion
(27 records) remains the hardest class. The model **reliably beats the majority baseline** but
is a *moderate* predictor — it must not be described as accurate combustion
prediction.

## Validation design (why it is trustworthy for a 274-row table)

- **Group-aware evaluation**: out-of-fold predictions are produced with
  GroupKFold over the 81 experimental-series prefixes (3 seeds × 5 folds), so
  related runs never cross the train/test boundary; the duplicated `193F001`
  pair is guaranteed to share a fold (asserted in tests).
- **Imbalance handled and reported**: class_weight chosen on grouped CV;
  per-class metrics and the majority baseline reported alongside.
- **Uncertainty reported**: fold-level mean ± SD, not a single accuracy number.
- **Honest selection**: a model is serialised only if it beats the baseline on
  grouped-OOF balanced accuracy *and* macro-F1 *and* in *every* fold. All three
  candidates passed; `logreg_balanced` won on the documented primary criterion
  (balanced accuracy).

## Limitations (must be visible wherever predictions are shown)

1. Predictions are of **recorded labels**, not physics; no causal claim.
2. **Experimental independence is not established** (adaptive LOI design) —
   grouped CV mitigates, does not remove, this.
3. "Disruption" is an **undefined label** (61 records).
4. The target space is **imbalanced** (186/61/27); minority-class performance
   is weak.
5. The unresolved burning-rate column is **excluded** entirely.
6. Per-run temperature/gravity are unknown for 266 records → unquantified
   condition confounding.
7. Pressure and diluent are **confounded above 800 mmHg**; the model inherits
   this confounding.
8. Inputs outside the training ranges return **OOD warnings**; the model does
   not extrapolate silently.

## Frontend integration

See `deliverables/FRONTEND_INTEGRATION_GUIDE.md` for endpoints, JSON schemas,
example requests/responses, and how to render explanations and warnings.
