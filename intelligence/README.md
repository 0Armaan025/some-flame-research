# Evidence Intelligence Engine — FLEX-PSI69

A deterministic question-to-evidence engine over the frozen FLEX-PSI69
research project. It answers scientific questions about the recorded
droplet-combustion experiments with traceable numbers, transparent evidence
ranking, and explicit limitations — no LLM, no invented values, no physical
interpretation of the unresolved burning-rate column.

## What it does

```
question (catalog) → relevant variables → retrieval (raw records + frozen
analysis artifacts) → comparability rules → supported summaries
→ transparent evidence ranking → explanation assembly
```

Every answer contains: direct answer, supporting experiments, numerical
findings (with denominators), the method used, important exclusions,
contradictory evidence, limitations, what data would resolve the remaining
uncertainty, and traceability (files / raw rows).

## Supported questions

| ID | Question | Answer type |
|---|---|---|
| Q1 | How do methanol and heptane experimental outcomes differ? | recorded-label contingency, Fisher + Freeman–Halton, Cramér's V |
| Q2 | How do their recorded burn-duration distributions differ? | medians/IQRs, Mann–Whitney, rank-biserial |
| Q3 | Evidence on oxygen concentration vs experimental outcomes? | per-level compositions + restricted air-family contrast |
| Q4 | Which experiments are comparable under specified O₂/diluent conditions? | comparability classification (4 full / 3 partial / 3 rejected cells) |
| Q5 | Evidence for pressure-related differences? | confounding disclosure (no effect claim) |
| Q6 | Which findings are sensitive to data-quality issues? | quantified sensitivity under documented record-handling rules |
| Q7 | What information is missing that prevents a stronger conclusion? | missingness + evidence-gap inventory mapped to originator questions |

## Evidence ranking (interpretable, not a black-box score)

Four **independent** dimensions per evidence item, each with a score (0–1)
*and* a human-readable reason:

| Dimension | Measures |
|---|---|
| relevance | fraction of the query's conditions matched |
| data_quality | completeness of required fields, minus integrity-flag penalties |
| comparability | whether a defensible comparison exists (cell class / family / confound) |
| statistical_strength | sample size dominated, modified by effect size |

Bands (`high` / `moderate` / `low` / `excluded_from_primary_evidence`) come
from an **explicit, printed rule** — no opaque composite is reported. A highly
relevant but poorly documented experiment cannot reach "high"; zero
comparability excludes an item from primary evidence.

## Run it

```bash
# API
notebooks/.venv/bin/python -m uvicorn intelligence.api:app --port 8001

# direct Python
notebooks/.venv/bin/python -c "
import sys; sys.path.insert(0, 'intelligence')
import evidence_engine as e
print(e.answer_question('Q1')['direct_answer'])"

# tests
notebooks/.venv/bin/python -m pytest intelligence/tests/ -v
```

## Files

| File | Contents |
|---|---|
| `retrieval.py` | byte-preserving loader + deterministic statistics |
| `comparability.py` | comparability rules (reproduces the frozen Phase 4A verdicts) |
| `ranking.py` | the four-dimension ranking and banding rule |
| `evidence_engine.py` | the seven question engines + experiment accessors |
| `explanations.py` | (documented in `evidence_engine.py`'s answer shell) — every answer's structure |
| `api.py` | FastAPI service |
| `question_catalog.json` | the seven questions with variables and caveats |
| `response_schema.json` | the JSON contract for `POST /query` |
| `model/delegation_manifest.json` | pointer to the separately validated prediction model |
| `tests/test_intelligence.py` | 20 tests incl. frozen-artifact cross-checks and integrity |

## Scientific constraints (enforced and tested)

no fabricated evidence · no unsupported physical interpretation · no unit
assignment to the burning-rate column · no imputation · no causal claims from
observational comparisons · no synchronized-time claims · no fake confidence
values · no invented calibration · frozen phases never modified · everything
local.

## Prediction module (optional, separate)

`POST /predict` delegates to the validated recorded-outcome classifier in
`prediction/` (series-grouped CV; balanced accuracy 0.530 vs 0.333 baseline;
exact linear explanations). It predicts **recorded labels**, not physical
fire risk, and the evidence engine works without it.