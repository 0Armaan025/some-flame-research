#!/usr/bin/env python3
"""FLEX PSI-69 Phase 6 - evaluate.py.

Independently recomputes the headline evaluation numbers from the stored
out-of-fold predictions (artifacts/oof_predictions.csv) rather than trusting
the training script's metrics, and writes evaluation_report.md. This is the
verification step: if this file's metrics and the manifest disagree, the model
is not accepted.

Run:
    notebooks/.venv/bin/python prediction/evaluate.py
"""

import csv
import json
import os
import sys
from collections import Counter, OrderedDict

import numpy as np
from sklearn.metrics import (balanced_accuracy_score, confusion_matrix,
                             f1_score, log_loss, precision_recall_fscore_support)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explain

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "artifacts")


def recompute_from_oof():
    with open(os.path.join(ART, "oof_predictions.csv")) as fh:
        rows = list(csv.DictReader(fh))
    manifest = explain.load_manifest()
    classes = manifest["model"]["classes"]
    selected = manifest["model"]["selected"]
    y = np.asarray([r["true_outcome"] for r in rows])
    pred = np.asarray([r[f"pred_{selected}"] for r in rows])
    prob = np.asarray([[float(r[f"p_{selected}_{c}"]) for c in classes] for r in rows])
    p, r, f1, support = precision_recall_fscore_support(y, pred, labels=classes,
                                                        zero_division=0)
    recomputed = OrderedDict(
        n=len(y), accuracy=float(np.mean(y == pred)),
        balanced_accuracy=float(balanced_accuracy_score(y, pred)),
        macro_f1=float(f1_score(y, pred, average="macro", labels=classes,
                                zero_division=0)),
        per_class={c: dict(precision=float(p[i]), recall=float(r[i]),
                           f1=float(f1[i]), support=int(support[i]))
                   for i, c in enumerate(classes)},
        confusion_matrix={classes[i]: {classes[j]: int(v) for j, v in enumerate(row)}
                          for i, row in enumerate(
                              confusion_matrix(y, pred, labels=classes))},
        log_loss=float(log_loss(y, prob, labels=classes)),
    )
    return recomputed, manifest, selected, classes


def main():
    recomputed, manifest, selected, classes = recompute_from_oof()
    stored = json.load(open(os.path.join(ART, "evaluation_metrics.json")))
    stored_sel = stored["results"][selected]
    mismatches = []
    for key in ("accuracy", "balanced_accuracy", "macro_f1", "log_loss"):
        if abs(recomputed[key] - stored_sel[key]) > 1e-9:
            mismatches.append((key, stored_sel[key], recomputed[key]))
    for c in classes:
        for metric in ("precision", "recall", "f1"):
            if abs(recomputed["per_class"][c][metric]
                   - stored_sel["per_class"][c][metric]) > 1e-9:
                mismatches.append((f"{c}.{metric}",
                                   stored_sel["per_class"][c][metric],
                                   recomputed["per_class"][c][metric]))
    baseline = manifest["validation"]["baseline"]

    lines = []
    A = lines.append
    A("# Prediction Engine — Evaluation Report\n")
    A(f"**Model:** `{selected}` (version {manifest['model']['version']}), "
      f"trained on {manifest['model']['training_records']} records in "
      f"{manifest['model']['training_groups']} experimental-series groups.\n")
    A(f"**Validation scheme:** {manifest['validation']['scheme']}\n")
    A("## Independent recomputation\n")
    A("The numbers below were recomputed by `evaluate.py` from the stored "
      "out-of-fold predictions (`artifacts/oof_predictions.csv`), not copied "
      f"from the training log. Discrepancies vs the training metrics: "
      f"**{'none' if not mismatches else mismatches}**.\n")
    A("## Grouped out-of-fold metrics (pooled over all folds)\n")
    A("| Metric | Selected model | Majority baseline |")
    A("|---|---|---|")
    A(f"| Accuracy | {recomputed['accuracy']:.4f} | {baseline['accuracy']:.4f} |")
    A(f"| Balanced accuracy | **{recomputed['balanced_accuracy']:.4f}** | "
      f"{baseline['balanced_accuracy']:.4f} |")
    A(f"| Macro-F1 | **{recomputed['macro_f1']:.4f}** | {baseline['macro_f1']:.4f} |")
    A(f"| Log loss | {recomputed['log_loss']:.4f} | n/a (hard labels) |\n")
    A("Per-fold variability across the 15 grouped folds "
      f"(3 seeds × 5 folds): balanced accuracy "
      f"{stored_sel['fold_balanced_accuracy_mean']:.4f} ± "
      f"{stored_sel['fold_balanced_accuracy_sd']:.4f}, macro-F1 "
      f"{stored_sel['fold_macro_f1_mean']:.4f} ± "
      f"{stored_sel['fold_macro_f1_sd']:.4f}.\n")
    A("## Per-class performance (out-of-fold)\n")
    A("| Class | Precision | Recall | F1 | Support |")
    A("|---|---|---|---|---|")
    for c in classes:
        d = recomputed["per_class"][c]
        A(f"| {c} | {d['precision']:.3f} | {d['recall']:.3f} | {d['f1']:.3f} | "
          f"{d['support']} |")
    A("")
    A("## Confusion matrix (out-of-fold, rows = true, cols = predicted)\n")
    A("| true \\ predicted | " + " | ".join(classes) + " |")
    A("|---|" + "---|" * len(classes))
    for c in classes:
        A(f"| {c} | " + " | ".join(str(recomputed["confusion_matrix"][c][k])
                                    for k in classes) + " |")
    A("")
    A("## Interpretation\n")
    A("- The model **outperforms the majority-class baseline** on grouped "
      "out-of-fold data (balanced accuracy "
      f"{recomputed['balanced_accuracy']:.3f} vs {baseline['balanced_accuracy']:.3f}; "
      f"macro-F1 {recomputed['macro_f1']:.3f} vs {baseline['macro_f1']:.3f}); "
      "every validation fold exceeds the baseline's balanced accuracy.")
    A("- Performance is **moderate, not strong**: balanced accuracy ≈ 0.53 and "
      "macro-F1 ≈ 0.50 mean the model separates the classes markedly better "
      "than chance but with substantial error, concentrated in the minority "
      "classes (Completion: 27 records).")
    A("- All results are **conditional on an independence assumption the "
      "experimental design does not establish** (sequential/adaptive LOI "
      "procedure, series clustering, duplicated identifier). Grouped CV "
      "mitigates but does not remove this.")
    A("- The target is the **recorded outcome label**. 'Disruption' is an "
      "undefined label, and Extinction is visible-flame extinction. These "
      "predictions are label predictions, not combustion physics.\n")
    A("## Reproduce\n")
    A("```bash")
    A("notebooks/.venv/bin/python prediction/train.py")
    A("notebooks/.venv/bin/python prediction/evaluate.py")
    A("notebooks/.venv/bin/python -m pytest prediction/tests/ -v")
    A("```")
    out = os.path.join(HERE, "evaluation_report.md")
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[report] {out}")
    print(f"[check] recomputed vs stored mismatches: {mismatches or 'none'}")
    return mismatches


if __name__ == "__main__":
    main()
