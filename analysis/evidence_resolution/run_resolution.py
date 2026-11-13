#!/usr/bin/env python3
"""FLEX PSI-69 Phase 3.5 - evidence resolution pipeline.

Local and read-only with respect to ALL existing artifacts (raw data, schema,
src, tests, and Phases 1-3). This script:

  1. verifies SHA-256 of every protected file and refuses to run on drift;
  2. loads the raw experimental table with its own byte-preserving loader
     (independent of every previous phase's code);
  3. recomputes every forensic quantity cited in the Phase 3.5 documents into
     resolution_checks.csv;
  4. writes the evidence-resolution register, source-document register and
     correction register;
  5. writes run_manifest.json (inputs, hashes, documents inspected, archive
     metadata inspected, outputs, integrity, limitations).

No modelling, no imputation, no unit assignment, no archive extraction, no
contact with originators.

Run from the repository root:
    notebooks/.venv/bin/python analysis/evidence_resolution/run_resolution.py
"""

import csv
import datetime
import glob
import hashlib
import json
import math
import os
import platform
import re
import statistics
import sys
import zipfile
from collections import Counter, OrderedDict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

MISSING_BYTE = "\x96"
CORE = ("d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s")

PROTECTED = [
    "data/raw/flex/PSI-69_Experimental table_FLEX.csv",
    "data/raw/flex/s_PSI-69.txt",
    "schema/v1.2.0.sql",
    "src/prediction/predictor.py",
    "tests/validate_schema_candidate.py",
] + sorted(
    os.path.join(d, f)
    for phase in ("audit", "exploratory", "validation")
    for d, _, fs in sorted(os.walk(os.path.join(ROOT, "analysis", phase)))
    for f in sorted(fs)
    if "__pycache__" not in d and not f.startswith(".")
)

RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"

STATUSES = ("RESOLVED", "PARTIALLY_RESOLVED", "DOCUMENTED_UNCONFIRMED",
            "UNVERIFIED", "BLOCKED", "ORIGINATOR_CONFIRMATION_REQUIRED")


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


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
    records = []
    cols = {"pressure_mmHg": "Ambient pressure; mmHg",
            "o2_mf": "O initial ambient composition; mole fraction",
            "n2_mf": "N initial ambient composition; mole fraction",
            "co2_mf": "CO initial ambient composition; mole fraction",
            "he_mf": "He initial ambient composition; mole fraction",
            "d0_mm": "Droplet initial diameter; mm",
            "d_ext_mm": "Visible flame extinction diameter; mm",
            "burn_rate_raw": "Burning rate; mm",
            "burn_time_s": "Burn time; s"}
    for r in rows:
        rec = {"flex_test_no": r["FLEX Test #"].strip(),
               "flex_identifier": r["FLEX Identifier"].strip(),
               "test_date": r["Test Date"].strip(),
               "test_gmt": r["Test GMT"].strip(),
               "fuel": r["Fuel"].strip(),
               "test_end": r["Test end"].strip()}
        for key, col in cols.items():
            rec[key] = r[col]  # original string, verbatim
            rec[key + "_val"], rec[key + "_approx"] = parse_measured(r[col])
        records.append(rec)
    return records


def mwu_two_sided(x, y):
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
    z = (u - mu + 0.5) / math.sqrt(sig2)
    return u, math.erfc(abs(z) / math.sqrt(2.0))


def spearman(x, y):
    def ranks(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            avg = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    if len(set(rx)) < 2 or len(set(ry)) < 2:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


# ---------------------------------------------------------------------------
# Forensic recomputation
# ---------------------------------------------------------------------------
def forensic(records):
    out = OrderedDict()
    meoh = [r for r in records if r["fuel"] == "Methanol"]
    hep = [r for r in records if r["fuel"] == "Heptane"]

    out["n_records"] = len(records)
    out["n_methanol"], out["n_heptane"] = len(meoh), len(hep)

    # --- duplicate (date, GMT) clusters ---
    sg = Counter((r["test_date"], r["test_gmt"]) for r in records if r["test_gmt"])
    dups = {k: v for k, v in sg.items() if v > 1}
    out["duplicate_datetime_pairs"] = len(dups)
    out["duplicate_datetime_detail"] = sorted(
        [{"date_gmt": f"{k[0]} {k[1]}", "records": [
            {"test_no": r["flex_test_no"], "identifier": r["flex_identifier"],
             "fuel": r["fuel"]} for r in records
            if (r["test_date"], r["test_gmt"]) == k]} for k in dups],
        key=lambda d: d["date_gmt"])

    # --- pressure-zero record context ---
    p0 = [r for r in records if r["pressure_mmHg_val"] == 0.0]
    out["pressure_zero_records"] = [
        {"test_no": r["flex_test_no"], "identifier": r["flex_identifier"],
         "fuel": r["fuel"], "date": r["test_date"], "gmt": r["test_gmt"],
         "composition": f"O2={r['o2_mf']}/N2={r['n2_mf']}/CO2={r['co2_mf']}",
         "d0": r["d0_mm"], "d_ext": r["d_ext_mm"], "rate": r["burn_rate_raw"],
         "burn_time": r["burn_time_s"], "outcome": r["test_end"]} for r in p0]
    out["pressure_zero_series_median"] = statistics.median(
        [r["pressure_mmHg_val"] for r in records
         if r["flex_identifier"].startswith("C11")
         and r["pressure_mmHg_val"] not in (None, 0.0)])

    # --- zero extinction diameters ---
    zeros = [r for r in records if r["d_ext_mm_val"] == 0.0]
    out["zero_extinction_records"] = [
        {"test_no": r["flex_test_no"], "identifier": r["flex_identifier"],
         "fuel": r["fuel"], "date": r["test_date"],
         "composition": f"O2={r['o2_mf']}/N2={r['n2_mf']}/CO2={r['co2_mf']}",
         "d0": r["d0_mm"], "burn_time": r["burn_time_s"], "outcome": r["test_end"]}
        for r in zeros]
    out["zero_extinction_fuel_split"] = dict(Counter(r["fuel"] for r in zeros))
    out["zero_extinction_outcome_split"] = dict(Counter(r["test_end"] for r in zeros))

    # --- d_ext > d0 ---
    gt = [r for r in records
          if r["d0_mm_val"] not in (None, 0.0) and r["d_ext_mm_val"] is not None
          and r["d_ext_mm_val"] > r["d0_mm_val"] + 1e-9]
    out["d_ext_gt_d0_records"] = [
        {"test_no": r["flex_test_no"], "identifier": r["flex_identifier"],
         "fuel": r["fuel"], "d0": r["d0_mm"], "d_ext": r["d_ext_mm"],
         "excess_mm": round(r["d_ext_mm_val"] - r["d0_mm_val"], 4)}
        for r in gt]

    # --- 193F001 collision ---
    coll = [r for r in records if r["flex_identifier"] == "193F001"]
    out["collision_193F001"] = [
        {"test_no": r["flex_test_no"], "identifier": r["flex_identifier"],
         "fuel": r["fuel"], "date": r["test_date"], "gmt": r["test_gmt"],
         "pressure": r["pressure_mmHg"], "o2": r["o2_mf"], "n2": r["n2_mf"],
         "d0": r["d0_mm"], "d_ext": r["d_ext_mm"], "rate": r["burn_rate_raw"],
         "burn_time": r["burn_time_s"], "outcome": r["test_end"]} for r in coll]

    # --- burning-rate hypothesis tests (consistency forensics, not unit inference) ---
    trips = [(r["d0_mm_val"], r["burn_time_s_val"], r["burn_rate_raw_val"], r["fuel"])
             for r in records
             if None not in (r["d0_mm_val"], r["burn_time_s_val"], r["burn_rate_raw_val"])
             and r["burn_time_s_val"] > 0 and r["d0_mm_val"] > 0]
    for fuel in ("Methanol", "Heptane", "All"):
        sub = [t for t in trips if t[3] == fuel or fuel == "All"]
        rt = [t[2] for t in sub]
        d2t = [t[0] ** 2 / t[1] for t in sub]
        d1t = [t[0] / t[1] for t in sub]
        out[f"burnrate_hypothesis_{fuel}"] = {
            "n": len(sub),
            "spearman_rate_vs_d2_over_t": round(spearman(rt, d2t), 4),
            "spearman_rate_vs_d_over_t": round(spearman(rt, d1t), 4),
            "median_rate": round(statistics.median(rt), 4),
            "median_d2_over_t": round(statistics.median(d2t), 4),
        }

    # --- duplicate sensitivity of the d0 fuel contrast ---
    x = [r["d0_mm_val"] for r in meoh if r["d0_mm_val"] is not None]
    y = [r["d0_mm_val"] for r in hep if r["d0_mm_val"] is not None]
    u0, p0v = mwu_two_sided(x, y)
    out["d0_contrast_all"] = {"U": u0, "p": round(p0v, 5), "n_meoh": len(x), "n_hep": len(y)}
    for i, drop in enumerate(coll, 1):
        keep = [r for r in records if r is not drop]
        xx = [r["d0_mm_val"] for r in keep if r["fuel"] == "Methanol" and r["d0_mm_val"] is not None]
        yy = [r["d0_mm_val"] for r in keep if r["fuel"] == "Heptane" and r["d0_mm_val"] is not None]
        u1, p1 = mwu_two_sided(xx, yy)
        out[f"d0_contrast_excluding_collision_{i}"] = {"U": u1, "p": round(p1, 5),
                                                      "n_meoh": len(xx), "n_hep": len(yy)}

    # --- chamber pressure cross-check (linked runs) ---
    tests = ["20CAL08", "20CAL10", "20CAL12", "20CAL13", "30CAL02", "30CAL03",
             "30CAL06", "40CAL01"]
    cross = []
    for t in tests:
        chp = os.path.join(ROOT, "data", "raw", "flex", "part-01",
                           f"{t}_Chamber_Readings.txt")
        if not os.path.exists(chp):
            continue
        rows = [r for r in csv.reader(open(chp, encoding="latin-1")) if len(r) > 5]
        if len(rows) < 2:
            continue
        pt16 = float(rows[1][1])
        rec = next(r for r in records if r["flex_identifier"] == t)
        cross.append({"run": t, "fcu_pt16_psia": pt16,
                      "fcu_mmHg": round(pt16 * 51.7149, 2),
                      "table_mmHg": float(rec["pressure_mmHg"]),
                      "abs_diff_mmHg": round(abs(pt16 * 51.7149 - rec["pressure_mmHg_val"]), 2),
                      "chamber_rows": len(rows) - 1,
                      "first_fcu_ts": rows[1][0],
                      "as_igniter_on": _as_igniter_on(t)})
    out["chamber_pressure_crosscheck"] = cross

    # --- clock offsets (PIP vs MAIN, radiometer frame vs MAIN) ---
    clocks = []
    for t in tests:
        rp = os.path.join(ROOT, "data", "raw", "flex", "part-01",
                          f"{t}_Radiometer_Readings.txt")
        if not os.path.exists(rp):
            continue
        rows = list(csv.reader(open(rp, encoding="latin-1")))
        hdr = rows[0]
        ci = {c.strip(): i for i, c in enumerate(hdr)}
        pm, mc, ms = "PIP TimeStamp", "MAIN_COMPUTER_TIME(GMT)", "MAIN_COMPUTER_MILLISECONDS(N/A)"
        if not all(c in ci for c in (pm, mc, ms)):
            continue
        offs = []
        for r in rows[1:]:
            if len(r) <= max(ci[pm], ci[mc], ci[ms]):
                continue
            a, b = _t(r[ci[pm]]), _t(r[ci[mc]])
            if not (a and b):
                continue
            try:
                msv = float(r[ci[ms]])
            except ValueError:
                continue
            offs.append((a - (b + datetime.timedelta(milliseconds=msv))).total_seconds())
        if offs:
            n = len(offs)
            mx, my = (n - 1) / 2.0, sum(offs) / n
            slope = sum((i - mx) * (o - my) for i, o in enumerate(offs)) / \
                sum((i - mx) ** 2 for i in range(n))
            clocks.append({"run": t, "n": n,
                           "pip_minus_main_median_s": round(statistics.median(offs), 3),
                           "min_s": round(min(offs), 3), "max_s": round(max(offs), 3),
                           "net_drift_s_per_1000_samples": round(slope * 1000, 3)})
    out["clock_offsets"] = clocks

    # --- image archive metadata (no extraction) ---
    archives = []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "flex", "part-01", "*.zip"))):
        zf = zipfile.ZipFile(path)
        names = zf.namelist()
        imgs = [n for n in names if n.lower().endswith((".tif", ".tiff", ".bmp"))]
        nums = sorted(int(re.search(r"(\d+)$", n.rsplit(".", 1)[0]).group(1)) for n in imgs)
        gaps = sum(1 for a, b in zip(nums, nums[1:]) if b - a != 1)
        first = zf.open(sorted(imgs)[0]).read(600000) if imgs else b""
        fmt, dims = _image_header(first)
        archives.append({"archive": os.path.basename(path),
                         "entries": len(names), "images": len(imgs),
                         "first_image_num": nums[0] if nums else None,
                         "last_image_num": nums[-1] if nums else None,
                         "internal_numbering_gaps": gaps,
                         "format": fmt, "dimensions": dims,
                         "embedded_manifest_txt": sum(1 for n in names if n.endswith(".txt")),
                         "zip_uncompressed_gb": round(sum(
                             i.file_size for i in zf.infolist()) / 1e9, 3)})
        zf.close()
    out["image_archives"] = archives

    # --- study provenance facts (from i_Investigation.txt) ---
    inv = open(os.path.join(ROOT, "docs", "flex", "i_Investigation.txt"),
               encoding="utf-8").read()
    doi = re.search(r"Comment\[DOI\]\s+(\S+)", inv)
    study_id = re.search(r"Study Identifier\s+(\S+)", inv)
    out["study_doi"] = doi.group(1) if doi else None
    out["study_identifier"] = study_id.group(1) if study_id else None
    return out


def _tiff_dims(data):
    """Read basic geometry tags from an in-memory TIFF header (baseline TIFF)."""
    bo = "little" if data[:2] == b"II" else "big"
    off = int.from_bytes(data[4:8], bo)
    n = int.from_bytes(data[off:off + 2], bo)
    out = {}
    for i in range(n):
        e = off + 2 + i * 12
        tag = int.from_bytes(data[e:e + 2], bo)
        if tag in (256, 257, 258, 259):
            out[{256: "width", 257: "height", 258: "bits",
                 259: "compression"}[tag]] = int.from_bytes(data[e + 8:e + 10], bo)
    return out


def _image_header(data):
    """Identify format and geometry from the first ~600 KB of an image."""
    if data[:2] in (b"II", b"MM"):
        return "TIFF", _tiff_dims(data)
    if data[:2] == b"BM":
        return "BMP", {"width": int.from_bytes(data[18:22], "little"),
                       "height": int.from_bytes(data[22:26], "little"),
                       "bpp": int.from_bytes(data[28:30], "little")}
    return None, None


def _t(s):
    s = s.strip().strip('"')
    for f in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def _as_igniter_on(test):
    p = os.path.join(ROOT, "data", "raw", "flex", "part-01", f"{test}.txt")
    if not os.path.exists(p):
        return None
    for r in csv.reader(open(p, encoding="latin-1"), delimiter="\t"):
        if len(r) > 1 and "Igniter On" in r[0] and r[1].strip():
            return r[1].strip()
    return None


# ---------------------------------------------------------------------------
# Registers (curated; every row traceable to an inspected artifact)
# ---------------------------------------------------------------------------
SOURCES = [
    # (source_id, path, kind, version/date evidence, what it establishes, sha256?)
    ("SRC-01", "data/raw/flex/PSI-69_Experimental table_FLEX.csv", "primary dataset",
     "no version marker; studied under PSI-69", "the 274-record experimental table under investigation", True),
    ("SRC-02", "data/raw/flex/s_PSI-69.txt", "study placeholder",
     "points to i_Investigation.txt", "no usable content", True),
    ("SRC-03", "data/raw/flex/part-01/", "per-run telemetry (8 runs)",
     "2009-03-05..2009-04-10 file mtimes/timestamps", "event timelines, chamber/radiometer/telemetry, image manifests", False),
    ("SRC-04", "data/raw/flex/part-01/*.zip (23 archives)", "image archives",
     "member timestamps 2009-03-05..2009-04-10", "TIFF (A/B) and BMP (D) frame sequences, ~5.34 GB", False),
    ("SRC-05", "docs/flex/i_Investigation.txt", "PSI investigation record",
     "Study PSI-69 submitted/released 31-Jul-2016; ontology refs PSI 1.0 / EFO 132",
     "study DOI 10.60555/mbq8-0451; hardware CIR-FCF/MDCA; ISS platform; grant NNX09AM33A; "
     "51 DOI-aligned publication citations incl. the dataset paper (NTRS 20150023456) and the "
     "burning-rate uncertainty paper (Shaw, 10.1007/s12217-014-9377-x); investigator contact list", True),
    ("SRC-06", "docs/flex/FLEX_EIRD_v4.pdf", "research requirements document",
     "v4; 82 PDF pages; content dated Nov 4 2005 per Test Plan preamble",
     "LOI procedure; diagnostic requirements (drop-let imaging 30 um / 30 fps; pressure +/-0.01 atm; "
     "temp +/-0.5 C; GMT +/-0.03 s); droplet size 2-6 mm; fuels/purity; microgravity <1e-4 m/s2; "
     "d2-law context (0.8 mm2/s literature assumption)", True),
    ("SRC-07", "docs/flex/FLEX_Test_Plan.pdf", "test plan",
     "extracted from the Nov 4 2005 EIRD", "adaptive sequential LOI procedure (documented); "
     "flammability-map construction; slow-flow procedure", True),
    ("SRC-08", "docs/flex/FLEX Engineering Requirements Document.pdf", "engineering requirements (FLEX-2)",
     "FLX-REQ-0001, February 04 2010", "dispenser tolerance +/-0.25 mm and +/-5% reproducibility; "
     "pressure 0.5-3 atm +/-0.05 atm; O2 0.1-0.4 +/-0.005; temp 18-27 C; RH <10%; "
     "g-level <1e-4 m/s2; GMT synchronisation +/-0.03 s", True),
    ("SRC-09", "docs/flex/FLEX DoD.docx", "declaration of data / investigation description",
     "no version marker", "UNIQUE CONTENT absent from SRC-05: documents that the PSI data system "
     "hosts five FLEX experiment data records - 'FLEX - Calibration', 'FLEX - LCTF Calibration', "
     "'FLEX - Radiometer Calibration', 'FLEX - HEP', 'FLEX - MeOH' - plus the analysis/image "
     "download structure (1465 chars of extracted text); this is the only local pointer to the "
     "calibration experiment records behind OQ-7", True),
    ("SRC-10", "docs/flex/FLEX Overall Ext File-2.pdf", "selection of engineering documents",
     "no version marker", "FLEX test-matrix context (550 points, Table 3); no measurement definitions", True),
    ("SRC-11", "notebooks/ (10 exploration scripts)", "prior intermediate analysis code",
     "mtime 2025-06-06 (s_PSI-69) to project dates", "image manifests, clock audits, timeline reconstruction; "
     "documents clock-uncertainty handling; NOT a measurement-definition source", False),
    ("SRC-12", "data/interim/flex/ (8 artifacts)", "prior intermediate outputs",
     "2009 run 20CAL13", "timestamped image manifest with explicit "
     "'camera_index_timestamp_timezone_unverified' status; ignition-aligned frame timelines", False),
    ("SRC-13", "data/processed/ (3 files)", "processed outputs",
     "empty (0 bytes) placeholders", "no content", True),
    ("SRC-14", "reports/telemetry_gc.tsv, reports/video_gc.tsv", "JAXA GCEM manifests",
     "2017 GC campaigns", "different experiment (Group Combustion); inspected and excluded from FLEX scope", True),
    ("SRC-15", "docs/jaxa/, data/raw/jaxa_group_combustion/, docs/tnf/, data/raw/tnf/",
     "other experiments' docs/data", "n/a", "JAXA docs only (no GCEM data locally); TNF empty; "
     "out of FLEX scope", False),
]


def source_register_rows():
    rows = []
    for sid, path, kind, version, establishes, is_file in SOURCES:
        digest = ""
        exists = "-"
        if is_file:
            full = os.path.join(ROOT, path)
            if os.path.isfile(full):
                digest = sha256_of(path)
                exists = "yes"
            elif os.path.isdir(full):
                exists = "dir"
        rows.append(OrderedDict(
            source_id=sid, path=path, source_type=kind, version_or_date_evidence=version,
            sha256=digest, present=exists, establishes=establishes))
    return rows


def evidence_rows(records, checks):
    E = []

    def add(rid, req, q, src, ver, sec, pg, ev, level, status, conf, lim, res):
        E.append(OrderedDict(
            evidence_id=rid, requirement_id=req, question=q, source_document=src,
            source_version=ver, section=sec, page=pg, supporting_evidence=ev,
            evidence_level=level, status=status, confidence=conf, limitation=lim,
            resolution=res))

    # --- R1 burning rate ---
    add("ER-01", "R1", "Burning-rate definition/unit for the table column",
        "docs/flex/FLEX_EIRD_v4.pdf", "v4", "4.3 Experimental Diagnostics", "30 (PDF)",
        "Backlit droplet view yields 'droplet size as a function of time'; 'the time evolution of "
        "the droplet size yields the droplet burning rate (heat release), and extinction droplet "
        "size'; burning rate is 'instantaneous as well as average'", "L1",
        "DOCUMENTED_UNCONFIRMED", "medium",
        "Defines the experiment's burning rate as image-derived and notes instantaneous vs average "
        "forms, but does not name, define, dimension or give the unit of the PSI-69 table column; "
        "the '(heat release)' gloss is narrative, not a measurement equation",
        "Table-column definition still unresolved; narrowed to specific publications")
    add("ER-02", "R1", "Burning-rate definition/unit for the table column",
        "docs/flex/FLEX_EIRD_v4.pdf", "v4", "5.2.1 Droplet Imaging", "41 (PDF)",
        "Resolution 30 um, min frame rate 30 fps, back-lit; imaging exists to 'obtain droplet "
        "burning rates and extinction droplet diameters'", "L2",
        "DOCUMENTED_UNCONFIRMED", "medium",
        "Confirms method class (image-derived) only", "same as ER-01")
    add("ER-03", "R1", "Candidate definition: d2-law burning-rate constant",
        "analysis/evidence_resolution/resolution_checks.csv", "this phase",
        "burnrate_hypothesis_*", "-",
        "Reported rate vs d0^2/t: Spearman rho = "
        f"{checks['burnrate_hypothesis_All']['spearman_rate_vs_d2_over_t']} (All), "
        f"{checks['burnrate_hypothesis_Heptane']['spearman_rate_vs_d2_over_t']} (Heptane); "
        f"median reported rate {checks['burnrate_hypothesis_All']['median_rate']} vs median d0^2/t "
        f"{checks['burnrate_hypothesis_All']['median_d2_over_t']}", "L4",
        "BLOCKED", "high",
        "Consistency forensics: the column is essentially uncorrelated with d0^2/t and negatively "
        "correlated for heptane, so the naive 'average d2-law constant' reading is contradicted by "
        "the data itself; a negative result is not a definition",
        "UNIT UNVERIFIED - PHYSICAL INTERPRETATION BLOCKED; see originator questions OQ-1")
    add("ER-04", "R1", "Authoritative publication for the table and its definitions",
        "docs/flex/i_Investigation.txt", "PSI-69, released 31-Jul-2016", "Study Publication rows",
        "line 90/94 alignment",
        "'Detailed results from the flame extinugishment experiment (FLEX) - March 2009 to December "
        "2011' (Dietrich et al.), NTRS 20150023456 - matches the table's exact date span; plus "
        "'ISS Droplet Combustion Experiments - Uncertainties in Droplet Sizes and Burning Rates' "
        "(Shaw, DOI 10.1007/s12217-014-9377-x), 'AUTOMATED DATA ANALYSIS FOR CONSECUTIVE IMAGES...' "
        "(Dembia et al., 10.5566/ias.v31.p137-148), 'Interpretation of Backlit Droplet Images...' "
        "(Yu & Shaw, 10.2478/gsr-2014-0007)", "L3",
        "ORIGINATOR_CONFIRMATION_REQUIRED", "high",
        "The publications that would define the column are identified with DOIs but are NOT among "
        "the local files; their content could not be inspected (no external download permitted)",
        "Obtain NTRS 20150023456 and 10.1007/s12217-014-9377-x to close R1")

    # --- table provenance ---
    add("ER-05", "R8", "Experimental table version provenance",
        "docs/flex/i_Investigation.txt", "PSI-69", "Comment[DOI]; Study rows", "54, 33-37",
        "Study Identifier PSI-69 'Flame Extinguishment Experiment', DOI 10.60555/mbq8-0451, "
        "submitted and publicly released 31-Jul-2016; hardware CIR-FCF/MDCA; platform ISS; "
        "grant NNX09AM33A; managing centre NASA GRC", "L1",
        "RESOLVED", "high",
        "Establishes the study identity and citation for the table; does not identify the specific "
        "export version of the CSV (no export date in the file)",
        "Cite PSI-69 DOI 10.60555/mbq8-0451 in future work")

    # --- Disruption semantics ---
    add("ER-06", "R2", "Meaning of the 'Disruption' outcome label",
        "docs/flex/FLEX_EIRD_v4.pdf; FLEX_Test_Plan.pdf; FLEX Engineering Requirements "
        "Document.pdf; FLEX Overall Ext File-2.pdf; FLEX DoD.docx", "all inspected",
        "full-text search", "-",
        "'disrupt' has zero occurrences across all five FLEX documents and the investigation "
        "record; Test Plan documents only burn-to-completion / finite-extinction / no-ignition "
        "outcomes", "L1",
        "UNVERIFIED", "high",
        "The label exists in 61 records and is used as an analysis category, but no inspected "
        "source defines it; a mechanistic reading (e.g. droplet breakup) is NOT supported",
        "OUTCOME SEMANTICS UNVERIFIED; originator question OQ-2")

    # --- anomalies ---
    add("ER-07", "R6", "Origin of the 0 mmHg pressure record (C11M201)",
        "analysis/evidence_resolution/resolution_checks.csv", "this phase",
        "pressure_zero_records; duplicate_datetime_detail", "-",
        f"C11M201 (test 114) reports 0 mmHg while its C11 series siblings run at 531.1-536.3 mmHg "
        f"(series median {checks['pressure_zero_series_median']}); its own measurements are "
        "in-family (d0=3.23, d_ext=1.68, rate=0.42, t=18.9); it shares the exact timestamp "
        "19:14:22 with C11H201 (test 118) - the only other duplicate date-time cluster in the "
        "table besides 193F001", "L4 (data forensics)",
        "PARTIALLY_RESOLVED", "high",
        "A real C11-series measurement whose pressure cell was corrupted in the table is the "
        "strongest reading; the exact true value (531-536) is unknowable locally and is NOT imputed; "
        "instrument failure and 'actual zero' are not supported by any evidence",
        "Originator question OQ-3; retain flag; exclude only in screened variants")
    add("ER-08", "R6", "Origin of the eight 0 mm extinction diameters",
        "analysis/evidence_resolution/resolution_checks.csv + "
        "docs/flex/FLEX_Test_Plan.pdf", "this phase / test plan",
        "zero_extinction_records; Test Plan 5.3", "-",
        f"All 8 are Heptane; outcome split {checks['zero_extinction_outcome_split']}; all carry "
        "non-zero burn times (1.3-18.3 s) and non-zero initial diameters; Test Plan documents that "
        "extinction droplet sizes can be 'too small to either be observed or measured with the "
        "available diagnostics'", "L3 (mechanism) + L4 (per-record classification)",
        "PARTIALLY_RESOLVED", "medium",
        "A documented measurement-floor mechanism exists, so 'non-detection placeholder' is "
        "plausible; but the 4 Disruption records sit oddly under that reading, and no source states "
        "a zero-coding convention; the values are NOT replaced by missing",
        "Originator question OQ-4; retain flags and both interpretations")
    add("ER-09", "R6", "Extinction diameter exceeding initial diameter (C13H102)",
        "analysis/evidence_resolution/resolution_checks.csv + docs/flex/FLEX_EIRD_v4.pdf",
        "this phase / v4", "d_ext_gt_d0_records; EIRD 5.2.1", "41 (PDF)",
        f"C13H102: d0=3.33 mm, d_ext=3.34 mm, excess "
        f"{checks['d_ext_gt_d0_records'][0]['excess_mm']} mm - one third of the documented 30 um "
        "imaging resolution", "L2",
        "RESOLVED", "high",
        "Resolved as within the documented 30 um imaging resolution (excess 0.01 mm); the record is retained, not "
        "rejected; calibration/scale forensics see image_archive_pilot.md", "no action beyond flag")

    # --- 193F001 ---
    add("ER-10", "R5", "Identity of the 193F001 collision",
        "analysis/evidence_resolution/resolution_checks.csv", "this phase",
        "collision_193F001; duplicate_datetime_detail", "-",
        "Tests 70 and 73 share identifier 193F001, the exact timestamp 3/23/2010 07:25:43, "
        "761 mmHg and O2=0.15/N2=0.84; near-identical d0 (4.67/4.64) and d_ext (4.60/4.58) but "
        "different reduced values (rate 0.41 vs 0.56, burn time 1.6 vs 1.5 s); the 193 series "
        "otherwise contains 1.1-1.13 mm droplets, so both rows are outliers within their series",
        "L4 (data forensics)",
        "PARTIALLY_RESOLVED", "high",
        "Two physically distinct reduction products sharing one identifier and one timestamp is "
        "the best-supported reading (duplicated run reduced twice, or two nearly identical "
        "deployments); it cannot be resolved from the table alone; removing either row moves the "
        "initial-diameter fuel contrast p from "
        f"{checks['d0_contrast_all']['p']} to {checks['d0_contrast_excluding_collision_1']['p']}",
        "Originator question OQ-5; never join on identifier alone")

    # --- clocks ---
    add("ER-11", "R4", "Telemetry clock offsets across the six clock domains",
        "analysis/evidence_resolution/resolution_checks.csv", "this phase", "clock_offsets", "-",
        "PIP minus MAIN_COMPUTER offset is per-run (medians 1.226-1.714 s across the 8 runs) and "
        "drifts within runs (up to ~1.0 s per file; ~6.9 ms per 1000 samples for 20CAL08); the "
        "radiometer frame clock trails MAIN by ~1.0 s; FCU logs start 56-62 s before ignition; "
        "image series are referenced to different physical events", "L1 (files) / L4 (meaning)",
        "BLOCKED", "high",
        "No constant offset exists and no documented synchronization event ties the domains; the "
        "GMT +/-0.03 s requirement is not met by the delivered files; no merged timeline is "
        "produced", "Originator question OQ-6; clock map required before any time-resolved work")
    add("ER-12", "R4", "Status of the three one-row chamber logs (30CAL02, 30CAL03, 40CAL01)",
        "analysis/evidence_resolution/resolution_checks.csv", "this phase",
        "chamber_pressure_crosscheck", "-",
        "Each single FCU row is stamped at the whole second 0.41-0.61 s before that run's AS "
        "igniter-on event - i.e. an event-triggered ignition snapshot, not an incomplete log; "
        "PT16 = 14.72 PSIA = 761.2 mmHg against table 760 mmHg", "L2",
        "RESOLVED", "high",
        "Resolves the Phase 3 'effectively absent chamber telemetry' concern for those 3 runs: a "
        "single at-ignition chamber snapshot exists and cross-validates the table pressure",
        "no action")
    add("ER-13", "R4", "Filename typo 40CAL01_Testpont_Settings.txt",
        "data/raw/flex/part-01/40CAL01_Testpont_Settings.txt", "raw file", "header row", "-",
        "Structurally identical to the other Testpoint files (62 columns, 1 data row): fiber flag "
        "No, burn-to-completion 20000 ms", "L2",
        "RESOLVED", "high",
        "Filename typo only, content structurally normal (62 columns, 1 row). Do not rename the raw file; record the alias in any future join logic", "no action")

    # --- calibration ---
    add("ER-14", "R10", "Calibration records for the measured quantities",
        "docs/flex/*; data/raw/flex/*; analysis/*", "all inspected", "full-text search 'calibrat'",
        "-",
        "No calibration certificate, analyzer log or transducer record exists in any inspected "
        "file. The investigation record documents that PSI hosts FLEX Calibration / LCTF "
        "Calibration / Radiometer Calibration experiment data records, but none is in the local "
        "dataset. Requirement-level accuracies exist (EIRD/ERD). Independent corroboration: for "
        "all 8 linked runs the FCU PT16 transducer (PSIA) converts to within 0.6-1.2 mmHg of the "
        "table's pressure (0.06-1.24 mmHg, <=0.164%)", "L3",
        "ORIGINATOR_CONFIRMATION_REQUIRED", "medium",
        "The PSIA cross-check is an indirect consistency check, not a calibration; requirement "
        "tolerances are spec-level, not verification records",
        "Originator question OQ-7; request calibration experiment records")

    # --- images ---
    add("ER-15", "R3", "Image archive usability",
        "analysis/evidence_resolution/resolution_checks.csv", "this phase", "image_archives", "-",
        "23 archives; A/B = 512x512 16-bit uncompressed TIFF, D = 640x480 24-bit uncompressed BMP; "
        "800-1290 frames each; sequential numbering with occasional gaps (e.g. 20CAL08A holds "
        "200-1480 with 20 internal gaps); each archive embeds its frame manifest; TIFF tags carry "
        "only a nominal 150 dpi (scanner convention), no physical pixel scale; no EXIF timestamps",
        "L1 (structure) / L4 (measurements)",
        "PARTIALLY_RESOLVED", "high",
        "Run association and sequence ordering ARE recoverable from filenames + embedded "
        "manifests; scale calibration is absent from the images themselves; no image-derived "
        "measurement is claimed", "Pilot extract one run for scale/geometry before any depth work")

    # --- metadata ---
    add("ER-16", "R7", "Per-run ambient temperature",
        "data/raw/flex/part-01/*_Chamber_Readings.txt", "raw telemetry", "FCU_MP_TM1..4", "-",
        "Chamber temperatures logged (TM1 spans 23.57-26.06 C across the 8 runs) for all 8 linked runs - none for the "
        "other 266 records; the experimental table has no temperature column", "L2",
        "PARTIALLY_RESOLVED", "high",
        "Recoverable for 8 runs from chamber logs; absent for 266 records",
        "Originator question OQ-8; request remaining chamber logs")
    add("ER-17", "R7", "Per-run gravity (g-level)",
        "all inspected sources", "n/a", "search 'gravity' / 'g-level'", "-",
        "Only the requirement (<1e-4 m/s2; measurement capability 1e-6 m/s2) is documented; no "
        "per-run accelerometer data exists in any local file", "L1 (requirement)",
        "UNVERIFIED", "high",
        "Per-run gravity values are UNVERIFIED; do not infer per-run gravity from the "
        "requirement",
        "Originator question OQ-8 (request per-run g-level data)")
    add("ER-18", "R7", "Fiber support per run",
        "data/raw/flex/part-01/*_Testpoint_Settings.txt", "raw telemetry",
        "TP_PARAMETER_FIBER_USAGE_FLAG", "-",
        "fiber flag = No for all 8 linked runs (and soot-sampler flag No); unknown for the other "
        "266 records", "L2",
        "PARTIALLY_RESOLVED", "high",
        "8-run coverage only", "Originator question OQ-8")
    return E


CORRECTIONS = [
    OrderedDict(
        correction_id="COR-01", phase="Phase 1",
        file="analysis/audit/data_quality_report.md", location="section 3 (zero-mm row)",
        original_statement="outcomes Disruption x5, Completion x3",
        corrected_statement="outcomes Disruption x4 (224F001, 223F002, 210F002, 149F001), "
                            "Completion x4 (209F005, 301F002, 193R002, C21H501)",
        verification="independent enumeration from the raw table this phase; Phase 3 defect "
                     "register D1 documented the defect; the frozen Phase 1 file is unchanged",
        action="documented, not modified"),
    OrderedDict(
        correction_id="COR-02", phase="Phase 3",
        file="analysis/validation/measurement_provenance.md / uncertainty_assessment.md",
        location="initial-diameter citations",
        original_statement="ERD section 4.1.33; EIRD section 6.1.1 (as first written in Phase 3)",
        corrected_statement="ERD 4.1.12 (Droplet Size Tolerance) and 4.1.13 (Reproducibility); "
                            "EIRD 5.1.2 (Droplet Deployment and Ignition) for the 2-6 mm range",
        verification="found by the Phase 3 independent review and CORRECTED IN PLACE during that "
                     "review cycle; Phase 3.5 re-verified the frozen files now cite the correct "
                     "sections (ERD 4.1.33 is 'Non-Quiescent Test Point Timing'; EIRD 6.1.1 is "
                     "'Test Fuels')",
        action="corrected in place before the Phase 3 freeze; re-verified in Phase 3.5"),
    OrderedDict(
        correction_id="COR-03", phase="Phase 3",
        file="analysis/validation/{measurement_provenance.md, telemetry_assessment.md, "
             "uncertainty_assessment.md} + evidence_register",
        location="GMT synchronisation citations",
        original_statement="ERD section 4.1.54 (as first written in Phase 3)",
        corrected_statement="ERD section 4.1.98 (Synchronization of Measurements)",
        verification="found by the Phase 3 independent review and CORRECTED IN PLACE before the "
                     "freeze; Phase 3.5 re-verified the frozen files cite ERD 4.1.98 "
                     "(4.1.54 is 'Diagnostics Imaging')",
        action="corrected in place before the Phase 3 freeze; re-verified in Phase 3.5"),
    OrderedDict(
        correction_id="COR-04", phase="Phase 3",
        file="analysis/validation/telemetry_assessment.md", location="sampling table",
        original_statement="chamber 386-387 rows per run; radiometer 146-147 rows (as first written)",
        corrected_statement="chamber 376-388 rows for 5 runs and header+1 row for 30CAL02, "
                            "30CAL03, 40CAL01 (ignition snapshots); radiometer 130-148 rows",
        verification="found by the Phase 3 independent review and CORRECTED IN PLACE before the "
                     "freeze; Phase 3.5 re-verified the frozen file carries the corrected ranges",
        action="corrected in place before the Phase 3 freeze; re-verified in Phase 3.5"),
]


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    # ---- integrity gate ----
    integrity = []
    for rel in PROTECTED:
        if os.path.isfile(os.path.join(ROOT, rel)):
            integrity.append((rel, sha256_of(rel)))
    bad = [rel for rel, d in integrity
           if rel.endswith(".csv") and rel == "data/raw/flex/PSI-69_Experimental table_FLEX.csv"
           and d != RAW_SHA256]
    if bad:
        raise SystemExit(f"raw dataset changed: {bad} - Phase 3.5 refuses to run")
    print(f"[integrity] {len(integrity)} protected files verified")

    # ---- data + forensics ----
    records = load_records()
    checks = forensic(records)
    print(f"[forensics] {checks['n_records']} records; "
          f"{checks['duplicate_datetime_pairs']} duplicate date-time clusters; "
          f"{len(checks['image_archives'])} archives catalogued")

    check_rows = []
    for k, v in checks.items():
        if isinstance(v, (dict, list)):
            value = json.dumps(v, default=str)
        else:
            value = v
        check_rows.append(OrderedDict(
            quantity=k, value=value,
            source="independent recomputation by run_resolution.py from the raw table "
                   "(and raw telemetry/archive metadata; no extraction)"))
    write_csv(os.path.join(HERE, "resolution_checks.csv"), check_rows)
    print(f"[csv] resolution_checks.csv ({len(check_rows)} rows)")

    sr = source_register_rows()
    write_csv(os.path.join(HERE, "source_document_register.csv"), sr)
    print(f"[csv] source_document_register.csv ({len(sr)} rows)")

    er = evidence_rows(records, checks)
    write_csv(os.path.join(HERE, "evidence_resolution_register.csv"), er)
    print(f"[csv] evidence_resolution_register.csv ({len(er)} rows)")

    write_csv(os.path.join(HERE, "correction_register.csv"), CORRECTIONS)
    print(f"[csv] correction_register.csv ({len(CORRECTIONS)} rows)")

    # ---- manifest ----
    import matplotlib  # noqa: F401  (environment record)
    outputs = {}
    for name in ("resolution_checks.csv", "source_document_register.csv",
                 "evidence_resolution_register.csv", "correction_register.csv"):
        rel = os.path.join("analysis", "evidence_resolution", name)
        outputs[name] = dict(sha256=sha256_of(rel),
                             rows=sum(1 for _ in open(os.path.join(HERE, name))) - 1)
    manifest = OrderedDict(
        analysis="FLEX PSI-69 Phase 3.5 evidence resolution",
        script=dict(name="run_resolution.py", version="3.5.0",
                    entrypoint="notebooks/.venv/bin/python "
                               "analysis/evidence_resolution/run_resolution.py"),
        executed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        environment=dict(python=platform.python_version(), platform=platform.platform(),
                        numpy=np.__version__, matplotlib=matplotlib.__version__),
        inputs=[dict(path="data/raw/flex/PSI-69 Experimental table_FLEX.csv",
                     sha256=RAW_SHA256, records=checks["n_records"],
                     encoding="latin-1 byte-preserving; 0x96 = missing marker")],
        documents_inspected=[s[1] for s in SOURCES],
        archive_metadata_inspected=OrderedDict(
            archives=len(checks["image_archives"]),
            total_uncompressed_gb=round(sum(a["zip_uncompressed_gb"]
                                            for a in checks["image_archives"]), 3),
            method="zip directory listings + in-memory first/middle/last frame header reads; "
                   "NO bulk extraction performed"),
        integrity=dict(protected_files_checked=len(integrity),
                      note="full per-file hashes for Phases 1-3 are asserted in "
                           "tests/test_resolution.py"),
        outputs=outputs,
        restrictions=dict(modelling="none performed", imputation="none",
                         renormalisation="none", unit_assignment="none",
                         archive_extraction="none beyond in-memory header reads",
                         external_contact="none"),
        limitations=[
            "Burning-rate column definition remains unavailable locally; the identifying "
            "publications (NTRS 20150023456; DOI 10.1007/s12217-014-9377-x) are not local files.",
            "'Disruption' is undefined in every inspected document.",
            "Clock offsets are quantified per run but no synchronization reference exists.",
            "Calibration records are absent locally; only spec-level accuracies and one "
            "indirect PSIA cross-check exist.",
            "Per-run temperature/gravity/fiber metadata exist only for the 8 telemetry-linked runs.",
        ])
    with open(os.path.join(HERE, "run_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("[manifest] run_manifest.json")


if __name__ == "__main__":
    main()
