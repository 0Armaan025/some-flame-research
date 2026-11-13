# combustion-research

Combustion research data organization for microgravity droplet flame experiments (FLEX, JAXA group combustion, TNF).

## Directory layout

```
combustion-research/
├── data/
│   ├── raw/            # Source data as received
│   │   ├── flex/
│   │   ├── jaxa_group_combustion/
│   │   └── tnf/
│   ├── interim/        # Intermediate cleaned/normalized artifacts
│   │   ├── flex/
│   │   ├── jaxa/
│   │   └── tnf/
│   └── processed/      # Final analysis-ready datasets
│       ├── unified_observations.csv
│       ├── experiment_metadata.csv
│       └── measurement_manifest.csv
├── docs/               # Project documentation (PDFs, plans, requirements)
│   ├── flex/
│   ├── jaxa/
│   └── tnf/
├── src/                # Source code
│   ├── ingestion/
│   ├── parsers/
│   ├── normalization/
│   ├── extinction/
│   ├── analysis/
│   ├── uncertainty/
│   └── prediction/
├── notebooks/          # Exploratory analysis notebooks
├── reports/            # Generated reports and figures
├── tests/              # Test suite
└── README.md
```

## Data provenance

- `data/raw/flex/` — FLEX (Flame Extinguishment Experiment) test data, including the `part-01/` dataset and chamber gas notes.
- `docs/flex/` — FLEX investigation documents (test plan, requirements, EIRD, DoD).
- `docs/jaxa/` — JAXA group combustion experiment documents.
- `src/prediction/predictor.py` — Flame test outcome predictor trained on the FLEX experimental table.

## Usage

Run the predictor from the repository root:

```bash
python src/prediction/predictor.py
```
# some-flame-research
