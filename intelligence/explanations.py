"""FLEX-PSI69 evidence intelligence - explanation assembly.

Every engine answer is assembled through `answer_shell()` so that the response
contract (direct answer, supporting experiments, numerical findings, method,
exclusions, contradictions, limitations, resolvers, traceability) is identical
for every question. The shells themselves are built in evidence_engine.py;
this module documents the contract and provides the validation helper used by
the tests and the API to assert that no answer can omit a required field.
"""

from collections import OrderedDict

REQUIRED_FIELDS = (
    "question_id", "question", "direct_answer", "numerical_findings",
    "evidence_ranking", "method", "important_exclusions",
    "contradictory_or_conflicting_evidence", "limitations",
    "what_would_resolve_uncertainty", "traceability",
)


def validate(answer):
    """Return a list of contract violations (empty list = compliant)."""
    problems = []
    for field in REQUIRED_FIELDS:
        if field not in answer:
            problems.append(f"missing field: {field}")
    if not answer.get("limitations"):
        problems.append("limitations must be non-empty")
    if not answer.get("method"):
        problems.append("method must be non-empty")
    for key in ("direct_answer", "traceability"):
        if not answer.get(key):
            problems.append(f"{key} must be non-empty")
    for key in ("important_exclusions",
                "contradictory_or_conflicting_evidence",
                "what_would_resolve_uncertainty"):
        if not isinstance(answer.get(key), list):
            problems.append(f"{key} must be a list")
    return problems


def summarise_for_display(answer):
    """Compact view for a UI: answer, key numbers, top-ranked evidence, and
    the caveats that must be displayed."""
    return OrderedDict(
        question=answer["question"],
        direct_answer=answer["direct_answer"],
        numerical_findings=answer["numerical_findings"],
        top_evidence=[dict(label=item["label"],
                           band=item["band"],
                           dimensions=item["dimensions"])
                      for item in answer.get("evidence_ranking", [])[:3]],
        limitations=answer["limitations"],
        what_would_resolve_uncertainty=answer.get(
            "what_would_resolve_uncertainty", []),
        traceability=answer.get("traceability", []),
    )
