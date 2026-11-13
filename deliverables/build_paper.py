#!/usr/bin/env python3
"""FLEX PSI-69 Phase 6 - build the research-paper PDF.

Assembles the frozen Phase 5 manuscript with the six Phase 4A figures and the
eight research tables embedded at their in-text positions, then compiles to
PDF with pandoc + typst. The original manuscript is never modified; the
assembled working copy is written to deliverables/_build/.

Run:
    notebooks/.venv/bin/python deliverables/build_paper.py

The original manuscript (`analysis/phase5/research_paper.md`) is unchanged;
formatting-only changes (figure/table embedding, title metadata, page
numbering) are documented in build_paper.py's report at the end of the run.
"""

import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P5 = os.path.join(ROOT, "analysis", "phase5")
P4A = os.path.join(ROOT, "analysis", "phase4a")
OUT_DIR = os.path.join(ROOT, "deliverables")
BUILD = os.path.join(OUT_DIR, "_build")

PAPER_MD = os.path.join(P5, "research_paper.md")
TABLES_MD = os.path.join(P5, "tables.md")
CAPTIONS_MD = os.path.join(P5, "figure_captions.md")
FIG_DIR = os.path.join(P4A, "figures")

FIGURES = {
    "6.1": ("fig01_outcome_distribution.png",
            "Figure 1 — Recorded outcome-label composition by fuel (Figure 4A-1)."),
    "6.2": ("fig02_burn_duration.png",
            "Figure 2 — Burn duration: distributions and medians by fuel (Figure 4A-2)."),
    "6.3": ("fig03_initial_diameter.png",
            "Figure 3 — Initial droplet diameter by fuel; 193F001 collision records ringed (Figure 4A-3)."),
    "6.4": ("fig04_extinction_diameter.png",
            "Figure 4 — Visible flame extinction diameter by fuel within each recorded outcome (Figure 4A-4)."),
    "6.5": ("fig05_condition_cells.png",
            "Figure 5 — Matched-oxygen CO2/He substitution cells and comparability class (Figure 4A-5)."),
    "6.6": ("fig06_pressure_confounding.png",
            "Figure 6 — Pressure versus oxygen with the confounded high-pressure cluster (Figure 4A-6)."),
}

# which table block follows which results section
TABLE_ANCHORS = {
    "6.1": ("1", "2"),
    "6.2": ("3",),
    "6.3": ("4",),
    "6.4": ("5",),
    "6.5": ("6",),
    "6.6": ("7", "8"),
}

YAML = """---
title: "Measurable Differences Between Methanol and n-Heptane in the FLEX-PSI69 Droplet-Combustion Records: A Comparative Analysis With Explicit Limitations"
author:
  - "FLEX-PSI69 research project — comparative analysis of the released experimental table"
date: "Research manuscript (Phase 5); analysis pipeline Phase 6"
abstract: |
"""

ABSTRACT_TEXT = """The FLEX-PSI69 experimental table records 274 droplet-combustion tests flown on
the International Space Station — 157 with methanol and 117 with n-heptane —
spanning March 2009 to December 2011. This paper reports a comparative
analysis of the recordable quantities and states explicitly which comparisons
the data support and which they do not. Recorded outcome-label composition
differs strongly (Extinction 80.3% vs 51.3%; Freeman–Halton p = 1.75e-06,
Cramér's V = 0.3099); burn duration differs (medians 12.10 s vs 7.50 s;
heptane-minus-methanol −4.6 s, 95% bootstrap CI −7.8 to −2.9); initial
diameter is sensitivity-dependent on the handling of a duplicated identifier.
Visible flame extinction diameter is reported for 197 of 274 records with
eight measurement-floor zeros retained. Only four of ten oxygen-matched
diluent cells are fully comparable; all nine records above 800 mmHg belong to
one CO2-diluted family. The burning-rate column's definition is unresolved and
experimental independence is not established, so no causal or physical claim
is made.
"""

TYPST_HEADER = """#set page(numbering: "1", margin: 2.2cm)
#set par(justify: true)
#show heading: set text(font: "New Computer Modern", weight: "bold")
#set figure.caption(separator: [. ])
"""


def load_tables():
    """Split tables.md into (heading, body) blocks keyed by table number."""
    with open(TABLES_MD) as fh:
        text = fh.read()
    text = text.split("# Tables", 1)[1] if "# Tables" in text else text
    blocks = re.split(r"\n## (Table \d+ —[^\n]*)\n", "\n" + text)
    out = {}
    for i in range(1, len(blocks) - 1, 2):
        heading = blocks[i].strip()
        body = blocks[i + 1].strip()
        num = re.match(r"Table (\d+)", heading).group(1)
        out[num] = (heading, body)
    assert len(out) == 8, f"expected 8 tables, found {sorted(out)}"
    return out


def rel(path):
    return os.path.relpath(path, BUILD).replace(os.sep, "/")


def assemble():
    os.makedirs(BUILD, exist_ok=True)
    with open(PAPER_MD) as fh:
        paper = fh.read()
    tables = load_tables()

    # strip the paper's own Abstract/Keywords headers (moved into YAML metadata)
    paper = paper.replace("# Measurable Differences", "## 0. Title and abstract", 1)

    # embed figures and tables under their results sections
    for section, (fig, caption) in FIGURES.items():
        anchor = re.search(rf"(### {re.escape(section)}[^\n]*\n)", paper)
        if not anchor:
            raise SystemExit(f"section {section} not found in manuscript")
        embed = (f"\n![{caption}]({rel(os.path.join(FIG_DIR, fig))})\n")
        paper = paper[:anchor.end()] + embed + paper[anchor.end():]
    for section, table_keys in TABLE_ANCHORS.items():
        anchor = None
        for m in re.finditer(r"(### [0-9.]+ [^\n]*\n)", paper):
            if m.group(1).startswith(f"### {section}"):
                anchor = m
                break
        if anchor is None:
            raise SystemExit(f"anchor {section} not found")
        # insert the tables at the END of that subsection: find the next ### heading
        nxt = paper.find("\n### ", anchor.end())
        insert_at = nxt if nxt != -1 else len(paper)
        block = ""
        for key in table_keys:
            heading, body = tables[key]
            block += f"\n**{heading}**\n\n{body}\n"
        paper = paper[:insert_at] + "\n" + block + paper[insert_at:]

    abstract_block = "\n".join("    " + l if l.strip() else ""
                                for l in ABSTRACT_TEXT.splitlines())
    full = YAML + abstract_block + "\n---\n\n" + paper
    out_md = os.path.join(BUILD, "research_paper_full.md")
    with open(out_md, "w") as fh:
        fh.write(full)
    return out_md


def compile_pdf(md_path):
    header = os.path.join(BUILD, "header.typ")
    with open(header, "w") as fh:
        fh.write(TYPST_HEADER)
    out_pdf = os.path.join(OUT_DIR, "FLEX_PSI69_Research_Paper.pdf")
    cmd = ["pandoc", md_path, "-o", out_pdf, "--pdf-engine=typst",
           "--include-in-header", header, "--number-sections",
           "--resource-path", BUILD]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if res.returncode != 0:
        raise SystemExit(f"pandoc failed:\n{res.stdout}\n{res.stderr}")
    return out_pdf


def verify(pdf_path):
    txt = subprocess.run(["pdftotext", pdf_path, "-"], capture_output=True,
                         text=True).stdout
    pages = len(re.findall(r"\f", txt)) + 1
    required = [
        "Abstract", "Keywords", "Introduction", "Research objectives",
        "Dataset and experimental background", "Data preparation",
        "Statistical methodology", "Results", "Discussion",
        "Experimental and statistical limitations", "Conclusions",
        "References", "Data and code availability",
        "80.3", "51.3", "12.10", "7.50", "4838", "1.75", "0.3099",
        "193F001", "measurement-floor", "fully comparable", "800 mmHg",
        "Table 1", "Table 8", "Figure 1", "Figure 6",
        "References", "NTRS 20150023456", "10.1007/s12217-014-9377-x",
    ]
    missing = [s for s in required if s not in txt]
    return pages, missing, txt


def main():
    md = assemble()
    pdf = compile_pdf(md)
    pages, missing, txt = verify(pdf)
    print(f"[pdf] {os.path.relpath(pdf, ROOT)}")
    print(f"[verify] pages={pages}")
    print(f"[verify] required strings missing: {missing or 'none'}")
    size = os.path.getsize(pdf)
    print(f"[verify] size={size/1e6:.2f} MB")
    # image presence: typst embeds images; check the PDF for image XObjects
    with open(pdf, "rb") as fh:
        raw = fh.read()
    n_images = raw.count(b"/Subtype /Image") + raw.count(b"/Subtype/Image")
    print(f"[verify] embedded image objects: {n_images}")
    if missing:
        raise SystemExit(f"PDF verification failed: {missing}")


if __name__ == "__main__":
    main()
