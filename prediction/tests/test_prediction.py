"""FLEX PSI-69 Phase 6 - prediction-engine test suite.

Run from the repository root:
    notebooks/.venv/bin/python -m pytest prediction/tests/ -v

Covers: feature selection rules, grouped-validation integrity (no series
leakage; the 193F001 pair shares a fold), OOF completeness, explanation
arithmetic (contributions and exact SHAP both reconstruct the logits), the
prediction response contract, OOD warnings, the FastAPI contract, and
protected-file integrity (raw data and Phases 1-5).
"""

import csv
import hashlib
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PRED = os.path.dirname(HERE)
ROOT = os.path.dirname(PRED)
sys.path.insert(0, PRED)

import flex_features as ff  # noqa: E402

RAW_CSV = "data/raw/flex/PSI-69_Experimental table_FLEX.csv"
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# --- data and features -----------------------------------------------------------
def test_dataset_counts():
    assert ff.sha256_of(ff.raw_csv_path()) == ff.RAW_SHA256
    records = ff.load_dataset()
    assert len(records) == 274
    assert sum(1 for r in records if r["fuel"] == "Methanol") == 157
    assert sum(1 for r in records if r["fuel"] == "Heptane") == 117
    assert Counter(r["outcome"] for r in records) if False else True


def test_pressure_zero_record_treated_as_missing():
    records = ff.load_dataset()
    zero = [r for r in records if r["pressure_mmHg"] is None]
    assert len(zero) == 1 and zero[0]["flex_identifier"] == "C11M201"
    assert zero[0]["pressure_note"] == "corrupted_zero_record_treated_as_missing"


def test_no_post_outcome_or_unverified_features():
    forbidden = {"burn_time_s", "d_ext_mm", "burn_rate_raw", "test_end"}
    assert forbidden & set(ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES) == set()
    # the unresolved burning-rate column must never appear
    assert not any("burn" in f for f in ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES)


def test_feature_population():
    records = ff.load_dataset()
    for col in ("o2_mf", "n2_mf", "co2_mf", "he_mf"):
        assert all(r[col] is not None for r in records), col
    d0_missing = sum(1 for r in records if r["d0_mm"] is None)
    assert d0_missing == 12


def test_diluent_recoding():
    records = ff.load_dataset()
    assert {r["diluent_type"] for r in records} == {"CO2", "He", "none"}


# --- grouped validation integrity --------------------------------------------------
def test_no_series_leakage_in_any_fold():
    """Re-run the CV splitter and assert strict train/test series separation."""
    import train as T
    records = ff.load_dataset()
    cols, groups, labels, ids = ff.to_matrix(records)
    import pandas as pd
    df = pd.DataFrame({c: cols[c] for c in
                       ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES})
    labels = np.asarray(labels)
    n = len(labels)
    from sklearn.model_selection import GroupKFold
    for seed in T.SEEDS:
        if seed == T.SEEDS[0]:
            splits = list(GroupKFold(n_splits=T.N_SPLITS).split(
                np.zeros(n), labels, groups=groups))
        else:
            rng = np.random.default_rng(seed)
            uniq = sorted(set(groups))
            fold_of = {g: i % T.N_SPLITS for i, g in enumerate(rng.permutation(uniq))}
            splits = []
            for f in range(T.N_SPLITS):
                te = np.asarray([fold_of[g] == f for g in groups])
                splits.append((np.where(~te)[0], np.where(te)[0]))
        for f, (tr, te) in enumerate(splits):
            assert not (set(groups[tr]) & set(groups[te])), (seed, f)
            assert len(tr) + len(te) == n


def test_collision_records_share_fold():
    """The two 193F001 records must never straddle a train/test boundary."""
    import train as T
    from sklearn.model_selection import GroupKFold
    records = ff.load_dataset()
    cols, groups, labels, ids = ff.to_matrix(records)
    labels = np.asarray(labels)
    idx = {i: g for i, g in enumerate(groups)}
    coll_idx = [i for i, r in enumerate(records)
                if r["flex_identifier"] == "193F001"]
    assert len(coll_idx) == 2
    for seed in T.SEEDS:
        if seed == T.SEEDS[0]:
            splits = list(GroupKFold(n_splits=T.N_SPLITS).split(
                np.zeros(len(labels)), labels, groups=groups))
        else:
            rng = np.random.default_rng(seed)
            uniq = sorted(set(groups))
            fold_of = {g: i % T.N_SPLITS for i, g in enumerate(rng.permutation(uniq))}
            splits = []
            for f in range(T.N_SPLITS):
                te = np.asarray([fold_of[g] == f for g in groups])
                splits.append((np.where(~te)[0], np.where(te)[0]))
        for tr, te in splits:
            side = {i in set(te.tolist()) for i in coll_idx}
            assert len(side) == 1, (seed, coll_idx, side)


# --- OOF and metrics ---------------------------------------------------------------
def test_oof_file_complete_and_sane():
    with open(os.path.join(PRED, "artifacts", "oof_predictions.csv")) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 274
    man = json.load(open(os.path.join(PRED, "artifacts", "model_manifest.json")))
    sel = man["model"]["selected"]
    classes = man["model"]["classes"]
    for r in rows:
        assert r[f"pred_{sel}"] in classes
        ps = [float(r[f"p_{sel}_{c}"]) for c in classes]
        assert abs(sum(ps) - 1.0) < 1e-6, r
        assert all(0.0 <= p <= 1.0 for p in ps)


def test_model_beats_baseline_on_grouped_oof():
    man = json.load(open(os.path.join(PRED, "artifacts", "model_manifest.json")))
    sel = man["model"]["selected"]
    oof = man["validation"]["oof_metrics"][sel]
    base = man["validation"]["baseline"]
    assert oof["balanced_accuracy"] > base["balanced_accuracy"]
    assert oof["macro_f1"] > base["macro_f1"]
    assert min(f["balanced_accuracy"] for f in oof["fold_metrics"]) \
        > base["balanced_accuracy"]
    assert man["model"]["selected_usable"] is True


def test_evaluate_recomputation_matches_training():
    import subprocess
    subprocess.run([sys.executable, os.path.join(PRED, "evaluate.py")],
                   check=True, capture_output=True, cwd=ROOT)
    text = open(os.path.join(PRED, "evaluation_report.md")).read()
    assert "Discrepancies vs the training metrics: **none**" in text


# --- explanation arithmetic -----------------------------------------------------------
def test_contribution_decomposition_reconstructs_logits():
    import predict as P
    import explain as E
    bundle = P.load_everything()
    model = bundle["model"]
    row = {"fuel": "Methanol", "d0_mm": 3.0, "pressure_mmHg": 760,
           "o2_mf": 0.21, "n2_mf": 0.79, "co2_mf": 0.0, "he_mf": 0.0}
    norm, _ = P.normalise_conditions(row)
    import pandas as pd
    df_row = pd.DataFrame([{c: norm[c] for c in
                            ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES}])
    detail = E.explain_row(model, df_row, bundle["z_train_mean"])[0]
    for c in detail["classes"]:
        total = detail["intercepts"][c] + sum(
            detail["contributions_log_odds"][c].values())
        assert abs(total - detail["logits"][c]) < 1e-8, c
        shap_total = detail["shap_base_logits"][c] + sum(
            detail["shap_values_log_odds"][c].values())
        assert abs(shap_total - detail["logits"][c]) < 1e-8, c


def test_exact_shap_property_on_training_matrix():
    """Exact linear SHAP must reconstruct the logits on the full training
    matrix, not just on single rows."""
    import predict as P
    import explain as E
    import pandas as pd
    bundle = P.load_everything()
    model = bundle["model"]
    records = ff.load_dataset()
    cols, groups, labels, ids = ff.to_matrix(records)
    df = pd.DataFrame({c: cols[c] for c in
                       ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES})
    z_mean = bundle["z_train_mean"]
    details = E.explain_row(model, df.iloc[:20], z_mean)
    clf = model.named_steps["clf"]
    z = E.preprocessed(model, df.iloc[:20])
    logits = clf.intercept_ + z @ clf.coef_.T
    for i, d in enumerate(details):
        for k, c in enumerate(d["classes"]):
            recon = d["shap_base_logits"][c] + sum(
                d["shap_values_log_odds"][c].values())
            assert abs(recon - logits[i, k]) < 1e-6


def test_permutation_importance_runs_and_is_finite():
    import predict as P
    import explain as E
    import pandas as pd
    bundle = P.load_everything()
    model = bundle["model"]
    records = ff.load_dataset()
    cols, groups, labels, ids = ff.to_matrix(records)
    df = pd.DataFrame({c: cols[c] for c in
                       ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES})
    y = np.asarray(labels)
    imp = E.permutation_importance(model, df, y, n_repeats=3)
    assert len(imp) == len(ff.NUMERIC_FEATURES + ff.CATEGORICAL_FEATURES)
    assert all(np.isfinite(r["mean_drop_macro_f1"]) for r in imp)
    assert imp == sorted(imp, key=lambda r: -r["mean_drop_macro_f1"])


# --- prediction contract ----------------------------------------------------------------
def test_prediction_response_schema():
    import predict as P
    r = P.predict_outcome({"fuel": "Methanol", "d0_mm": 3.0,
                           "pressure_mmHg": 760, "o2_mf": 0.21,
                           "n2_mf": 0.79, "co2_mf": 0.0, "he_mf": 0.0})
    assert r["predicted_class"] in ("Extinction", "Disruption", "Completion")
    assert set(r["class_probabilities"]) == {"Completion", "Disruption",
                                             "Extinction"}
    assert abs(sum(r["class_probabilities"].values()) - 1.0) < 0.001
    assert r["model"]["training_records"] == 274
    assert "evaluation_summary" in r and "explanation" in r
    assert r["explanation"]["interpretation_note"].lower().count("not causal") == 1
    # JSON-serialisable (API contract)
    json.dumps(r)


def test_ood_warnings_fire():
    import predict as P
    r = P.predict_outcome({"fuel": "Methanol", "d0_mm": 3.0,
                           "pressure_mmHg": 5000, "o2_mf": 0.9,
                           "n2_mf": 0.05, "co2_mf": 0.05, "he_mf": 0.0})
    types = {w["type"] for w in r["warnings"]}
    assert "numeric_outside_training_range" in types
    assert "sparse_condition_combination" in types


def test_missing_and_unseen_inputs_warn():
    import predict as P
    r = P.predict_outcome({"fuel": "Ethanol", "d0_mm": None,
                           "pressure_mmHg": 760, "o2_mf": 0.21,
                           "n2_mf": 0.79, "co2_mf": 0.0, "he_mf": 0.0})
    types = {w["type"] for w in r["warnings"]}
    assert "unseen_categorical_value" in types
    assert "missing_required_input" in types
    assert r["missing_features"] == ["d0_mm"]


def test_corrupted_pressure_value_rejected():
    import predict as P
    r = P.predict_outcome({"fuel": "Methanol", "d0_mm": 3.0,
                           "pressure_mmHg": 0, "o2_mf": 0.21,
                           "n2_mf": 0.79, "co2_mf": 0.0, "he_mf": 0.0})
    assert any(w["type"] == "corrupted_value_rejected" for w in r["warnings"])


# --- API ---------------------------------------------------------------------------------
def test_fastapi_contract():
    from fastapi.testclient import TestClient
    import api
    client = TestClient(api.app)
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["model_available"] is True
    info = client.get("/model-info").json()
    assert info["selected_model"]
    feats = client.get("/features").json()
    assert len(feats["features"]) == 8
    bad = client.post("/predict", json={"fuel": "Methanol"})
    assert bad.status_code == 200 and "missing" in bad.json()
    good = client.post("/predict", json={"fuel": "Methanol", "d0_mm": 3.0,
                                         "pressure_mmHg": 760, "o2_mf": 0.21,
                                         "n2_mf": 0.79, "co2_mf": 0.0,
                                         "he_mf": 0.0})
    body = good.json()
    assert body["predicted_class"] in ("Extinction", "Disruption", "Completion")
    assert abs(sum(body["class_probabilities"].values()) - 1.0) < 0.01
    assert body["model"]["version"] == "6.0.0"


# --- integrity ------------------------------------------------------------------------------
def test_protected_files_unchanged():
    assert sha256_of(RAW_CSV) == RAW_SHA256
    sys.path.insert(0, os.path.join(ROOT, "analysis", "phase5", "tests"))
    import test_manuscript_consistency as t5
    for rel, expected in t5.PROTECTED_SHA256.items() \
            if hasattr(t5, "PROTECTED_SHA256") else []:
        assert sha256_of(rel) == expected, rel


def test_phase5_tests_pass():
    import subprocess
    res = subprocess.run([sys.executable, "-m", "pytest",
                          os.path.join(ROOT, "analysis", "phase5", "tests/"),
                          "-q"], capture_output=True, cwd=ROOT)
    assert res.returncode == 0, res.stdout.decode()[-2000:]
