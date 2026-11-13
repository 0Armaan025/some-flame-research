"""FLEX PSI-69 Phase 6 - feature engineering and data loading for the
recorded-outcome prediction engine.

Integrity rules inherited from the frozen research phases:

* raw values are read verbatim (latin-1; 0x96 = missing marker; ~ = approximate);
* the corrupted 0 mmHg pressure record is treated as MISSING (documented
  decision), not as 0 and not as an imputed value;
* the unresolved burning-rate column is never a feature;
* no post-outcome quantity (burn time, extinction diameter) is ever a feature;
* experimental series (identifier prefix) is used ONLY as a grouping variable
  for validation, never as a model input.
"""

import csv
import glob
import os
import re
from collections import OrderedDict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATTERN = os.path.join("data", "raw", "flex", "PSI-69*FLEX.csv")
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"
MISSING_BYTE = "\x96"
OUTCOMES = ("Extinction", "Disruption", "Completion")
FUELS = ("Methanol", "Heptane")

# The final pre-outcome feature set (see feature_selection.md for justification).
NUMERIC_FEATURES = ("d0_mm", "pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf")
CATEGORICAL_FEATURES = ("fuel", "diluent_type")


def series_prefix(ident):
    m = re.match(r"^([0-9A-Z]*?)[A-Z]?[0-9]+$", ident)
    return m.group(1) if m else ident


def is_missing(raw):
    return raw is None or raw.strip() in ("", MISSING_BYTE)


def parse_measured(raw):
    if is_missing(raw):
        return None
    s = raw.strip()
    if s.startswith("~"):
        s = s.lstrip("~").strip()
    try:
        return float(s)
    except ValueError:
        return None


def raw_csv_path():
    return glob.glob(os.path.join(ROOT, RAW_PATTERN))[0]


def sha256_of(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_dataset(path=None):
    """Return a list of dicts: model features + label + grouping + provenance."""
    path = path or raw_csv_path()
    with open(path, newline="", encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        pressure_raw = r["Ambient pressure; mmHg"].strip()
        pressure = parse_measured(pressure_raw)
        # documented decision: 0 mmHg is a corrupted transcription (Phase 3.5
        # anomaly resolution), so it is treated as missing, never used as 0.
        if pressure == 0.0:
            pressure = None
            pressure_note = "corrupted_zero_record_treated_as_missing"
        else:
            pressure_note = ""
        co2 = parse_measured(r["CO initial ambient composition; mole fraction"])
        he = parse_measured(r["He initial ambient composition; mole fraction"])
        diluent = "CO2+He" if (co2 or 0) > 0 and (he or 0) > 0 else \
                  ("CO2" if (co2 or 0) > 0 else ("He" if (he or 0) > 0 else "none"))
        rec = OrderedDict(
            flex_test_no=r["FLEX Test #"].strip(),
            flex_identifier=r["FLEX Identifier"].strip(),
            series=series_prefix(r["FLEX Identifier"].strip()),
            fuel=r["Fuel"].strip(),
            d0_mm=parse_measured(r["Droplet initial diameter; mm"]),
            pressure_mmHg=pressure,
            o2_mf=parse_measured(r["O initial ambient composition; mole fraction"]),
            n2_mf=parse_measured(r["N initial ambient composition; mole fraction"]),
            co2_mf=co2,
            he_mf=he,
            diluent_type=diluent,
            outcome=r["Test end"].strip(),
            pressure_note=pressure_note,
        )
        out.append(rec)
    return out


def to_matrix(records):
    """Convert to a plain dict of column arrays for sklearn."""
    cols = {k: [] for k in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
    groups, labels, ids = [], [], []
    for r in records:
        for k in NUMERIC_FEATURES:
            cols[k].append(np.nan if r[k] is None else float(r[k]))
        for k in CATEGORICAL_FEATURES:
            cols[k].append(str(r[k]))
        groups.append(r["series"])
        labels.append(r["outcome"])
        ids.append(r["flex_test_no"])
    return cols, np.asarray(groups), np.asarray(labels), ids


FEATURE_LABELS = {
    "fuel": "Fuel (categorical)",
    "d0_mm": "Initial droplet diameter (mm, measured)",
    "pressure_mmHg": "Ambient pressure (mmHg; 0 mmHg record treated as missing)",
    "o2_mf": "O2 initial mole fraction",
    "n2_mf": "N2 initial mole fraction",
    "co2_mf": "CO2 initial mole fraction",
    "he_mf": "He initial mole fraction",
    "diluent_type": "Substituted inert diluent (recoded from CO2/He mole fractions)",
}
