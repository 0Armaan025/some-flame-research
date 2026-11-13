# Frontend Integration Guide — FLEX-PSI69 Evidence Intelligence Platform

How to connect your frontend to the FLEX-PSI69 backend intelligence. You own
everything above the API (pages, layout, styling, navigation); this documents
the contract below it.

**The platform is the evidence engine.** The prediction classifier is an
optional, separate component that you may expose as a second feature.

## 1. Install and run

```bash
# from the repository root — one-time install into the project venv
notebooks/.venv/bin/pip install -r intelligence/requirements.txt

# start the evidence intelligence API
notebooks/.venv/bin/python -m uvicorn intelligence.api:app --port 8001
# interactive docs at http://localhost:8001/docs
```

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | dataset + question-count health |
| GET | `/questions` | the seven supported questions with variables and caveats |
| GET | `/experiments` | browse the 274 experiments; filters: `fuel`, `outcome`, `series`, `has_flag`, `text`, `limit` |
| POST | `/query` | ask a question: `{"question_id": "Q1"[, "parameters": {...}]}` |
| POST | `/predict` | optional recorded-outcome classifier `{"fuel": …, "d0_mm": …, "pressure_mmHg": …, "o2_mf": …, "n2_mf": …, "co2_mf": …, "he_mf": …}` |
| GET | `/evidence/{test_no}` | full record with preserved raw values and flags |

## 3. The `/query` response (every answer has the same shape)

```json
{
  "question_id": "Q2",
  "question": "How do their recorded burn-duration distributions differ?",
  "direct_answer": "Recorded burn durations differ substantially: median 12.10 s (methanol, n=155) vs 7.50 s (heptane, n=111); Mann-Whitney U=4838, p=1.17e-09, rank-biserial r=0.438. The median difference is -4.60 s (heptane minus methanol). ...",
  "numerical_findings": {
    "methanol": {"n": 155, "median": 12.1, "iqr": [7.85, 17.9]},
    "heptane": {"n": 111, "median": 7.5, "iqr": [3.3, 11.25]},
    "median_difference_heptane_minus_methanol": -4.6,
    "mwu_U": 4838.0, "mwu_p": 1.17e-09, "rank_biserial": 0.4376,
    "approximate_values_excluded": ["~6", "~9"]
  },
  "evidence_ranking": [
    {"label": "burn-time distributions by fuel (266 exact records)",
     "dimensions": {
       "relevance": {"score": 1.0, "reason": "direct answer"},
       "data_quality": {"score": 0.85, "reason": "6 missing and 2 approximate handled explicitly"},
       "comparability": {"score": 0.3, "reason": "unassessed"},
       "statistical_strength": {"score": 0.68, "reason": "n=266; effect size 0.438; p=1.17e-09 (Mann-Whitney)"}
     },
     "band": "moderate", "banding_rule": "band = high iff ..."}
  ],
  "method": "exact recorded burn times only ...",
  "important_exclusions": [],
  "contradictory_or_conflicting_evidence": [],
  "limitations": ["burn duration is a recorded scalar with undocumented start/stop events", "..."],
  "what_would_resolve_uncertainty": ["originator definition of burn-time start/stop events"],
  "traceability": ["data/raw/flex/PSI-69 Experimental table_FLEX.csv", "analysis/phase4a/duration_comparison.csv"]
}
```

Full schema: `intelligence/response_schema.json`.

## 4. UI requirements (non-negotiable)

1. **Always render `limitations`** next to every answer — they are the point of
   the platform, not fine print.
2. **Never relabel `band` scores as confidence**; show the four dimensions with
   their `reason` strings when a user expands an evidence item.
3. **Never describe model contributions or associations as causes.**
4. **Q5 (pressure) and Q3 (oxygen) are confounding disclosures, not effects** —
   display them as such.
5. **`/predict` is a recorded-label classifier**, not physical fire risk; show
   its evaluation summary (balanced accuracy 0.530 vs 0.333 baseline) beside
   any prediction and never omit its warnings.
6. Answers are deterministic: the same question returns the same JSON. You may
   cache aggressively.

## 5. Reading the frozen comparison data

Static files for your comparison pages (copy into `public/`; never modify):

| What | Where |
|---|---|
| Headline comparisons | `analysis/phase4a/results_summary.csv` |
| Outcomes / duration / diameter / extinction / conditions | `analysis/phase4a/*_comparison.csv`, `extinction_diameter_assessment.csv` |
| Sensitivity + limitations | `analysis/phase4a/sensitivity_analysis.csv`, `limitations_register.csv` |
| Figures | `analysis/phase4a/figures/*.png` |
| Paper tables | `analysis/phase5/tables.md` |
| The paper PDF | `deliverables/FLEX_PSI69_Research_Paper.pdf` |

## 6. Recommended frontend structure

```
frontend/
├── src/
│   ├── api/              # typed clients for /query, /experiments, /predict
│   ├── components/
│   │   ├── QuestionPicker.tsx     # the seven catalog questions with caveats
│   │   ├── AnswerPanel.tsx        # direct_answer + numerical_findings + method
│   │   ├── EvidenceCard.tsx       # four dimensions with reasons + band
│   │   ├── LimitationsPanel.tsx   # always visible
│   │   ├── ExperimentBrowser.tsx  # /experiments with filters + flags
│   │   └── PredictPanel.tsx       # optional /predict with warnings
│   └── pages/            # Home / Ask / Compare / Explore / Limitations / About
└── README.md
```

## 7. Example flow

1. `GET /questions` → render the seven questions.
2. User picks Q4 → `POST /query {"question_id":"Q4","parameters":{"o2_mf":0.17}}`.
3. Render the direct answer, the 10-cell classification table, and the
   `supporting_experiments` list (each with its `flags` and `provenance`).
4. Show the evidence-ranking cards and the limitations list.
5. Link to the frozen CSVs/figures for the underlying comparison data.
</content>