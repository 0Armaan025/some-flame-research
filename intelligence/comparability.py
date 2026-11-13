"""FLEX-PSI69 evidence intelligence - comparability rules.

Reproduces the frozen Phase 3/4A comparability logic against the raw records
so that the intelligence engine can decide, per query, which experiments are
comparable. The rules are identical to the frozen assessment; tests assert the
same classifications as `analysis/phase4a/condition_comparison.csv`.
"""

from collections import OrderedDict

import retrieval as R

MIN_SIDE_N = 3


def diluent_of(rec):
    if (rec["co2_mf"] or 0) > 0 and (rec["he_mf"] or 0) > 0:
        return "CO2+He"
    if (rec["co2_mf"] or 0) > 0:
        return "CO2"
    if (rec["he_mf"] or 0) > 0:
        return "He"
    return "none"


def pressure_band(rec):
    p = rec["pressure_mmHg"]
    if p is None:
        return "not_reported"
    if p < 560:
        return "<560 mmHg"
    if p < 800:
        return "560-800 mmHg"
    if p <= 2100:
        return "800-2100 mmHg"
    return ">2100 mmHg"


def condition_family(rec):
    return "O2={o}/N2={n}/CO2={c}/He={h}".format(
        o=rec["o2_mf"], n=rec["n2_mf"], c=rec["co2_mf"], h=rec["he_mf"])


def dilution_cells(records):
    """Matched-O2 CO2-vs-He substitution cells with the Phase 4A verdicts."""
    by_o2 = {}
    for r in records:
        d = diluent_of(r)
        if d in ("CO2", "He"):
            by_o2.setdefault(r["o2_mf"], {}).setdefault(d, []).append(r)
    cells = []
    for o2 in sorted(by_o2):
        kinds = by_o2[o2]
        if "CO2" not in kinds or "He" not in kinds:
            continue
        co2, he = kinds["CO2"], kinds["He"]
        n2_co2 = sorted({r["n2_mf"] for r in co2})
        n2_he = sorted({r["n2_mf"] for r in he})
        bands_co2 = sorted({pressure_band(r) for r in co2})
        bands_he = sorted({pressure_band(r) for r in he})
        shared = sorted(set(bands_co2) & set(bands_he))
        n2_match = set(n2_co2) == set(n2_he)
        enough = len(co2) >= MIN_SIDE_N and len(he) >= MIN_SIDE_N
        if not enough:
            cls = "rejected"
            reason = (f"insufficient records on a side (CO2 n={len(co2)}, He n={len(he)}; "
                      f"minimum {MIN_SIDE_N})")
        elif not shared:
            cls = "rejected"
            reason = "no shared pressure band"
        elif not n2_match:
            cls = "partial"
            reason = ("reported N2 balances differ across sides "
                      f"(CO2 {n2_co2} vs He {n2_he})")
        else:
            cls = "full"
            reason = (f"identical N2 balances {n2_co2}, shared pressure band(s) "
                      f"{shared}, both sides n>={MIN_SIDE_N}")
        cells.append(OrderedDict(
            o2_mf=o2, diluent="CO2 vs He",
            n_co2=len(co2), n_he=len(he),
            n_co2_by_fuel={f: sum(1 for r in co2 if r["fuel"] == f) for f in R.FUELS},
            n_he_by_fuel={f: sum(1 for r in he if r["fuel"] == f) for f in R.FUELS},
            n2_co2=n2_co2, n2_he=n2_he, bands_co2=bands_co2, bands_he=bands_he,
            shared_bands=shared, comparability=cls, reason=reason))
    return cells


def experiments_in_cell(records, o2, side):
    return [r for r in records
            if r["o2_mf"] == o2 and diluent_of(r) == side]


def match_conditions(records, conditions):
    """Filter records matching a partial condition spec (exact on given keys)."""
    out = records
    for key, want in conditions.items():
        if want is None:
            continue
        if key == "diluent":
            out = [r for r in out if diluent_of(r) == want]
        elif key == "pressure_band":
            out = [r for r in out if pressure_band(r) == want]
        else:
            out = [r for r in out if r.get(key) == want]
    return out