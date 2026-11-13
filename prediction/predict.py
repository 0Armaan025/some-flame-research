"""FLEX PSI-69 Phase 6 - predict.py.

Direct Python inference for the recorded-outcome predictor. The frontend team
may call `predict_outcome(conditions)` directly, or go through the FastAPI
service in api.py which wraps this module.

Contract (documented in README.md / FRONTEND_INTEGRATION_GUIDE.md):

    from prediction.predict import predict_outcome
    response = predict_outcome({
        "fuel": "Methanol",
        "d0_mm": 3.0,
        "pressure_mmHg": 760,
        "o2_mf": 0.21, "n2_mf": 0.79, "co2_mf": 0.0, "he_mf": 0.0,
    })

Every response carries the predicted class, class probabilities, the inputs
actually used, contributing features, model version, training size, the
grouped-CV evaluation summary, and input/OOD warnings. Interpretations are
statistical associations, never causal effects.
"""

import json
import os
import sys
from collections import OrderedDict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explain
import flex_features as ff

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")

_MODEL_CACHE = {}


def load_everything():
    if "bundle" in _MODEL_CACHE:
        return _MODEL_CACHE["bundle"]
    manifest = explain.load_manifest()
    if not manifest["model"]["selected_usable"]:
        raise RuntimeError("no usable model was selected; baseline-only mode")
    model = explain.load_model()
    with open(os.path.join(ART, "train_stats.json")) as fh:
        stats = json.load(fh)
    with open(os.path.join(ART, "evaluation_metrics.json")) as fh:
        metrics = json.load(fh)
    bundle = dict(model=model, manifest=manifest, stats=stats, metrics=metrics,
                  z_train_mean=np.asarray(stats["z_train_mean"], float))
    _MODEL_CACHE["bundle"] = bundle
    return bundle


REQUIRED_INPUTS = ("fuel", "d0_mm", "pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf")


def _dedupe(warnings):
    seen, out = set(), []
    for w in warnings:
        key = (w.get("type"), str(w.get("feature")))
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out


def normalise_conditions(conditions):
    """Coerce a request dict into the model's raw feature row.

    The 0 mmHg corrupted value is rejected (treated as missing) exactly as in
    training; composition values are validated to [0, 1]; diluent_type is
    recoded from the CO2/He fractions when not supplied.
    """
    row = OrderedDict()
    warnings = []
    for key in ("d0_mm", "pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf"):
        v = conditions.get(key)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            row[key] = np.nan
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            row[key] = np.nan
            warnings.append(dict(type="invalid_numeric_input", feature=key,
                                 value=conditions.get(key),
                                 message=f"{key} is not numeric; treated as missing"))
            continue
        if key in ("o2_mf", "n2_mf", "co2_mf", "he_mf") and not (0.0 <= v <= 1.0):
            warnings.append(dict(type="numeric_out_of_physical_range", feature=key,
                                 value=v, message=f"{key}={v} is not a valid mole "
                                 "fraction (must be 0-1)"))
        row[key] = v
    if row["pressure_mmHg"] == 0.0:
        row["pressure_mmHg"] = np.nan
        warnings.append(dict(type="corrupted_value_rejected", feature="pressure_mmHg",
                             value=0.0,
                             message=("0 mmHg is the documented corrupted record value "
                                      "(C11M201); treated as missing")))
    fuel = conditions.get("fuel")
    if fuel not in ff.FUELS:
        row["fuel"] = fuel if fuel else np.nan
        warnings.append(dict(type="unseen_categorical_value", feature="fuel",
                             value=fuel,
                             message=f"fuel={fuel!r} was not observed in training"))
    else:
        row["fuel"] = fuel
    if "diluent_type" in conditions and conditions["diluent_type"]:
        row["diluent_type"] = conditions["diluent_type"]
    else:
        co2 = row.get("co2_mf") or 0.0
        he = row.get("he_mf") or 0.0
        row["diluent_type"] = ("CO2+He" if co2 > 0 and he > 0 else
                               "CO2" if co2 > 0 else
                               "He" if he > 0 else "none")
    return row, warnings


def predict_outcome(conditions, explain_top=5):
    """Predict the recorded outcome label for one condition set.

    Returns the full documented response schema (see README).
    """
    bundle = load_everything()
    model, manifest = bundle["model"], bundle["manifest"]
    row, input_warnings = normalise_conditions(conditions)
    df_row = pd.DataFrame([{c: row[c] for c in
                            ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES}])
    ood_warnings, missing = explain.ood_check(row, bundle["stats"]["raw_ranges"])

    details = explain.explain_row(model, df_row, bundle["z_train_mean"])
    detail = details[0]
    classes = [str(c) for c in detail["classes"]]
    probs = {str(k): float(v) for k, v in detail["probabilities"].items()}
    pred = str(detail["predicted_class"])

    # contributions for the predicted class and the runner-up, ranked
    ranked = sorted(probs, key=lambda c: -probs[c])
    contributions = {}
    for c in (ranked[0], ranked[1] if len(ranked) > 1 else None):
        if c is None:
            continue
        items = sorted(detail["contributions_log_odds"][c].items(),
                       key=lambda kv: -abs(kv[1]))[:explain_top]
        contributions[str(c)] = [OrderedDict(feature=f, contribution_log_odds=round(v, 4))
                                 for f, v in items]
    shap_items = sorted(detail["shap_values_log_odds"][ranked[0]].items(),
                        key=lambda kv: -abs(kv[1]))[:explain_top]
    shap_top = [OrderedDict(feature=f, shap_log_odds=round(v, 4)) for f, v in shap_items]

    sel = manifest["model"]["selected"]
    eval_metrics = bundle["metrics"]["results"][sel]
    response = OrderedDict(
        predicted_class=pred,
        class_probabilities={c: round(probs[c], 4) for c in classes},
        model=OrderedDict(
            version=manifest["model"]["version"],
            type="multinomial logistic regression (class_weight=balanced)",
            training_records=manifest["model"]["training_records"],
            training_groups=manifest["model"]["training_groups"],
            classes=classes,
            validation_scheme=manifest["validation"]["scheme"],
        ),
        evaluation_summary=OrderedDict(
            grouped_oof_balanced_accuracy=round(eval_metrics["balanced_accuracy"], 4),
            grouped_oof_macro_f1=round(eval_metrics["macro_f1"], 4),
            fold_balanced_accuracy_mean_sd=[
                round(eval_metrics["fold_balanced_accuracy_mean"], 4),
                round(eval_metrics["fold_balanced_accuracy_sd"], 4)],
            majority_baseline_balanced_accuracy=round(
                manifest["validation"]["baseline"]["balanced_accuracy"], 4),
            per_class=eval_metrics["per_class"],
        ),
        inputs_used={c: (None if (isinstance(row[c], float) and np.isnan(row[c]))
                         else row[c])
                     for c in ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES},
        features_used=list(ff.NUMERIC_FEATURES) + list(ff.CATEGORICAL_FEATURES),
        explanation=OrderedDict(
            logits={str(k): round(float(v), 4) for k, v in detail["logits"].items()},
            intercepts={str(k): round(float(v), 4)
                        for k, v in detail["intercepts"].items()},
            contributions_log_odds=contributions,
            exact_linear_shap_top=shap_top,
            shap_base_logits={str(k): round(float(v), 4)
                              for k, v in detail["shap_base_logits"].items()},
            interpretation_note=("contributions are additive log-odds terms of the "
                                 "fitted linear model on this input; SHAP values are "
                                 "exact for a linear model and are relative to the "
                                 "training mean. They are STATISTICAL ASSOCIATIONS, "
                                 "not causal effects."),
        ),
        warnings=_dedupe(input_warnings + ood_warnings),
        missing_features=missing,
    )
    return response


def model_info():
    bundle = load_everything()
    m = bundle["manifest"]
    sel = m["model"]["selected"]
    return OrderedDict(
        model_version=m["model"]["version"],
        selected_model=sel,
        classes=m["model"]["classes"],
        features=m["model"]["features"],
        training_records=m["model"]["training_records"],
        validation_scheme=m["validation"]["scheme"],
        baseline=m["validation"]["baseline"],
        oof_metrics=bundle["metrics"]["results"][sel],
        restrictions=m["restrictions"],
    )


def feature_spec():
    bundle = load_everything()
    ranges = bundle["stats"]["raw_ranges"]
    spec = []
    for col in ff.NUMERIC_FEATURES:
        r = ranges[col]
        spec.append(OrderedDict(
            feature=col, label=ff.FEATURE_LABELS[col], type="numeric",
            training_min=r["min"], training_max=r["max"],
            training_median=r["median"], required=col != "diluent_type",
            note=("0 mmHg rejected as corrupted; treated as missing"
                  if col == "pressure_mmHg" else None)))
    for col in ff.CATEGORICAL_FEATURES:
        spec.append(OrderedDict(
            feature=col, label=ff.FEATURE_LABELS[col], type="categorical",
            allowed_values=ranges["_categoricals"][col], required=True, note=None))
    return spec
