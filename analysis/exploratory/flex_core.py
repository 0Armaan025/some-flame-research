"""Core loading and statistics for FLEX PSI-69 exploratory analysis (Phase 2).

Design rules (inherited from the Phase 1 audit and the project scientific
integrity requirements):

* Raw values are never modified. The source CSV is read byte-preserving
  (Windows-1252), exactly like analysis/audit/audit_flex_psi69.py.
* Missing means missing: empty fields and the 0x96 artifact byte are
  "not reported" and are NEVER imputed, filled, or treated as zero.
* Approximate values ("~6") keep their numeric value with an approx flag,
  matching the *_approx fields in schema/v1.2.0.sql. Statistics are computed
  on exact values only; approximate values are reported separately.
* Implausible records are retained in the dataset with explicit flags. Any
  statistic computed with such records removed appears as a separate,
  documented "screened" variant, never as a replacement of the as-reported
  numbers.
* No unit conversion happens anywhere. In particular the burning rate has an
  UNRESOLVED unit (the source header "Burning rate; mm" is not a valid rate
  unit); it is treated as a recorded scalar only.
"""

import csv
import glob
import hashlib
import math
import os
import platform
import sys
from collections import Counter, OrderedDict

import numpy as np

RAW_FLEX = os.path.join("data", "raw", "flex")


def _resolve_csv_path():
    """Locate the source CSV independently of the current working directory.

    The filename contains a space ('PSI-69_Experimental table_FLEX.csv'), so a
    literal path in code is a trap; resolve by glob from the repository root
    with a CWD fallback.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    candidates = glob.glob(os.path.join(root, "data", "raw", "flex", "PSI-69*FLEX.csv"))
    if not candidates:
        candidates = glob.glob(os.path.join(RAW_FLEX, "PSI-69*FLEX.csv"))
    if not candidates:
        raise FileNotFoundError("PSI-69 experimental table not found under data/raw/flex")
    return candidates[0]


CSV_PATH = _resolve_csv_path()

# The exact sha256 recorded when Phase 2 was authored. Tests assert against it
# so any accidental modification of the raw dataset is detected.
EXPECTED_CSV_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"

MISSING_BYTE = "\x96"  # 0x96 Windows-1252 en-dash used as a blank marker
FUELS = ("Methanol", "Heptane")  # source labels: "Heptane" = n-heptane as named in the source

QUARTILE_METHOD = "numpy linear interpolation (inclusive / method 7)"

COLUMNS = OrderedDict([
    ("flex_test_no", "FLEX Test #"),
    ("flex_identifier", "FLEX Identifier"),
    ("test_date", "Test Date"),
    ("test_gmt", "Test GMT"),
    ("fuel", "Fuel"),
    ("pressure_mmHg", "Ambient pressure; mmHg"),
    ("o2_mf", "O initial ambient composition; mole fraction"),
    ("n2_mf", "N initial ambient composition; mole fraction"),
    ("co2_mf", "CO initial ambient composition; mole fraction"),
    ("he_mf", "He initial ambient composition; mole fraction"),
    ("d0_mm", "Droplet initial diameter; mm"),
    ("d_ext_mm", "Visible flame extinction diameter; mm"),
    ("burn_rate_raw", "Burning rate; mm"),
    ("burn_time_s", "Burn time; s"),
    ("test_end", "Test end"),
])

NUMERIC_KEYS = ("pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf",
                "d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s")

# Measurement variables (units as headed in the source; burning rate UNRESOLVED)
VARIABLES = OrderedDict([
    ("d0_mm", "Droplet initial diameter (mm)"),
    ("d_ext_mm", "Visible flame extinction diameter (mm; visible-flame basis only)"),
    ("burn_rate_raw", "Burning rate (UNIT UNRESOLVED; recorded scalar as headed)"),
    ("burn_time_s", "Burn time (s)"),
    ("pressure_mmHg", "Ambient pressure (mmHg)"),
])

CORE_MEASUREMENT_KEYS = ("d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s")

OUTCOMES = ("Extinction", "Disruption", "Completion")


class SourceDataError(Exception):
    """Raised when the source file does not match the expected Phase 1 layout."""


def is_missing(raw):
    if raw is None:
        return True
    s = raw.strip()
    return s == "" or s == MISSING_BYTE


def parse_measured(raw):
    """Return (value, approx_flag). Missing -> (None, False). '~6' -> (6.0, True)."""
    if is_missing(raw):
        return None, False
    s = raw.strip()
    approx = s.startswith("~")
    if approx:
        s = s.lstrip("~").strip()
    try:
        return float(s), approx
    except ValueError:
        return None, False  # never invent: unparseable marker == not reported


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_records(path=CSV_PATH):
    """Load the experimental table byte-preservingly; no cleaning, no imputation."""
    with open(path, newline="", encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SourceDataError(f"no rows read from {path}")
    for col in COLUMNS.values():
        if col not in rows[0]:
            raise SourceDataError(f"expected column missing: {col!r}")
    records = []
    for i, row in enumerate(rows, start=2):
        rec = {"csv_line": i}
        for key, col in COLUMNS.items():
            rec[key] = (row[col] or "").strip()
        for key in NUMERIC_KEYS:
            rec[key + "_val"], rec[key + "_approx"] = parse_measured(rec[key])
        rec["missing_marker_bytes"] = sum(1 for v in row.values() if v and MISSING_BYTE in v)
        rec["comp_sum_mf"] = (None if any(rec[k + "_val"] is None for k in
                                          ("o2_mf", "n2_mf", "co2_mf", "he_mf"))
                              else round(sum(rec[k + "_val"] for k in
                                             ("o2_mf", "n2_mf", "co2_mf", "he_mf")), 6))
        rec["flags"] = compute_flags(rec)
        records.append(rec)
    return records


def compute_flags(rec):
    """Explicit, documented anomaly flags. Nothing is dropped or corrected."""
    flags = []
    if rec["pressure_mmHg_val"] == 0.0:
        flags.append("pressure_reported_zero")
    if rec["d_ext_mm_val"] == 0.0:
        flags.append("extinction_diameter_reported_zero")
    if (rec["d0_mm_val"] not in (None, 0.0) and rec["d_ext_mm_val"] is not None
            and rec["d_ext_mm_val"] > rec["d0_mm_val"] + 1e-9):
        flags.append("extinction_diameter_gt_initial_diameter")
    if rec["comp_sum_mf"] is not None and abs(rec["comp_sum_mf"] - 1.0) > 1e-9:
        flags.append("composition_sum_not_one")
    if any(rec[k + "_approx"] for k in ("d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s")):
        flags.append("contains_approximate_value")
    if rec["test_end"] not in OUTCOMES:
        flags.append("unrecognised_outcome_label")
    return flags


def pressure_band(value):
    """Reporting aid over the reported mmHg values. No conversion performed."""
    if value is None:
        return "not_reported"
    if value < 560:
        return "<560 mmHg"
    if value < 800:
        return "560-800 mmHg"
    if value <= 2100:
        return "800-2100 mmHg"
    return ">2100 mmHg"


def diluent_type(rec):
    """Which inert diluent is substituted (CO2-tagged, He-tagged or none) as reported."""
    if rec["co2_mf_val"] or rec["he_mf_val"]:
        if rec["co2_mf_val"] and rec["he_mf_val"]:
            return "CO2+He"
        return "CO2" if rec["co2_mf_val"] else "He"
    return "none"


def condition_family(rec):
    return "O2={o}/N2={n}/CO2={c}/He={h}".format(
        o=rec["o2_mf"] or "?", n=rec["n2_mf"] or "?",
        c=rec["co2_mf"] or "?", h=rec["he_mf"] or "?")


def screened_out(rec):
    """True if the record carries a value-integrity flag on the measurement
    variables. Screened statistics EXCLUDE these records; the as-reported
    statistics always include them."""
    return bool({"pressure_reported_zero", "extinction_diameter_reported_zero",
                 "extinction_diameter_gt_initial_diameter"} & set(rec["flags"]))


# ---------------------------------------------------------------------------
# Descriptive statistics (exact values only; approx values never mixed in)
# ---------------------------------------------------------------------------
def descriptive_stats(values):
    """n_used / mean / std / min / q1 / median / q3 / max / iqr for exact values.

    std is the sample standard deviation (ddof=1). Quartiles use numpy's
    default linear interpolation (inclusive, a.k.a. method 7); the method is
    documented in the README so results are reproducible.
    Values flagged approximate are NOT included here; they are counted in
    n_approx_excluded so every reader sees the effective sample size.
    """
    vals = [v for v, approx in values if v is not None and not approx]
    n_approx = sum(1 for v, approx in values if v is not None and approx)
    out = OrderedDict(n_total=len(values), n_used=len(vals), n_missing=sum(
        1 for v, _ in values if v is None), n_approx_excluded=n_approx)
    if not vals:
        out.update(mean=None, std=None, min=None, q1=None, median=None,
                   q3=None, max=None, iqr=None)
        return out
    arr = np.asarray(vals, dtype=float)
    q1, median, q3 = (float(x) for x in np.percentile(arr, [25, 50, 75]))
    out.update(mean=float(arr.mean()), std=float(arr.std(ddof=1)) if len(arr) > 1 else None,
               min=float(arr.min()), q1=q1, median=median, q3=q3,
               max=float(arr.max()), iqr=q3 - q1)
    return out


def fmt_num(x, digits=4):
    return "" if x is None else f"{x:.{digits}f}"


def fmt_p(p):
    """Format p-values so small values stay legible and honest.

    4 fixed decimals would render 1.97e-9 as "0.0000", which reads as
    exactly zero; switch to scientific notation below 1e-4.
    """
    if p is None:
        return ""
    p = float(p)
    return f"{p:.3g}"


# ---------------------------------------------------------------------------
# Nonparametric comparisons (implemented without scipy; validated in tests)
# ---------------------------------------------------------------------------
def mann_whitney_u(x, y):
    """Two-sided Mann-Whitney U with tie correction and normal approximation.

    Returns (U, p_two_sided, n_x, n_y). Appropriate for independent samples;
    independence is a caveat documented in the README (the 193F001 identifier
    collision means two rows may not be independent runs).
    """
    x = np.asarray([v for v in x], dtype=float)
    y = np.asarray([v for v in y], dtype=float)
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return None, None, nx, ny
    allv = np.concatenate([x, y])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv), dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1, dtype=float)
    # average ties
    i = 0
    tie_term = 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[order[j + 1]] == allv[order[i]]:
            j += 1
        if j > i:
            avg = (i + j + 2) / 2.0  # mean of ranks i+1..j+1 (1-based)
            ranks[order[i:j + 1]] = avg
            t = j - i + 1
            tie_term += t ** 3 - t
        i = j + 1
    rx = ranks[:nx].sum()
    ux = rx - nx * (nx + 1) / 2.0
    uy = nx * ny - ux
    u = min(ux, uy)
    n = nx + ny
    mu = nx * ny / 2.0
    sigma_sq = (nx * ny / 12.0) * ((n + 1) - tie_term / (n * (n - 1.0)))
    if sigma_sq <= 0:
        return u, None, nx, ny
    z = (u - mu + 0.5) / np.sqrt(sigma_sq)  # continuity correction
    p = 2.0 * 0.5 * math.erfc(abs(z) / math.sqrt(2.0))
    return float(u), float(min(1.0, p)), nx, ny


def spearman_rho(x, y):
    """Spearman rank correlation with tie-averaged ranks (descriptive association)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3:
        return None, len(x)

    def rankdata(a):
        order = a.argsort(kind="mergesort")
        ranks = np.empty(len(a), dtype=float)
        ranks[order] = np.arange(1, len(a) + 1, dtype=float)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            if j > i:
                ranks[order[i:j + 1]] = (i + j + 2) / 2.0
            i = j + 1
        return ranks
    rx, ry = rankdata(x), rankdata(y)
    if rx.std() == 0 or ry.std() == 0:
        return None, len(x)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    n = len(x)
    if n > 2 and abs(rho) < 1.0:
        t = rho * np.sqrt((n - 2) / (1 - rho ** 2))
        # two-sided p for the t statistic: 2*Phi(-|t|) = erfc(|t|/sqrt(2)).
        # NOTE: this is the SAME correct form as the Mann-Whitney line above;
        # an earlier version wrote 2*(1 - 0.5*erfc(...)) = 2*Phi(|t|), which is
        # >= 1 for every |t| > 0 and was silently clipped to 1.0.
        p = float(min(1.0, math.erfc(abs(t) / math.sqrt(2.0))))
    else:
        p = None
    return rho, p


def fisher_exact_2x2(a, b, c, d):
    """Two-sided Fisher exact test for [[a,b],[c,d]] (hypergeometric)."""
    def logchoose(n, k):
        if 0 <= k <= n:
            return float(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1))
        return -math.inf
    n = a + b + c + d
    r1, c1 = a + b, a + c
    if n == 0:
        return None, None
    obs_p = np.exp(logchoose(r1, a) + logchoose(n - r1, c1 - a) - logchoose(n, c1))
    total = 0.0
    kmax = min(r1, c1)
    for k in range(0, kmax + 1):
        p = np.exp(logchoose(r1, k) + logchoose(n - r1, c1 - k) - logchoose(n, c1))
        if p <= obs_p + 1e-12:
            total += p
    return float(min(1.0, total)), float(obs_p)


def holm_adjust(pvals):
    """Holm-Bonferroni step-down adjusted p-values (list order preserved)."""
    m = len(pvals)
    idx = sorted(range(m), key=lambda i: pvals[i])
    adjusted = [None] * m
    running = 0.0
    for rank, i in enumerate(idx):
        val = min(1.0, (m - rank) * pvals[i])
        running = max(running, val)
        adjusted[i] = running
    return adjusted


# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------
def python_env():
    import matplotlib
    return OrderedDict(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        numpy=np.__version__,
        matplotlib=matplotlib.__version__,
    )
