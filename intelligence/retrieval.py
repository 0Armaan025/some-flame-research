"""FLEX-PSI69 evidence intelligence - deterministic retrieval layer.

Byte-preserving loader for the frozen raw experimental table plus accessors
for the frozen Phase 4A result artifacts. This module invents nothing: every
value returned is either the raw record or a value recomputed from raw records.

Integrity rules (identical to all prior phases):
  * latin-1 read; 0x96 = missing marker; "~" = approximate;
  * the 0 mmHg pressure record (C11M201) is treated as missing (corrupted);
  * burning-rate column is carried verbatim but never interpreted;
  * no imputation, no renormalisation, no unit assignment.
"""

import csv
import glob
import hashlib
import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATTERN = os.path.join("data", "raw", "flex", "PSI-69*FLEX.csv")
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"
MISSING_BYTE = "\x96"
OUTCOMES = ("Extinction", "Disruption", "Completion")
FUELS = ("Methanol", "Heptane")

PHASE4A = os.path.join(ROOT, "analysis", "phase4a")
P4A_INPUTS = {  # frozen evidence artifacts this engine may read
    "results_summary": os.path.join(PHASE4A, "results_summary.csv"),
    "outcome_comparison": os.path.join(PHASE4A, "outcome_comparison.csv"),
    "duration_comparison": os.path.join(PHASE4A, "duration_comparison.csv"),
    "diameter_comparison": os.path.join(PHASE4A, "diameter_comparison.csv"),
    "extinction_assessment": os.path.join(PHASE4A, "extinction_diameter_assessment.csv"),
    "condition_comparison": os.path.join(PHASE4A, "condition_comparison.csv"),
    "sensitivity_analysis": os.path.join(PHASE4A, "sensitivity_analysis.csv"),
    "limitations_register": os.path.join(PHASE4A, "limitations_register.csv"),
}


def raw_csv_path():
    return glob.glob(os.path.join(ROOT, RAW_PATTERN))[0]


def sha256_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _parse(raw):
    if raw is None:
        return None
    s = raw.strip()
    if s in ("", MISSING_BYTE):
        return None
    if s.startswith("~"):
        s = s.lstrip("~").strip()
    try:
        return float(s)
    except ValueError:
        return None


def series_prefix(ident):
    m = re.match(r"^([0-9A-Z]*?)[A-Z]?[0-9]+$", ident)
    return m.group(1) if m else ident


def load_records():
    """All 274 records as ordered dicts with parsed values and provenance."""
    path = raw_csv_path()
    with open(path, newline="", encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh))
    records = []
    for r in rows:
        pressure = _parse(r["Ambient pressure; mmHg"])
        co2 = _parse(r["CO initial ambient composition; mole fraction"])
        he = _parse(r["He initial ambient composition; mole fraction"])
        rec = OrderedDict(
            flex_test_no=r["FLEX Test #"].strip(),
            flex_identifier=r["FLEX Identifier"].strip(),
            series=series_prefix(r["FLEX Identifier"].strip()),
            test_date=r["Test Date"].strip(),
            test_gmt=r["Test GMT"].strip(),
            fuel=r["Fuel"].strip(),
            pressure_mmHg=(None if pressure == 0.0 else pressure),
            pressure_reported=r["Ambient pressure; mmHg"].strip(),
            o2_mf=_parse(r["O initial ambient composition; mole fraction"]),
            n2_mf=_parse(r["N initial ambient composition; mole fraction"]),
            co2_mf=co2,
            he_mf=he,
            d0_mm=_parse(r["Droplet initial diameter; mm"]),
            d_ext_mm=_parse(r["Visible flame extinction diameter; mm"]),
            burn_rate_raw=_parse(r["Burning rate; mm"]),
            burn_time_s_raw=r["Burn time; s"].strip(),
            burn_time_s=_parse(r["Burn time; s"]),
            burn_time_approx=r["Burn time; s"].strip().startswith("~"),
            outcome=r["Test end"].strip(),
        )
        rec["pressure_note"] = ("corrupted_zero_record_treated_as_missing"
                                if rec["pressure_mmHg"] is None
                                and rec["pressure_reported"] not in ("", MISSING_BYTE)
                                else "")
        rec["flags"] = _flags(rec)
        rec["complete_core"] = all(rec[k] is not None for k in
                                   ("d0_mm", "d_ext_mm", "burn_rate_raw",
                                    "burn_time_s"))
        records.append(rec)
    return records


def _flags(rec):
    f = []
    if rec["pressure_reported"] == "0":
        f.append("pressure_reported_zero")
    if rec["d_ext_mm"] == 0.0:
        f.append("extinction_diameter_reported_zero")
    if (rec["d0_mm"] not in (None, 0.0) and rec["d_ext_mm"] is not None
            and rec["d_ext_mm"] > rec["d0_mm"] + 1e-9):
        f.append("extinction_diameter_gt_initial_diameter")
    if rec["flex_identifier"] == "193F001":
        f.append("identifier_collision_193F001")
    if rec["burn_time_approx"]:
        f.append("contains_approximate_value")
    s = sum(v for v in (rec["o2_mf"], rec["n2_mf"], rec["co2_mf"], rec["he_mf"])
            if v is not None)
    if s and abs(s - 1.0) > 1e-9:
        f.append("composition_sum_not_one")
    return f


def read_frozen(name):
    """Read a frozen Phase 4A CSV artifact."""
    with open(P4A_INPUTS[name]) as fh:
        return list(csv.DictReader(fh))


def experiment_view(rec):
    """Compact, provenance-complete view of one record for API responses."""
    return OrderedDict(
        flex_test_no=rec["flex_test_no"],
        flex_identifier=rec["flex_identifier"],
        series=rec["series"],
        test_date=rec["test_date"],
        test_gmt=rec["test_gmt"],
        fuel=rec["fuel"],
        pressure_mmHg=rec["pressure_mmHg"],
        o2_mf=rec["o2_mf"], n2_mf=rec["n2_mf"], co2_mf=rec["co2_mf"],
        he_mf=rec["he_mf"],
        d0_mm=rec["d0_mm"],
        d_ext_mm=rec["d_ext_mm"],
        burn_time_s=rec["burn_time_s"],
        outcome=rec["outcome"],
        flags=rec["flags"],
        complete_core=rec["complete_core"],
        provenance="data/raw/flex/PSI-69 Experimental table_FLEX.csv "
                   f"(sha256 {RAW_SHA256[:16]}…), row {rec['flex_test_no']}",
    )


# ---------------------------------------------------------------------------
# deterministic statistics (self-contained; validated against hand-computed
# reference values in tests)
# ---------------------------------------------------------------------------
def fisher_exact_2x2(a, b, c, d):
    import math
    def lc(n, k):
        if 0 <= k <= n:
            return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
        return -math.inf
    n = a + b + c + d
    r1, c1 = a + b, a + c
    if n == 0:
        return None
    obs = math.exp(lc(r1, a) + lc(n - r1, c1 - a) - lc(n, c1))
    total = 0.0
    for k in range(0, min(r1, c1) + 1):
        p = math.exp(lc(r1, k) + lc(n - r1, c1 - k) - lc(n, c1))
        if p <= obs + 1e-12:
            total += p
    return float(min(1.0, total))


def fisher_freeman_halton_2x3(table):
    import math
    t = [[float(x) for x in row] for row in table]

    def prob(tbl):
        n1, n2 = sum(tbl[0]), sum(tbl[1])
        cs = [tbl[0][j] + tbl[1][j] for j in range(3)]
        n = n1 + n2
        v = math.lgamma(n1 + 1) + math.lgamma(n2 + 1)
        v += sum(math.lgamma(c + 1) for c in cs)
        v -= math.lgamma(n + 1)
        for i in range(2):
            for j in range(3):
                v -= math.lgamma(tbl[i][j] + 1)
        return math.exp(v)

    obs = prob(t)
    row1 = int(sum(t[0]))
    cs = [int(sum(t[i][j] for i in range(2))) for j in range(3)]
    total = obs
    for i in range(0, cs[0] + 1):
        for j in range(0, cs[1] + 1):
            k = row1 - i - j
            if not (0 <= k <= cs[2]):
                continue
            cand = [[i, j, k], [cs[0] - i, cs[1] - j, cs[2] - k]]
            if prob(cand) <= obs + 1e-12:
                total += prob(cand)
    return float(min(1.0, total))


def cramers_v(table):
    t = [[float(x) for x in row] for row in table]
    n = sum(sum(r) for r in t)
    rs = [sum(r) for r in t]
    cs = [sum(t[i][j] for i in range(2)) for j in range(3)]
    chi2 = 0.0
    for i in range(2):
        for j in range(3):
            e = rs[i] * cs[j] / n
            chi2 += (t[i][j] - e) ** 2 / e
    import math
    return math.sqrt(chi2 / (n * 1))  # min(r-1,c-1)=1 for 2x3


def holm(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [None] * m
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * pvals[i]))
        adj[i] = run
    return adj


def mwu(x, y):
    """Two-sided Mann-Whitney U, tie- and continuity-corrected normal approx."""
    import math
    allv = sorted(list(x) + list(y))
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
    tie = 0
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        tie += (j - i + 1) ** 3 - (j - i + 1)
        i = j + 1
    n = nx + ny
    sig2 = (nx * ny / 12.0) * ((n + 1) - tie / (n * (n - 1.0)))
    z = (u - nx * ny / 2.0 + 0.5) / math.sqrt(sig2)
    return float(u), float(math.erfc(abs(z) / math.sqrt(2.0)))


def rank_biserial(u, nx, ny):
    return 1.0 - 2.0 * u / (nx * ny)


def quantiles(vals):
    import numpy as np
    return [float(v) for v in np.percentile(vals, [25, 50, 75])]