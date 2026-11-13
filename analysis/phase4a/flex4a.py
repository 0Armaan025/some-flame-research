"""FLEX PSI-69 Phase 4A - comparative analysis library.

Independent, byte-preserving loader and statistical primitives. Nothing from
Phases 1-3.5 is imported; frozen artifacts are read-only inputs and every
prior-phase number quoted in the report is re-derived here.

Integrity rules carried forward:
  * raw values verbatim (latin-1 read; 0x96 = missing marker; "~" = approximate);
  * no imputation, no unit assignment, no composition renormalisation;
  * burning-rate column treated as an unresolved scalar - never interpreted;
  * flagged records retained; screened variants documented;
  * the 193F001 collision is reported under every exclusion rule, never resolved
    by preferring one version.
"""

import csv
import glob
import math
import os
from collections import Counter, OrderedDict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MISSING_BYTE = "\x96"
FUELS = ("Methanol", "Heptane")
OUTCOMES = ("Extinction", "Disruption", "Completion")
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"

# Series/campaign prefix = leading alphanumeric run before the trailing
# letter+number of the identifier (matches the Phase 3 prefix rule).
def series_prefix(ident):
    import re
    m = re.match(r"^([0-9A-Z]*?)[A-Z]?[0-9]+$", ident)
    return m.group(1) if m else ident


def is_missing(raw):
    return raw is None or raw.strip() in ("", MISSING_BYTE)


def parse_measured(raw):
    if is_missing(raw):
        return None, False
    s = raw.strip()
    approx = s.startswith("~")
    if approx:
        s = s.lstrip("~").strip()
    try:
        return float(s), approx
    except ValueError:
        return None, False


def load_records():
    path = glob.glob(os.path.join(ROOT, "data", "raw", "flex", "PSI-69*FLEX.csv"))[0]
    with open(path, newline="", encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh))
    cols = {"pressure_mmHg": "Ambient pressure; mmHg",
            "o2_mf": "O initial ambient composition; mole fraction",
            "n2_mf": "N initial ambient composition; mole fraction",
            "co2_mf": "CO initial ambient composition; mole fraction",
            "he_mf": "He initial ambient composition; mole fraction",
            "d0_mm": "Droplet initial diameter; mm",
            "d_ext_mm": "Visible flame extinction diameter; mm",
            "burn_rate_raw": "Burning rate; mm",
            "burn_time_s": "Burn time; s"}
    records = []
    for r in rows:
        rec = {"flex_test_no": r["FLEX Test #"].strip(),
               "flex_identifier": r["FLEX Identifier"].strip(),
               "test_date": r["Test Date"].strip(),
               "test_gmt": r["Test GMT"].strip(),
               "fuel": r["Fuel"].strip(),
               "test_end": r["Test end"].strip()}
        for key, col in cols.items():
            rec[key] = r[col].strip()
            rec[key + "_val"], rec[key + "_approx"] = parse_measured(r[col])
        rec["series"] = series_prefix(rec["flex_identifier"])
        rec["comp_sum_mf"] = (None if any(rec[k + "_val"] is None for k in
                                          ("o2_mf", "n2_mf", "co2_mf", "he_mf"))
                              else round(sum(rec[k + "_val"] for k in
                                             ("o2_mf", "n2_mf", "co2_mf", "he_mf")), 6))
        rec["diluent"] = ("CO2" if rec["co2_mf_val"] else
                          "He" if rec["he_mf_val"] else "none")
        rec["flags"] = _flags(rec)
        records.append(rec)
    return records


def _flags(rec):
    f = []
    if rec["pressure_mmHg_val"] == 0.0:
        f.append("pressure_reported_zero")
    if rec["d_ext_mm_val"] == 0.0:
        f.append("extinction_diameter_reported_zero")
    if (rec["d0_mm_val"] not in (None, 0.0) and rec["d_ext_mm_val"] is not None
            and rec["d_ext_mm_val"] > rec["d0_mm_val"] + 1e-9):
        f.append("extinction_diameter_gt_initial_diameter")
    if rec["comp_sum_mf"] is not None and abs(rec["comp_sum_mf"] - 1.0) > 1e-9:
        f.append("composition_sum_not_one")
    if rec["flex_identifier"] == "193F001":
        f.append("identifier_collision_193F001")
    if any(rec[k + "_approx"] for k in ("d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s")):
        f.append("contains_approximate_value")
    return f


def screened_out(rec):
    return bool({"pressure_reported_zero", "extinction_diameter_reported_zero",
                 "extinction_diameter_gt_initial_diameter"} & set(rec["flags"]))


def pressure_band(v):
    if v is None:
        return "not_reported"
    if v < 560:
        return "<560 mmHg"
    if v < 800:
        return "560-800 mmHg"
    if v <= 2100:
        return "800-2100 mmHg"
    return ">2100 mmHg"


# ---------------------------------------------------------------------------
# statistics (implemented in-repo; tested against reference values)
# ---------------------------------------------------------------------------
def mwu(x, y):
    """Two-sided Mann-Whitney U with tie and continuity corrections."""
    x, y = list(x), list(y)
    allv = sorted(x + y)
    ranks = {}
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        avg = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[allv[k]] = avg
        i = j + 1
    rx = sum(ranks[v] for v in x)
    nx, ny = len(x), len(y)
    ux = rx - nx * (nx + 1) / 2.0
    u = min(ux, nx * ny - ux)
    mu = nx * ny / 2.0
    tie = 0
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        t = j - i + 1
        tie += t ** 3 - t
        i = j + 1
    n = nx + ny
    sig2 = (nx * ny / 12.0) * ((n + 1) - tie / (n * (n - 1.0)))
    if nx == 0 or ny == 0:
        return None, None
    z = (u - mu + 0.5) / math.sqrt(sig2)
    return float(u), float(math.erfc(abs(z) / math.sqrt(2.0)))


def rank_biserial(u, nx, ny):
    """Effect size r = 1 - 2U/(n1*n2) for the two-sided MWU."""
    if not nx or not ny:
        return None
    return 1.0 - 2.0 * u / (nx * ny)


def perm_p(x, y, draws=200000, seed=20261112):
    """Exact-style permutation p for the MWU statistic difference (no
    distributional assumption; robust to the tie/approximation issues)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) == 0 or len(y) == 0:
        return None
    obs = abs(np.median(x) - np.median(y))
    rng = np.random.default_rng(seed)
    pool = np.concatenate([x, y])
    nx = len(x)
    count = 0
    for _ in range(draws):
        rng.shuffle(pool)
        if abs(np.median(pool[:nx]) - np.median(pool[nx:])) >= obs - 1e-12:
            count += 1
    return (count + 1) / (draws + 1)


def bootstrap_median_diff_ci(x, y, draws=20000, seed=20261112, alpha=0.05):
    """Percentile bootstrap CI for median(y)-median(x); independent resamples."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 2 or len(y) < 2:
        return None
    rng = np.random.default_rng(seed)
    diffs = np.empty(draws)
    for i in range(draws):
        bx = rng.choice(x, size=len(x), replace=True)
        by = rng.choice(y, size=len(y), replace=True)
        diffs[i] = np.median(by) - np.median(bx)
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(np.median(y) - np.median(x)), float(lo), float(hi)


def quantiles(vals, qs=(25, 50, 75)):
    return [float(v) for v in np.percentile(np.asarray(vals, float), qs)]


def describe(vals, exclude_approx=True, approx_flags=None):
    vals_l = list(vals)
    n_total = len(vals_l)
    used = [v for v in vals_l if v is not None] if approx_flags is None else \
        [v for v, a in zip(vals_l, approx_flags) if v is not None and not (exclude_approx and a)]
    out = OrderedDict(n_total=n_total, n_used=len(used),
                      n_missing=sum(1 for v in vals_l if v is None),
                      n_approx_excluded=sum(1 for v, a in zip(vals_l, approx_flags or [False] * n_total)
                                            if v is not None and a))
    if used:
        q1, med, q3 = quantiles(used)
        out.update(median=med, q1=q1, q3=q3, iqr=q3 - q1,
                   min=float(min(used)), max=float(max(used)),
                   mean=float(np.mean(used)),
                   sd=float(np.std(used, ddof=1)) if len(used) > 1 else None)
    return out


def fisher_exact_2x2(a, b, c, d):
    """Two-sided Fisher exact test; returns (p, oddsratio)."""
    def lc(n, k):
        if 0 <= k <= n:
            return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
        return -math.inf
    n = a + b + c + d
    r1, c1 = a + b, a + c
    if n == 0:
        return None, None
    obs = math.exp(lc(r1, a) + lc(n - r1, c1 - a) - lc(n, c1))
    total = 0.0
    for k in range(0, min(r1, c1) + 1):
        p = math.exp(lc(r1, k) + lc(n - r1, c1 - k) - lc(n, c1))
        if p <= obs + 1e-12:
            total += p
    or_ = (a / b) / (c / d) if b and d else float("inf")
    return float(min(1.0, total)), or_


def log_or_ci(a, b, c, d):
    """Wald 95% CI for the odds ratio (0.5 continuity correction if needed)."""
    if 0 in (a, b, c, d):
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    lor = math.log((a * d) / (b * c))
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return math.exp(lor), math.exp(lor - 1.96 * se), math.exp(lor + 1.96 * se)


def holm(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [None] * m
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * pvals[i]))
        adj[i] = run
    return adj


def cramers_v(table):
    """Cramer's V for an r x c contingency table (list of rows)."""
    t = np.asarray(table, float)
    n = t.sum()
    r, c = t.shape
    if n == 0 or min(r - 1, c - 1) == 0:
        return None
    exp = np.outer(t.sum(axis=1), t.sum(axis=0)) / n
    chi2 = float(((t - exp) ** 2 / exp).sum())
    return math.sqrt(chi2 / (n * min(r - 1, c - 1))), chi2


def fisher_freeman_halton_2x3(table):
    """Freeman-Halton extension of Fisher's exact test for a 2x3 table.

    Enumerates all 2x3 tables with the same margins and sums the probability
    of every table no more probable than the observed one (two-sided).
    """
    t = np.asarray(table, float)

    def prob(tbl):
        n1 = tbl[0].sum()
        n2 = tbl[1].sum()
        colsum = tbl.sum(axis=0)
        n = tbl.sum()
        val = math.lgamma(n1 + 1) + math.lgamma(n2 + 1)
        val += sum(math.lgamma(c + 1) for c in colsum)
        val -= math.lgamma(n + 1)
        for i in range(2):
            for j in range(3):
                val -= math.lgamma(tbl[i, j] + 1)
        return math.exp(val)

    obs = prob(t)
    row1 = int(t[0].sum())
    colsum = t.sum(axis=0).astype(int)
    total = obs
    # t[0][2] is determined by the row margin, so enumerate (t00, t01)
    for i in range(0, colsum[0] + 1):
        for j in range(0, colsum[1] + 1):
            k = row1 - i - j
            if k < 0 or k > colsum[2]:
                continue
            cand = np.array([[i, j, k],
                             [colsum[0] - i, colsum[1] - j, colsum[2] - k]], float)
            if prob(cand) <= obs + 1e-12:
                total += prob(cand)
    return float(min(1.0, total))


def fmt(x, digits=4, sci_below=1e-4):
    if x is None:
        return ""
    x = float(x)
    if x != 0 and abs(x) < sci_below:
        return f"{x:.3g}"
    return f"{x:.{digits}f}"
