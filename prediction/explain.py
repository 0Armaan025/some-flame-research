"""FLEX PSI-69 Phase 6 - model explanations and out-of-distribution detection.

Explanation methods for the selected (linear) model, all verifiable:

* coefficient table (log-odds per expanded feature per class);
* per-prediction additive contributions in log-odds space
  (logit_k = intercept_k + sum_j w_kj * z_j);
* exact linear-model SHAP values phi_kj = w_kj * (z_j - mean_z_j) with
  logit_k = base_k + sum_j phi_kj (exact because the model is linear in the
  preprocessed features - no approximation, no decorative output);
* permutation importance computed on held-out (out-of-fold) predictions.

Association language only: contributions are statistical associations of the
fitted model, never causal effects.
"""

import json
import os
import sys
from collections import Counter, OrderedDict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flex_features as ff

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")


def load_manifest():
    with open(os.path.join(ART, "model_manifest.json")) as fh:
        return json.load(fh)


def load_model():
    import joblib
    return joblib.load(os.path.join(ART, "outcome_model.joblib"))


def expanded_feature_names(model):
    pre = model.named_steps["pre"]
    imp = pre.named_transformers_["num"].named_steps["impute"]
    ohe = pre.named_transformers_["cat"].named_steps["onehot"]
    names = [f"num:{c}" for c in ff.NUMERIC_FEATURES]
    if imp.indicator_ is not None:
        names += [f"num:{ff.NUMERIC_FEATURES[j]}_MISSING"
                  for j in imp.indicator_.features_]
    names += [f"cat:{n}" for n in ohe.get_feature_names_out(ff.CATEGORICAL_FEATURES)]
    return names


def preprocessed(model, df):
    return model.named_steps["pre"].transform(df)


def coefficient_table(model):
    """Coefficients in the preprocessed (standardised/one-hot) space."""
    clf = model.named_steps["clf"]
    names = expanded_feature_names(model)
    classes = list(clf.classes_)
    table = []
    for j, name in enumerate(names):
        row = OrderedDict(feature=name)
        for i, c in enumerate(classes):
            # multinomial: coef_ has one row per class for OvR-normalised
            # multinomial in sklearn -> interpret as log-odds contribution
            row[f"coef_{c}"] = float(clf.coef_[i, j])
        table.append(row)
    intercept = OrderedDict(feature="(intercept)")
    for i, c in enumerate(classes):
        intercept[f"coef_{c}"] = float(clf.intercept_[i])
    table.append(intercept)
    return classes, table

def explain_row(model, df_row, z_train_mean):
    """Per-prediction explanation with contributions and exact linear SHAP.

    z_train_mean: mean of the preprocessed TRAINING design matrix (stored in
    the manifest companion `train_stats.json`).
    """
    clf = model.named_steps["clf"]
    classes = list(clf.classes_)
    names = expanded_feature_names(model)
    z = preprocessed(model, df_row)
    logits = clf.intercept_ + z @ clf.coef_.T
    proba = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    out = []
    for i in range(z.shape[0]):
        contrib = {c: OrderedDict() for c in classes}
        for k, c in enumerate(classes):
            for j, name in enumerate(names):
                contrib[c][name] = float(clf.coef_[k, j] * z[i, j])
        shap = {c: OrderedDict() for c in classes}
        for k, c in enumerate(classes):
            for j, name in enumerate(names):
                shap[c][name] = float(clf.coef_[k, j] * (z[i, j] - z_train_mean[j]))
        out.append(OrderedDict(
            classes=classes,
            probabilities={c: float(proba[i, k]) for k, c in enumerate(classes)},
            predicted_class=classes[int(np.argmax(proba[i]))],
            logits={c: float(logits[i, k]) for k, c in enumerate(classes)},
            intercepts={c: float(clf.intercept_[k]) for k, c in enumerate(classes)},
            contributions_log_odds=contrib,
            shap_values_log_odds=shap,
            shap_base_logits={c: float(clf.intercept_[k]
                                       + float(np.dot(clf.coef_[k], z_train_mean)))
                              for k, c in enumerate(classes)},
            feature_values_preprocessed={name: float(z[i, j])
                                         for j, name in enumerate(names)},
        ))
    return out


def permutation_importance(model, df, y, n_repeats=20, seed=20261112):
    """Permutation importance on held-out (OOF) rows: drop in macro-F1 and
    balanced accuracy when each RAW feature column is shuffled."""
    from sklearn.metrics import balanced_accuracy_score, f1_score
    classes = sorted(set(y))
    base_pred = model.predict(df)
    base_macro = f1_score(y, base_pred, average="macro", labels=classes,
                          zero_division=0)
    base_bal = balanced_accuracy_score(y, base_pred)
    rng = np.random.default_rng(seed)
    out = []
    for col in ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES:
        drops_macro, drops_bal = [], []
        for _ in range(n_repeats):
            shuffled = df.copy()
            shuffled[col] = rng.permutation(shuffled[col].to_numpy())
            pred = model.predict(shuffled)
            drops_macro.append(base_macro - f1_score(
                y, pred, average="macro", labels=classes, zero_division=0))
            drops_bal.append(base_bal - balanced_accuracy_score(y, pred))
        out.append(OrderedDict(
            feature=col,
            mean_drop_macro_f1=float(np.mean(drops_macro)),
            sd_drop_macro_f1=float(np.std(drops_macro, ddof=1)),
            mean_drop_balanced_accuracy=float(np.mean(drops_bal)),
            sd_drop_balanced_accuracy=float(np.std(drops_bal, ddof=1)),
            n_repeats=n_repeats))
    out.sort(key=lambda r: -r["mean_drop_macro_f1"])
    return out


def training_ranges(records):
    """Observed ranges/distributions of the RAW features over the training
    records (the model is refit on all 274 records, so these are the training
    ranges used for OOD detection)."""
    stats = OrderedDict()
    numeric = ["d0_mm", "pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf"]
    for col in numeric:
        vals = np.asarray([r[col] for r in records if r[col] is not None], float)
        stats[col] = OrderedDict(
            n=int(vals.size),
            min=float(vals.min()), max=float(vals.max()),
            p1=float(np.percentile(vals, 1)), p99=float(np.percentile(vals, 99)),
            median=float(np.median(vals)))
    cats = {}
    for col in ("fuel", "diluent_type"):
        cats[col] = sorted({r[col] for r in records})
    stats["_categoricals"] = cats
    # combination buckets: (diluent_type, pressure band, rounded O2)
    buckets = Counter()
    for r in records:
        if r["pressure_mmHg"] is None or r["o2_mf"] is None:
            key = (r["diluent_type"], "unknown", "unknown")
        else:
            key = (r["diluent_type"],
                   "<560" if r["pressure_mmHg"] < 560 else
                   ("560-800" if r["pressure_mmHg"] < 800 else ">=800"),
                   round(round(r["o2_mf"] / 0.02) * 0.02, 2))
        buckets[key] += 1
    stats["_combination_buckets"] = {str(k): int(v) for k, v in sorted(buckets.items())}
    return stats


def ood_check(conditions, stats):
    """Warnings for numerical out-of-range, unseen categorical, sparse
    combinations, and missing required inputs."""
    warnings = []
    missing = []
    numeric = ["d0_mm", "pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf"]
    for col in numeric:
        v = conditions.get(col)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            missing.append(col)
            continue
        s = stats[col]
        if v < s["min"] or v > s["max"]:
            warnings.append(OrderedDict(
                type="numeric_outside_training_range", feature=col, value=v,
                training_range=[s["min"], s["max"]],
                message=(f"{col}={v} lies outside the observed training range "
                         f"[{s['min']}, {s['max']}]; the model extrapolates "
                         "beyond its evidence and the prediction is unreliable")))
        elif v < s["p1"] or v > s["p99"]:
            warnings.append(OrderedDict(
                type="numeric_in_extreme_percentiles", feature=col, value=v,
                training_p1_p99=[s["p1"], s["p99"]],
                message=(f"{col}={v} lies within the training extremes but outside "
                         "the central 98% percentile band; prediction rests on very "
                         "few training records")))
    cats = stats["_categoricals"]
    for col in ("fuel", "diluent_type"):
        v = conditions.get(col)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        if v not in cats[col]:
            warnings.append(OrderedDict(
                type="unseen_categorical_value", feature=col, value=v,
                training_values=cats[col],
                message=(f"{col}={v!r} was never observed in training; the model "
                         "cannot predict for this value")))
    if missing:
        warnings.append(OrderedDict(
            type="missing_required_input", feature=", ".join(missing), value=None,
            training_range="",
            message=(f"missing input(s): {', '.join(missing)}; the model uses "
                     "median imputation with missingness indicators as fitted, "
                     "but the prediction should be treated as provisional")))
    # combination sparsity
    dil = conditions.get("diluent_type") or (
        "CO2+He" if (conditions.get("co2_mf") or 0) > 0 and (conditions.get("he_mf") or 0) > 0
        else "CO2" if (conditions.get("co2_mf") or 0) > 0
        else "He" if (conditions.get("he_mf") or 0) > 0 else "none")
    p = conditions.get("pressure_mmHg")
    o2 = conditions.get("o2_mf")
    if p is not None and o2 is not None:
        band = "<560" if p < 560 else ("560-800" if p < 800 else ">=800")
        key = (dil, band, round(round(o2 / 0.02) * 0.02, 2))
        n_bucket = stats["_combination_buckets"].get(str(key), 0)
        if n_bucket < 5:
            warnings.append(OrderedDict(
                type="sparse_condition_combination", feature="combination",
                value=str(key), training_range=f"{n_bucket} training records",
                message=(f"the condition combination {key} is represented by only "
                         f"{n_bucket} training records; predictions in this region "
                         "are weakly supported")))
    return warnings, missing
