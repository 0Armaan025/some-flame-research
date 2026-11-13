#!/usr/bin/env python3
"""FLEX PSI-69 Phase 6 - train.py.

Trains and evaluates recorded-outcome prediction models with GROUP-AWARE
validation (experimental series as groups), selects a model only if it beats
the majority-class baseline on the grouped out-of-fold predictions, serialises
the winner and writes model_manifest.json.

Run from the repository root:
    notebooks/.venv/bin/python prediction/train.py

No raw data is modified; the raw file's sha256 is verified before training.
"""

import csv
import datetime
import hashlib
import json
import os
import platform
import sys
from collections import Counter, OrderedDict

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (balanced_accuracy_score, brier_score_loss,
                             classification_report, confusion_matrix,
                             log_loss, precision_recall_fscore_support)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flex_features as ff

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")
MODEL_VERSION = "6.0.0"
N_SPLITS = 5
SEEDS = (20261112, 20261113, 20261114)  # 3 grouped-CV repeats for variability


def build_pipeline(kind):
    numeric = list(ff.NUMERIC_FEATURES)
    categorical = list(ff.CATEGORICAL_FEATURES)
    num_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    cat_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent", add_indicator=True)),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    pre = ColumnTransformer([
        ("num", num_pipe, numeric),
        ("cat", cat_pipe, categorical),
    ])
    if kind == "majority":
        clf = DummyClassifier(strategy="most_frequent")
        return Pipeline([("pre", pre), ("clf", clf)])
    if kind == "logreg":
        clf = LogisticRegression(max_iter=5000, C=1.0, solver="lbfgs")
    elif kind == "logreg_balanced":
        clf = LogisticRegression(max_iter=5000, C=1.0, solver="lbfgs",
                                 class_weight="balanced")
    elif kind == "tree3":
        clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=10,
                                     class_weight="balanced", random_state=0)
    else:
        raise ValueError(kind)
    return Pipeline([("pre", pre), ("clf", clf)])


def grouped_oof(kind, df, groups, labels):
    """Out-of-fold predictions with series-grouped CV; returns per-fold records
    and pooled OOF probabilities."""
    classes = sorted(set(labels))
    n = len(labels)
    oof_prob = np.full((n, len(classes)), np.nan)
    oof_pred = np.full(n, "", dtype=object)
    fold_rows = []
    for seed in SEEDS:
        gkf = GroupKFold(n_splits=N_SPLITS)
        if seed == SEEDS[0]:
            iterator = [(tr, te) for tr, te in gkf.split(np.zeros(n), labels, groups=groups)]
        else:
            # later seeds reshuffle the assignment of GROUPS to folds only;
            # rows are never randomly split across train/test
            rng = np.random.default_rng(seed)
            uniq = sorted(set(groups))
            perm = rng.permutation(uniq)
            fold_of = {g: i % N_SPLITS for i, g in enumerate(perm)}
            iterator = []
            for f in range(N_SPLITS):
                te = np.asarray([fold_of[g] == f for g in groups])
                iterator.append((np.where(~te)[0], np.where(te)[0]))
        for k, (tr, te) in enumerate(iterator):
            pipe = build_pipeline(kind)
            pipe.fit(df.iloc[tr], labels[tr])
            proba = pipe.predict_proba(df.iloc[te])
            pred = pipe.classes_[np.argmax(proba, axis=1)]
            oof_prob[te] = proba
            oof_pred[te] = pred
            fold_rows.append(dict(
                seed=seed, fold=k, n_train=len(tr), n_test=len(te),
                n_train_groups=len(set(groups[tr])),
                n_test_groups=len(set(groups[te])),
                balanced_accuracy=float(balanced_accuracy_score(labels[te], pred)),
                macro_f1=float(precision_recall_fscore_support(
                    labels[te], pred, average="macro", zero_division=0)[2]),
                log_loss=float(log_loss(labels[te], proba, labels=classes)),
            ))
            # majority baseline computed from TRAIN labels, applied to test
            maj = Counter(labels[tr]).most_common(1)[0][0]
            fold_rows[-1]["majority_baseline_balanced_accuracy"] = float(
                balanced_accuracy_score(labels[te], np.asarray([maj] * len(te))))
    return classes, oof_prob, oof_pred, fold_rows


def pooled_metrics(labels, classes, oof_prob, oof_pred):
    y = np.asarray(labels)
    p, r, f1, support = precision_recall_fscore_support(
        y, oof_pred, labels=classes, zero_division=0)
    cm = confusion_matrix(y, oof_pred, labels=classes)
    metrics = OrderedDict(
        n=len(y),
        accuracy=float(np.mean(y == oof_pred)),
        balanced_accuracy=float(balanced_accuracy_score(y, oof_pred)),
        macro_f1=float(f1.mean()),
        weighted_f1=float(np.average(f1, weights=support)),
        per_class={c: OrderedDict(precision=float(p[i]), recall=float(r[i]),
                                  f1=float(f1[i]), support=int(support[i]))
                   for i, c in enumerate(classes)},
        confusion={classes[i]: {classes[j]: int(cm[i, j]) for j in range(len(classes))}
                   for i in range(len(classes))},
        log_loss=float(log_loss(y, oof_prob, labels=classes)),
    )
    # per-class Brier score (mean squared error of the class probability)
    brier = {}
    for i, c in enumerate(classes):
        yb = (y == c).astype(int)
        brier[c] = float(np.mean((oof_prob[:, i] - yb) ** 2))
    metrics["brier_per_class"] = brier
    return metrics


def _training_ranges(records):
    sys.path.insert(0, HERE)
    import explain
    return explain.training_ranges(records)


def majority_oof_baseline(groups, labels, classes, seeds=SEEDS):
    """Out-of-fold majority-class baseline with the identical grouped splits."""
    n = len(labels)
    preds = np.full(n, "", dtype=object)
    uniq_all = sorted(set(groups))
    for seed in seeds:
        rng = np.random.default_rng(seed)
        perm = rng.permutation(uniq_all)
        fold_of = {g: i % N_SPLITS for i, g in enumerate(perm)}
        for f in range(N_SPLITS):
            te = np.asarray([fold_of[g] == f for g in groups])
            tr = ~te
            maj = Counter(np.asarray(labels)[tr]).most_common(1)[0][0]
            preds[te] = maj
    return preds


def main():
    path = ff.raw_csv_path()
    digest = ff.sha256_of(path)
    if digest != ff.RAW_SHA256:
        raise SystemExit(f"raw dataset changed: {digest}")
    print(f"[input] {os.path.relpath(path, ff.ROOT)} sha256={digest} (match)")

    records = ff.load_dataset(path)
    cols, groups, labels, ids = ff.to_matrix(records)
    df = pd.DataFrame({c: cols[c] for c in ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES})
    labels = np.asarray(labels)
    classes = sorted(set(labels))
    print(f"[data] {len(records)} records; classes {classes}; "
          f"groups(series)={len(set(groups))}")

    results = {}
    oof_by_kind = {}
    for kind in ("majority", "logreg", "logreg_balanced", "tree3"):
        cls_, prob, pred, folds = grouped_oof(kind, df, groups, labels)
        assert np.isfinite(prob).all(), f"missing OOF predictions for {kind}"
        oof_by_kind[kind] = (cls_, prob, pred, folds)
        met = pooled_metrics(labels, cls_, prob, pred)
        met["fold_metrics"] = folds
        met["fold_balanced_accuracy_mean"] = float(np.mean(
            [f["balanced_accuracy"] for f in folds]))
        met["fold_balanced_accuracy_sd"] = float(np.std(
            [f["balanced_accuracy"] for f in folds], ddof=1))
        met["fold_macro_f1_mean"] = float(np.mean([f["macro_f1"] for f in folds]))
        met["fold_macro_f1_sd"] = float(np.std([f["macro_f1"] for f in folds], ddof=1))
        results[kind] = met
        print(f"[cv] {kind:16s} OOF balanced_acc={met['balanced_accuracy']:.4f} "
              f"macro_f1={met['macro_f1']:.4f} "
              f"fold_ba={met['fold_balanced_accuracy_mean']:.4f}"
              f"±{met['fold_balanced_accuracy_sd']:.4f}")

    base_maj = majority_oof_baseline(groups, labels, classes)
    baseline = OrderedDict(
        accuracy=float(np.mean(np.asarray(labels) == base_maj)),
        balanced_accuracy=float(balanced_accuracy_score(labels, base_maj)),
        macro_f1=float(precision_recall_fscore_support(
            labels, base_maj, average="macro", zero_division=0)[2]),
    )
    print(f"[baseline] majority-class OOF acc={baseline['accuracy']:.4f} "
          f"bal_acc={baseline['balanced_accuracy']:.4f} "
          f"macro_f1={baseline['macro_f1']:.4f}")

    # selection: only beat the baseline on BOTH grouped-OOF balanced accuracy
    # and macro F1, with every fold's balanced accuracy above the baseline's.
    candidates = {k: v for k, v in results.items() if k != "majority"}
    best_kind, best = None, None
    for k, v in candidates.items():
        beats = (v["balanced_accuracy"] > baseline["balanced_accuracy"]
                 and v["macro_f1"] > baseline["macro_f1"]
                 and min(f["balanced_accuracy"] for f in v["fold_metrics"])
                 > baseline["balanced_accuracy"])
        print(f"[select] {k}: beats_baseline_on_grouped_oof={beats}")
        # documented selection rule: primary = grouped-OOF balanced accuracy
        # (classes are imbalanced 186/61/27), tie-break = macro F1.
        if beats and (best is None
                      or v["balanced_accuracy"] > best["balanced_accuracy"] + 1e-9
                      or (abs(v["balanced_accuracy"] - best["balanced_accuracy"]) <= 1e-9
                          and v["macro_f1"] > best["macro_f1"])):
            best_kind, best = k, v
    selected = best_kind is not None
    print(f"[select] selected={'%s' % best_kind if selected else 'NONE (baseline only)'}")

    # refit the selected model on all records (documented) and serialise
    if selected:
        final = build_pipeline(best_kind)
        final.fit(df, labels)
        model_path = os.path.join(ART, "outcome_model.joblib")
        joblib.dump(final, model_path)
        pre = final.named_steps["pre"]
        imp = pre.named_transformers_["num"].named_steps["impute"]
        ohe = pre.named_transformers_["cat"].named_steps["onehot"]
        cat_names = list(ohe.get_feature_names_out(ff.CATEGORICAL_FEATURES))
        feature_names = [f"num:{c}" for c in ff.NUMERIC_FEATURES]
        if imp.indicator_ is not None:
            feature_names += [f"num:{ff.NUMERIC_FEATURES[j]}_MISSING"
                              for j in imp.indicator_.features_]
        feature_names += [f"cat:{n}" for n in cat_names]
        width = pre.transform(df.iloc[:2]).shape[1]
        assert len(feature_names) == width, (len(feature_names), width)
    else:
        model_path = None
        feature_names = None

    os.makedirs(ART, exist_ok=True)
    with open(os.path.join(ART, "oof_predictions.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        header = ["flex_test_no", "series", "true_outcome"]
        for k in results:
            header.append(f"pred_{k}")
        for k in results:
            header += [f"p_{k}_{c}" for c in classes]
        w.writerow(header)
        for i, rec in enumerate(records):
            row = [rec["flex_test_no"], rec["series"], labels[i]]
            for k, (cls_k, prob_k, pred_k, _f) in oof_by_kind.items():
                row.append(pred_k[i] if k != "majority" else base_maj[i])
            for k, (cls_k, prob_k, pred_k, _f) in oof_by_kind.items():
                if k == "majority":
                    row += [1.0 if base_maj[i] == c else 0.0 for c in classes]
                else:
                    row += [float(prob_k[i][classes.index(c)]) for c in classes]
            w.writerow(row)

    manifest = OrderedDict(
        model=dict(
            version=MODEL_VERSION,
            selected=best_kind,
            selected_usable=selected,
            artifact=os.path.relpath(model_path, ff.ROOT) if model_path else None,
            classes=classes,
            features=list(ff.NUMERIC_FEATURES) + list(ff.CATEGORICAL_FEATURES),
            expanded_feature_names=feature_names,
            training_records=len(records),
            training_groups=len(set(groups)),
        ),
        validation=OrderedDict(
            scheme=f"GroupKFold(n_splits={N_SPLITS}) over experimental-series "
                   "prefixes, 3 seeds; out-of-fold pooling",
            seeds=list(SEEDS),
            baseline=baseline,
            oof_metrics={k: v for k, v in results.items()},
        ),
        input=dict(path=os.path.relpath(path, ff.ROOT), sha256=digest),
        executed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(),
                         numpy=np.__version__, sklearn=__import__("sklearn").__version__),
        restrictions=dict(
            no_burning_rate_feature=True,
            no_post_outcome_features=True,
            no_imputation_of_raw_data=True,
            pressure_zero_treated_as_missing=True,
            causal_claims="none - associations only"),
    )
    if selected:
        manifest["model"]["artifact_sha256"] = ff.sha256_of(model_path)
        manifest["validation"]["oof_metrics"][best_kind]["selected_reason"] = (
            "beats grouped-OOF majority baseline on balanced accuracy and macro F1, "
            "every fold above the baseline, and highest grouped-OOF balanced accuracy "
            "among the candidates (primary criterion; macro F1 as tie-break)")
    if selected:
        # persist the training design-matrix mean (needed for exact linear
        # SHAP) and the raw-feature ranges (needed for OOD detection)
        z_train_mean = final.named_steps["pre"].transform(df).mean(axis=0)
        stats = dict(
            z_train_mean=[float(v) for v in z_train_mean],
            raw_ranges=_training_ranges(records),
        )
        with open(os.path.join(ART, "train_stats.json"), "w") as fh:
            json.dump(stats, fh)
    with open(os.path.join(ART, "model_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    # also expose metrics for evaluate.py
    payload = dict(results={k: {kk: vv for kk, vv in v.items()
                                if not kk.startswith("_")} for k, v in results.items()},
                   baseline=baseline, classes=classes,
                   selected=best_kind, selected_usable=selected)
    with open(os.path.join(ART, "evaluation_metrics.json"), "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"[artifacts] {ART}")


if __name__ == "__main__":
    main()
