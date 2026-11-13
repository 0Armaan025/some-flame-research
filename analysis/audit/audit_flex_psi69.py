#!/usr/bin/env python3
"""Read-only scientific data audit for the FLEX PSI-69 experimental table.

Scope (Phase 1):
  * inventory of data/raw/flex/ source files
  * per-fuel record counts, completeness, missingness, duplicates
  * outcome distribution (extinction / disruption / completion)
  * condition coverage (O2, pressure, diluent composition)
  * measurement linkage between the CSV and per-run telemetry files
  * confounding-variable and limitation notes used by the reports

Scientific integrity rules enforced by this script:
  * No unit conversion is performed anywhere. Values are carried through
    exactly as reported (pressure stays mmHg, rates stay "mm" as headed).
  * No missing value is invented, interpolated, or imputed. Missing means
    "not reported in the source". The byte 0x96 (Windows-1252 en-dash,
    a spreadsheet artifact) is treated as a missing marker, not as data.
  * Nothing is written under data/raw, schema/, tests/, or src/.

Run from the repository root:  python3 analysis/audit/audit_flex_psi69.py
"""

import csv
import glob
import os
import re
import statistics
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_FLEX = os.path.join(ROOT, "data", "raw", "flex")
CSV_PATH = glob.glob(os.path.join(RAW_FLEX, "PSI-69*FLEX.csv"))[0]
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

MISSING_BYTE = "\x96"  # 0x96, Windows-1252 en-dash used as a blank marker

# Column name -> short key. Units are part of the original headers and are
# never altered.
COLUMNS = {
    "flex_test_no": "FLEX Test #",
    "flex_identifier": "FLEX Identifier",
    "test_date": "Test Date",
    "test_gmt": "Test GMT",
    "fuel": "Fuel",
    "pressure_mmHg": "Ambient pressure; mmHg",
    "o2_mf": "O initial ambient composition; mole fraction",
    "n2_mf": "N initial ambient composition; mole fraction",
    "co_mf": "CO initial ambient composition; mole fraction",
    "he_mf": "He initial ambient composition; mole fraction",
    "d0_mm": "Droplet initial diameter; mm",
    "d_ext_mm": "Visible flame extinction diameter; mm",
    "burn_rate": "Burning rate; mm",
    "burn_time_s": "Burn time; s",
    "test_end": "Test end",
}

MEASUREMENT_VARS = ["d0_mm", "d_ext_mm", "burn_rate", "burn_time_s"]
CONDITION_VARS = ["pressure_mmhg".lower(), "o2_mf", "n2_mf", "co_mf", "he_mf"]
ALL_VARS = list(COLUMNS.keys())


def is_missing(raw):
    """Missing = empty field, whitespace, or the 0x96 artifact byte."""
    if raw is None:
        return True
    s = raw.strip()
    return s == "" or s == MISSING_BYTE


def parse_measured(raw):
    """Parse a reported numeric field.

    Returns (value, approx_flag). Rules:
      * empty / 0x96 byte          -> (None, False): not reported; never invented.
      * "~6" (tilde prefix)        -> (6.0, True): reported but flagged approximate
                                      by the source; the value is kept, the flag
                                      is carried alongside so downstream analysis
                                      can exclude or weight it explicitly.
      * "3.4"                      -> (3.4, False): measured as reported.
    No unit conversion happens here or anywhere in this script.
    """
    if is_missing(raw):
        return None, False
    s = raw.strip()
    approx = s.startswith("~")
    if approx:
        s = s.lstrip("~").strip()
    try:
        return float(s), approx
    except ValueError:
        # Unparseable non-numeric marker: treat as not reported, never as 0.
        return None, False


def fmt(value, digits=2):
    return "" if value is None else f"{value:.{digits}f}"


def fmt_range(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return ""
    return f"{min(vals):g}-{max(vals):g}"


def parse_date(raw):
    """Parse 'M/D/YYYY' and 'M/D/YY' exactly as written; no reformatting."""
    s = raw.strip()
    parts = s.split("/")
    if len(parts) != 3:
        return None
    m, d, y = parts
    if not (m.isdigit() and d.isdigit() and y.isdigit()):
        return None
    y = int(y)
    if y < 100:
        y += 2000
    return (y, int(m), int(d))


def describe(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return dict(n=0, mean="", median="", min="", max="")
    return dict(
        n=len(vals),
        mean=f"{statistics.fmean(vals):.3g}",
        median=f"{statistics.median(vals):.3g}",
        min=f"{min(vals):g}",
        max=f"{max(vals):g}",
    )


# ---------------------------------------------------------------------------
# 1. Load the experimental table (no normalisation, no unit conversion)
# ---------------------------------------------------------------------------
def load_records():
    with open(CSV_PATH, newline="", encoding="latin-1") as fh:
        reader = csv.DictReader(fh)
        raw_rows = list(reader)
    records = []
    for i, row in enumerate(raw_rows, start=2):  # header is line 1
        rec = {"csv_line": i}
        for key, col in COLUMNS.items():
            rec[key] = row[col]
        for key in MEASUREMENT_VARS + ["pressure_mmHg", "o2_mf", "n2_mf", "co_mf", "he_mf"]:
            rec[key + "_val"], rec[key + "_approx"] = parse_measured(rec[key])
        rec["missing_marker_bytes"] = sum(1 for v in row.values() if v and MISSING_BYTE in v)
        rec["approx_fields"] = [k for k in MEASUREMENT_VARS + ["pressure_mmHg"]
                                if rec.get(k + "_approx")]
        records.append(rec)
    return records


def completeness_tiers(rec):
    """Flag records by how many of the four core measurements are reported."""
    present = [v for v in MEASUREMENT_VARS if not is_missing(rec[v])]
    return len(present)


# ---------------------------------------------------------------------------
# 2. File inventory
# ---------------------------------------------------------------------------
def file_inventory():
    entries = []
    for dirpath, dirnames, filenames in os.walk(RAW_FLEX):
        for name in sorted(filenames):
            if name.endswith(".zip"):
                continue  # huge archives; listed separately
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT)
            entries.append((rel, os.path.getsize(path)))
    archives = []
    for dirpath, dirnames, filenames in os.walk(RAW_FLEX):
        for name in sorted(filenames):
            if name.endswith(".zip"):
                archives.append(
                    (os.path.relpath(os.path.join(dirpath, name), ROOT),
                     os.path.getsize(os.path.join(dirpath, name)))
                )
    return entries, archives


def run_files_by_test():
    """Map FLEX identifier -> list of telemetry/settings file suffixes."""
    out = defaultdict(list)
    part01 = os.path.join(RAW_FLEX, "part-01")
    for name in sorted(os.listdir(part01)):
        m = re.match(r"^([0-9A-Z]+?)(?:_(.+))?\.txt$", name)
        if not m:
            continue
        test, suffix = m.group(1), m.group(2) or "(main)"
        # base test files have no suffix; series files carry a suffix
        if suffix != "(main)":
            base = re.sub(r"[A-Z]$", "", name).replace(".txt", "")
            test = re.sub(r"_.+$", "", base)
        out[test].append(name)
    return out


# ---------------------------------------------------------------------------
# 3. Audit computations
# ---------------------------------------------------------------------------
def audit():
    records = load_records()
    fuels = ["Methanol", "Heptane"]
    by_fuel = {f: [r for r in records if r["fuel"].strip() == f] for f in fuels}

    # --- duplicate detection -------------------------------------------------
    exact_dupes = [k for k, v in Counter(
        tuple(r[c] for c in ALL_VARS) for r in records).items() if v > 1]
    test_no_dupes = [k for k, v in Counter(
        r["flex_test_no"] for r in records).items() if v > 1]
    ident_counts = Counter(r["flex_identifier"] for r in records)
    ident_dupes = {k: v for k, v in ident_counts.items() if v > 1}
    # repeated measurement signature (same fuel/conditions/size, ignoring IDs)
    sig_counts = Counter(
        (r["fuel"].strip(), r["pressure_mmHg"].strip(), r["o2_mf"].strip(),
         r["n2_mf"].strip(), r["co_mf"].strip(), r["he_mf"].strip(),
         r["d0_mm"].strip(), r["d_ext_mm"].strip(), r["burn_rate"].strip(),
         r["burn_time_s"].strip())
        for r in records)
    sig_dupes = {k: v for k, v in sig_counts.items() if v > 1}

    # --- per-fuel / per-variable missingness ---------------------------------
    missing_rows = []
    for fuel in fuels + ["All"]:
        subset = records if fuel == "All" else by_fuel[fuel]
        for key in ALL_VARS:
            n_missing = sum(1 for r in subset if is_missing(r[key]))
            markers = sum(r["missing_marker_bytes"] for r in subset
                          if is_missing(r[key]))
            empty_only = n_missing - markers
            missing_rows.append(dict(
                fuel=fuel, variable=COLUMNS[key], key=key,
                n_records=len(subset), n_present=len(subset) - n_missing,
                n_missing=n_missing,
                pct_missing=f"{100.0 * n_missing / len(subset):.1f}",
                n_missing_empty_field=empty_only,
                n_missing_0x96_byte=markers,
            ))

    # --- fuel comparison inventory -------------------------------------------
    comparison_rows = []
    for fuel in fuels + ["All"]:
        subset = records if fuel == "All" else by_fuel[fuel]
        n = len(subsubset := subset)
        complete_core = sum(1 for r in subset if completeness_tiers(r) == 4)
        partial_core = sum(1 for r in subset if 0 < completeness_tiers(r) < 4)
        no_meas = sum(1 for r in subset if completeness_tiers(r) == 0)
        outcomes = Counter(r["test_end"].strip() for r in subset)
        dup_ids = [k for k, v in Counter(r["flex_identifier"] for r in subset).items() if v > 1]
        comparison_rows.append(dict(
            fuel=fuel, total_records=n,
            records_with_initial_diameter=sum(1 for r in subset if not is_missing(r["d0_mm"])),
            records_with_extinction_diameter=sum(1 for r in subset if not is_missing(r["d_ext_mm"])),
            records_with_burning_rate=sum(1 for r in subset if not is_missing(r["burn_rate"])),
            records_with_burn_time=sum(1 for r in subset if not is_missing(r["burn_time_s"])),
            records_complete_core_measurements=complete_core,
            records_partial_core_measurements=partial_core,
            records_no_measurements=no_meas,
            records_with_approx_flagged_measurement=sum(1 for r in subset if r["approx_fields"]),
            outcome_extinction=outcomes.get("Extinction", 0),
            outcome_disruption=outcomes.get("Disruption", 0),
            outcome_completion=outcomes.get("Completion", 0),
            outcome_blank=outcomes.get("", 0),
            duplicate_identifiers=";".join(sorted(dup_ids)),
            missing_test_gmt=sum(1 for r in subset if is_missing(r["test_gmt"])),
            missing_test_date=sum(1 for r in subset if is_missing(r["test_date"])),
            pressure_min_mmHg=fmt_range([r["pressure_mmHg_val"] for r in subset]),
            o2_mf_distinct=";".join(sorted({r["o2_mf"].strip() for r in subset if not is_missing(r["o2_mf"])})),
            date_range=(
                f"{min(parse_date(r['test_date']) for r in subset if parse_date(r['test_date']))} to "
                f"{max(parse_date(r['test_date']) for r in subset if parse_date(r['test_date']))}"
            ) if any(parse_date(r["test_date"]) for r in subset) else "",
        ))

    # --- condition coverage ---------------------------------------------------
    coverage_rows = []
    for dim, colkey, unit in [
        ("O2 mole fraction", "o2_mf", "mole fraction"),
        ("N2 mole fraction", "n2_mf", "mole fraction"),
        ("CO2 mole fraction", "co_mf", "mole fraction"),
        ("He mole fraction", "he_mf", "mole fraction"),
    ]:
        vals = defaultdict(lambda: {"Methanol": 0, "Heptane": 0})
        for r in records:
            if is_missing(r[colkey]):
                continue
            vals[r[colkey].strip()][r["fuel"].strip()] += 1
        for value, counts in sorted(vals.items()):
            coverage_rows.append(dict(
                dimension=f"{dim} ({unit})", value=value,
                n_methanol=counts["Methanol"], n_heptane=counts["Heptane"],
                n_total=counts["Methanol"] + counts["Heptane"],
                note="as reported; not converted",
            ))

    # pressure bands, purely as a reporting aid on the reported mmHg values
    def pressure_band(v):
        if v is None:
            return "missing"
        if v < 560:
            return "<560 mmHg"
        if v < 800:
            return "560-800 mmHg"
        if v <= 2100:
            return "800-2100 mmHg"
        return ">2100 mmHg"

    band_counts = defaultdict(lambda: {"Methanol": 0, "Heptane": 0})
    for r in records:
        b = pressure_band(r["pressure_mmHg_val"])
        band_counts[b][r["fuel"].strip()] += 1
    for band in ["<560 mmHg", "560-800 mmHg", "800-2100 mmHg", ">2100 mmHg", "missing"]:
        c = band_counts.get(band, {"Methanol": 0, "Heptane": 0})
        coverage_rows.append(dict(
            dimension="Ambient pressure band (reported mmHg, bands are reporting aids only)",
            value=band, n_methanol=c["Methanol"], n_heptane=c["Heptane"],
            n_total=c["Methanol"] + c["Heptane"],
            note="no conversion to any other pressure unit performed",
        ))

    # gas-mixture families as reported (O2/N2/CO2/He tuple)
    fam_counts = defaultdict(lambda: {"Methanol": 0, "Heptane": 0})
    for r in records:
        fam = (
            r["o2_mf"].strip(), r["n2_mf"].strip(),
            r["co_mf"].strip(), r["he_mf"].strip(),
        )
        fam_counts[fam][r["fuel"].strip()] += 1
    for fam, c in sorted(fam_counts.items()):
        label = "O2/N2/CO2/He = " + "/".join(fam)
        coverage_rows.append(dict(
            dimension="Ambient gas mixture as reported (O2/N2/CO2/He mole fractions)",
            value=label, n_methanol=c["Methanol"], n_heptane=c["Heptane"],
            n_total=c["Methanol"] + c["Heptane"],
            note="mole fractions reported in the source table",
        ))

    # --- measured-value descriptions (descriptive only, no conversion) --------
    stats = {}
    for fuel in fuels:
        subsets = by_fuel[fuel]
        stats[fuel] = {v: describe([r[v + "_val"] for r in subsets]) for v in MEASUREMENT_VARS}
        stats[fuel]["pressure_mmHg"] = describe([r["pressure_mmHg_val"] for r in subsets])

    # --- composition sanity (sums of reported mole fractions) -----------------
    sum_flags = Counter()
    for r in records:
        parts = [r[k + "_val"] for k in ["o2_mf", "n2_mf", "co_mf", "he_mf"]]
        if any(p is None for p in parts):
            sum_flags["incomplete composition"] += 1
            continue
        total = sum(parts)
        if abs(total - 1.0) <= 1e-9:
            sum_flags["sums to 1.000"] += 1
        elif abs(total - 1.0) <= 0.02:
            sum_flags[f"sums to {total:.3f} (within 0.02 of 1)"] += 1
        else:
            sum_flags[f"sums to {total:.3f} (off by >0.02)"] += 1

    # --- physical-plausibility flags (values kept as reported, only flagged) --
    implausible = dict(
        pressure_zero=[(r["flex_test_no"], r["flex_identifier"], r["fuel"]) for r in records
                       if r["pressure_mmHg_val"] == 0.0],
        extinction_diameter_zero=[(r["flex_test_no"], r["flex_identifier"], r["fuel"])
                                  for r in records if r["d_ext_mm_val"] == 0.0],
        d_ext_gt_d0=[(r["flex_test_no"], r["flex_identifier"], r["fuel"],
                      r["d0_mm_val"], r["d_ext_mm_val"])
                     for r in records
                     if r["d0_mm_val"] not in (None, 0) and r["d_ext_mm_val"] is not None
                     and r["d_ext_mm_val"] > r["d0_mm_val"] + 1e-9],
    )

    # --- outcome label vs recorded extinction diameter (kept separate) --------
    consistency = {
        "outcome_extinction_with_d_ext": sum(
            1 for r in records
            if r["test_end"].strip() == "Extinction" and not is_missing(r["d_ext_mm"])),
        "outcome_extinction_missing_d_ext": sum(
            1 for r in records
            if r["test_end"].strip() == "Extinction" and is_missing(r["d_ext_mm"])),
        "outcome_disruption_with_d_ext": sum(
            1 for r in records
            if r["test_end"].strip() == "Disruption" and not is_missing(r["d_ext_mm"])),
        "outcome_completion_with_d_ext": sum(
            1 for r in records
            if r["test_end"].strip() == "Completion" and not is_missing(r["d_ext_mm"])),
    }

    # --- pressure band x mixture family cross-tab (confounding check) ---------
    cross = defaultdict(lambda: {"Methanol": 0, "Heptane": 0})
    for r in records:
        fam = "O2={}/N2={}/CO2={}/He={}".format(
            r["o2_mf"].strip() or "?",
            r["n2_mf"].strip() or "?",
            r["co_mf"].strip() or "?",
            r["he_mf"].strip() or "?")
        cross[(pressure_band(r["pressure_mmHg_val"]), fam)][r["fuel"].strip()] += 1
    cross_rows = [dict(
        dimension=("pressure band x ambient mixture (reported values only)"),
        value=f"{band} | {fam}",
        n_methanol=c["Methanol"], n_heptane=c["Heptane"],
        n_total=c["Methanol"] + c["Heptane"],
        note="no unit conversion; bands are reporting aids on the reported mmHg values",
    ) for (band, fam), c in sorted(cross.items())]

    # --- linkage ---------------------------------------------------------------
    telemetry = run_files_by_test()
    linked = {}
    for r in records:
        ident = r["flex_identifier"].strip()
        linked[ident] = bool(telemetry.get(ident))
    linked_ids = sorted(i for i, ok in linked.items() if ok)
    unlinked_records = sum(1 for ok in linked.values() if not ok)

    results = dict(
        records=records, by_fuel=by_fuel, comparison_rows=comparison_rows,
        missing_rows=missing_rows,
        coverage_rows=coverage_rows + cross_rows,
        stats=stats,
        exact_dupes=exact_dupes, test_no_dupes=test_no_dupes,
        ident_dupes=ident_dupes, sig_dupes=sig_dupes, sum_flags=sum_flags,
        implausible=implausible, consistency=consistency,
        linked_ids=linked_ids, unlinked_records=unlinked_records,
        telemetry=telemetry,
    )
    return results


# ---------------------------------------------------------------------------
# 4. Emit CSV deliverables
# ---------------------------------------------------------------------------
def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    fuels = ["Methanol", "Heptane"]
    res = audit()

    write_csv(os.path.join(OUT_DIR, "fuel_comparison_inventory.csv"),
              res["comparison_rows"], list(res["comparison_rows"][0].keys()))

    write_csv(os.path.join(OUT_DIR, "missing_data_report.csv"),
              res["missing_rows"], list(res["missing_rows"][0].keys()))

    write_csv(os.path.join(OUT_DIR, "condition_coverage.csv"),
              res["coverage_rows"], list(res["coverage_rows"][0].keys()))

    # stash computed context for the markdown reports (kept out of data/raw)
    import json
    ctx = dict(
        n_records=len(res["records"]),
        n_methanol=len(res["by_fuel"]["Methanol"]),
        n_heptane=len(res["by_fuel"]["Heptane"]),
        exact_dupes=len(res["exact_dupes"]),
        test_no_dupes=len(res["test_no_dupes"]),
        ident_dupes=res["ident_dupes"],
        sig_dupes={str(k): v for k, v in res["sig_dupes"].items()},
        sum_flags=dict(res["sum_flags"]),
        implausible=res["implausible"],
        consistency=res["consistency"],
        linked_ids=res["linked_ids"],
        unlinked_records=res["unlinked_records"],
        stats=res["stats"],
        outcome_by_fuel={
            fuel: dict(Counter(r["test_end"].strip() for r in res["by_fuel"][fuel]))
            for fuel in fuels},
    )
    with open(os.path.join(OUT_DIR, "_audit_context.json"), "w") as fh:
        json.dump(ctx, fh, indent=2, default=str)

    print(f"records: {len(res['records'])} "
          f"(Methanol {len(res['by_fuel']['Methanol'])}, "
          f"Heptane {len(res['by_fuel']['Heptane'])})")
    print(f"exact duplicate rows: {len(res['exact_dupes'])}; "
          f"duplicate test numbers: {len(res['test_no_dupes'])}; "
          f"duplicate identifiers: {res['ident_dupes']}")
    print(f"repeated condition/measurement signatures: {len(res['sig_dupes'])}")
    print("composition sums:", dict(res["sum_flags"]))
    print(f"identifiers with per-run telemetry: {res['linked_ids']} "
          f"({res['unlinked_records']} records without)")

    return res


if __name__ == "__main__":
    main()
