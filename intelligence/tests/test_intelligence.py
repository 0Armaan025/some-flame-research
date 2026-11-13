"""FLEX-PSI69 evidence-intelligence test suite.

    notebooks/.venv/bin/python -m pytest intelligence/tests/ -v

Verifies: deterministic answers; the engine's numbers match the frozen Phase 4A
artifacts (counts, p-values, cell classifications, missingness); comparability
rules reproduce the frozen verdicts; ranking dimensions and the banding rule;
the API contract; prediction delegation; and protected-file integrity.
"""

import csv
import hashlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
INT = os.path.dirname(HERE)
ROOT = os.path.dirname(INT)
sys.path.insert(0, INT)

import comparability as C          # noqa: E402
import evidence_engine as E         # noqa: E402
import retrieval as R               # noqa: E402

RAW_CSV = os.path.relpath(R.raw_csv_path(), ROOT)
RAW_SHA256 = "37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96"


def sha256_of(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture(scope="module")
def answers():
    return {qid: E.answer_question(qid)
            for qid in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7")}


# --- determinism and schema ----------------------------------------------------
def test_answers_deterministic(answers):
    for qid in answers:
        again = E.answer_question(qid)
        assert json.dumps(again, sort_keys=True) == json.dumps(answers[qid],
                                                              sort_keys=True), qid


def test_answer_structure(answers):
    for qid, a in answers.items():
        for key in ("question_id", "question", "direct_answer",
                    "numerical_findings", "method", "limitations",
                    "what_would_resolve_uncertainty", "traceability",
                    "evidence_ranking", "important_exclusions",
                    "contradictory_or_conflicting_evidence"):
            assert key in a, (qid, key)
        assert a["limitations"], qid
        assert a["method"], qid


def test_answer_contract_validation(answers):
    import explanations
    for qid, a in answers.items():
        assert explanations.validate(a) == [], qid
        compact = explanations.summarise_for_display(a)
        assert compact["direct_answer"] and compact["limitations"]


def test_response_schema_is_valid_json():
    with open(os.path.join(INT, "response_schema.json")) as fh:
        schema = json.load(fh)
    assert "query" in schema["title"].lower() or schema["title"]
    for req in ("question_id", "direct_answer", "numerical_findings",
                "method", "limitations"):
        assert req in schema["required"]


def test_catalog_covers_seven_questions():
    catalog = E.load_catalog()
    assert len(catalog["questions"]) == 7
    assert [q["id"] for q in catalog["questions"]] == [f"Q{i}" for i in range(1, 8)]


# --- numbers match the frozen artifacts -------------------------------------------------
def test_q1_matches_frozen_csv(answers):
    rows = R.read_frozen("outcome_comparison")
    counts = {(r["group"], r["outcome"]): (r["count"], r["n_fuel"])
              for r in rows if r["analysis"] == "A_outcome"}
    a = answers["Q1"]["numerical_findings"]
    for fuel, key in (("Methanol", "Methanol"), ("Heptane", "Heptane")):
        for o in R.OUTCOMES:
            assert str(a["contingency"][fuel][o]) == counts[(f"fuel={fuel}", o)][0]
    tbl = [r for r in rows if r["analysis"] == "A_outcome_table"][0]
    assert "1.75e-06" in tbl["proportion"]
    assert f"{a['freeman_halton_p']:.3g}" == "1.75e-06"
    assert f"{a['cramers_v']:.4f}" == "0.3099"


def test_q2_matches_frozen_csv(answers):
    rows = R.read_frozen("duration_comparison")
    med = {r["group"]: r["median"] for r in rows
           if r["metric"] == "burn_time_s_descriptive"}
    contrast = [r for r in rows if r["metric"] == "burn_time_s_contrast"][0]
    a = answers["Q2"]["numerical_findings"]
    assert f"{a['methanol']['median']:.4f}" == med["fuel=Methanol"]
    assert f"{a['heptane']['median']:.4f}" == med["fuel=Heptane"]
    assert contrast["test_statistic"] == "MWU U=4838.0"
    assert float(a["mwu_U"]) == 4838.0
    # the direction is stated explicitly
    ans = answers["Q2"]["direct_answer"].lower()
    assert "heptane minus methanol" in ans


def test_q4_cell_classification_matches_frozen_csv(answers):
    frozen = {}
    for r in R.read_frozen("condition_comparison"):
        if r["metric"] == "cell_summary":
            o2 = r["group"].split("=")[1]
            frozen[o2] = r["note"].split("class=")[1].split(";")[0]
    ours = {str(c["o2_mf"]): c["comparability"]
            for c in C.dilution_cells(E.records())}
    assert ours == frozen, (ours, frozen)
    assert [k for k, v in ours.items() if v == "full"] == ["0.16", "0.17",
                                                           "0.18", "0.24"]


def test_q5_disclosures_match_frozen(answers):
    rows = R.read_frozen("condition_comparison")
    disc = [r for r in rows if r["metric"] == "pressure_confounding_disclosure"][0]
    a = answers["Q5"]["numerical_findings"]
    assert a["n_above_800_mmHg"] == int(disc["n_total"]) == 9


def test_q6_sensitivity_matches_frozen(answers):
    rows = R.read_frozen("sensitivity_analysis")
    vals = {r["variant"]: r["p_value"] for r in rows
            if r["analysis"] == "S_diameter"}
    a = answers["Q6"]["numerical_findings"]["initial_diameter_p_by_variant"]
    assert a["as_reported"] == vals["as_reported"]
    assert a["excluding_193F001_record_1"] == vals["excluding_193F001_record_1"]
    assert a["screened_flagged_anomalies_excluded"] == \
        vals["screened_flagged_anomalies_excluded"]


def test_q7_missingness_matches_audit(answers):
    audit = list(csv.DictReader(open(os.path.join(
        ROOT, "analysis", "audit", "missing_data_report.csv"))))
    miss = {r["variable"]: int(r["n_missing"])
            for r in audit if r["fuel"] == "All"}
    a = answers["Q7"]["numerical_findings"]
    assert a["missing_counts"]["visible flame extinction diameter"] == \
        miss["Visible flame extinction diameter; mm"] == 77
    assert a["missing_counts"]["initial droplet diameter"] == \
        miss["Droplet initial diameter; mm"] == 12
    assert a["missing_counts"]["burn time"] == miss["Burn time; s"] == 6


# --- ranking -----------------------------------------------------------------------
def test_ranking_dimensions_present(answers):
    for a in answers.values():
        for item in a["evidence_ranking"]:
            dims = item["dimensions"]
            for d in ("relevance", "data_quality", "comparability",
                      "statistical_strength"):
                assert 0.0 <= dims[d]["score"] <= 1.0, (a["question_id"], d)
                assert dims[d]["reason"], d
            assert item["band"] in ("high", "moderate", "low",
                                    "excluded_from_primary_evidence")
            assert item["banding_rule"]


def test_relevant_but_poor_quality_cannot_be_high():
    import ranking
    dims = {
        "relevance": (1.0, "direct match"),
        "data_quality": (0.1, "mostly missing"),
        "comparability": (0.3, "unassessed"),
        "statistical_strength": (0.1, "n=4"),
    }
    items = ranking.rank_evidence([dict(label="x", **dims)])
    assert items[0]["band"] in ("low", "excluded_from_primary_evidence")


def test_comparability_zero_excludes():
    import ranking
    items = ranking.rank_evidence([dict(
        label="x", relevance=(1.0, ""), data_quality=(0.9, ""),
        comparability=(0.0, "rejected"), statistical_strength=(0.5, ""))])
    assert items[0]["band"] == "excluded_from_primary_evidence"


# --- engine behaviours ------------------------------------------------------------------
def test_experiment_filters_and_detail(answers):
    res = E.list_experiments({"fuel": "Heptane"}, limit=5)
    assert res["total"] == 117 and res["returned"] == 5
    flagged = E.list_experiments({"flags": "identifier_collision_193F001"}, limit=5)
    assert flagged["total"] == 2
    det = E.experiment_detail(70)
    assert det["flex_identifier"] == "193F001"
    assert det["raw_values_preserved"]["burn_time_reported"] == "1.6"


def test_pressure_zero_record_treated_as_missing(answers):
    recs = E.records()
    zero = [r for r in recs if r["pressure_mmHg"] is None]
    assert len(zero) == 1 and zero[0]["flex_identifier"] == "C11M201"
    for view in E.list_experiments({"text": "C11M201"}, limit=1)["experiments"]:
        assert view["pressure_mmHg"] is None


def test_q4_parameter_restriction():
    a = E.answer_question("Q4", {"o2_mf": 0.17})
    full = [c["o2_mf"] for c in a["numerical_findings"]["cells_full"]]
    assert full == [0.17]


def test_burning_rate_never_interpreted(answers):
    blob = json.dumps(answers)
    assert "mm2/s" not in blob and "mm²/s" not in blob
    assert "burning rate constant" not in blob.lower()


# --- API ------------------------------------------------------------------------------------
def test_api_contract():
    from fastapi.testclient import TestClient
    import api
    client = TestClient(api.app)
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["records"] == 274
    qs = client.get("/questions").json()
    assert len(qs["questions"]) == 7
    ex = client.get("/experiments", params={"fuel": "Methanol",
                                            "limit": 3}).json()
    assert ex["total"] == 157
    q1 = client.post("/query", json={"question_id": "Q1"}).json()
    assert q1["question_id"] == "Q1" and "80.3%" in q1["direct_answer"]
    bad = client.post("/query", json={"question_id": "Q9"}).json()
    assert "error" in bad
    empty = client.post("/query", json={}).json()
    assert "error" in empty
    ev = client.get("/evidence/70").json()
    assert ev["flex_identifier"] == "193F001"
    pred = client.post("/predict", json={"fuel": "Methanol", "d0_mm": 3.0,
                                         "pressure_mmHg": 760, "o2_mf": 0.21,
                                         "n2_mf": 0.79, "co2_mf": 0.0,
                                         "he_mf": 0.0}).json()
    assert "predicted_class" in pred or "error" in pred


# --- integrity -----------------------------------------------------------------------------------
def test_raw_and_frozen_unchanged():
    assert sha256_of(RAW_CSV) == RAW_SHA256
    sys.path.insert(0, os.path.join(ROOT, "analysis", "phase4a", "tests"))
    import test_phase4a as t4a  # holds the 59-file frozen hash constants
    bad = []
    for rel, expected in t4a.PROTECTED_SHA256.items():
        if not os.path.exists(os.path.join(ROOT, rel)):
            bad.append(f"missing: {rel}")
        elif sha256_of(rel) != expected:
            bad.append(rel)
    assert bad == [], bad


def test_no_llm_or_network_calls_in_engine():
    for fname in ("evidence_engine.py", "retrieval.py", "comparability.py",
                  "ranking.py", "api.py"):
        src = open(os.path.join(INT, fname)).read()
        for banned in ("openai", "anthropic", "requests.", "urllib",
                       "httpx", "socket"):
            assert banned not in src, (fname, banned)
