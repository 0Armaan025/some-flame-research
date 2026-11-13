"""FLEX-PSI69 evidence intelligence - interpretable evidence ranking.

Each evidence item is scored on four INDEPENDENT dimensions, each with an
explicit sub-score (0-1) and a human-readable reason. No opaque composite is
presented as authoritative: a documented rule combines the dimensions into a
band (high / moderate / low / excluded), and the rule is printed with every
answer. A highly relevant but poorly documented item cannot reach "high".
"""

from collections import OrderedDict


def _clamp(x):
    return max(0.0, min(1.0, float(x)))


def score_relevance(matched_conditions, total_conditions):
    """Fraction of the query's conditions the item matches exactly."""
    if total_conditions == 0:
        return 1.0, "no conditions specified"
    frac = matched_conditions / total_conditions
    return _clamp(frac), f"{matched_conditions}/{total_conditions} query conditions matched"


def score_data_quality(rec):
    """Completeness of required measurements and freedom from integrity flags."""
    required = ("d0_mm", "d_ext_mm", "burn_rate_raw", "burn_time_s",
                "pressure_mmHg", "o2_mf", "n2_mf", "co2_mf", "he_mf")
    present = sum(1 for k in required if rec.get(k) is not None)
    completeness = present / len(required)
    hard_flags = {"pressure_reported_zero", "extinction_diameter_reported_zero",
                  "extinction_diameter_gt_initial_diameter"}
    flag_penalty = 1.0 if hard_flags & set(rec.get("flags", [])) else 0.0
    soft = {"identifier_collision_193F001", "composition_sum_not_one",
            "contains_approximate_value"} & set(rec.get("flags", []))
    soft_penalty = 0.1 * len(soft)
    score = _clamp(completeness - flag_penalty - soft_penalty)
    notes = [f"{present}/{len(required)} required fields present"]
    if flag_penalty:
        notes.append("hard value-integrity flag present")
    if soft:
        notes.append("soft flag(s): " + ", ".join(sorted(soft)))
    return score, "; ".join(notes)


def score_comparability(rec, comparability="unassessed", shared_bands=None,
                        n2_match=None):
    """Whether the record participates in a defensible comparison."""
    if comparability == "full":
        return 1.0, "fully comparable cell (identical N2, shared pressure band)"
    if comparability == "partial":
        return 0.5, ("partial comparability (N2 balances or bands differ across "
                     "sides; sub-cell alignment only)")
    if comparability == "rejected":
        return 0.0, "comparison rejected (insufficient n or no shared band)"
    if comparability == "same_family":
        return 0.75, "same reported mixture family and pressure band"
    return 0.3, "comparability unassessed for this query type"


def score_statistical_strength(n, effect_size=None, p_value=None,
                               test_used=None):
    """Sample-size dominance with effect size as a modifier; never a fake
    significance claim."""
    if n <= 0:
        return 0.0, "no records"
    size_score = _clamp((n - 3) / 47.0)  # saturates around n=50
    bits = [f"n={n}"]
    if effect_size is not None:
        bits.append(f"effect size {effect_size:.3f}")
    if p_value is not None:
        bits.append(f"p={p_value:.3g}" + (f" ({test_used})" if test_used else ""))
    return size_score, "; ".join(bits)


def combine(dimensions):
    """Documented banding rule. No unexplained composite score."""
    rel, qual, comp, stat = (dimensions["relevance"]["score"],
                             dimensions["data_quality"]["score"],
                             dimensions["comparability"]["score"],
                             dimensions["statistical_strength"]["score"])
    if qual == 0.0 or comp == 0.0:
        band = "excluded_from_primary_evidence"
    elif rel >= 0.99 and qual >= 0.8 and comp >= 0.7 and stat >= 0.4:
        band = "high"
    elif rel >= 0.5 and qual >= 0.6 and comp >= 0.5:
        band = "moderate"
    else:
        band = "low"
    rule = ("band = high iff relevance=1.0, quality>=0.8, comparability>=0.7 and "
            "strength>=0.4; moderate iff relevance>=0.5, quality>=0.6, "
            "comparability>=0.5; excluded iff quality=0 or comparability=0; "
            "otherwise low. Composite arithmetic scores are deliberately not "
            "reported.")
    return band, rule


def rank_evidence(items):
    """items: list of dicts with the four dimension (score, reason) pairs.
    Returns each item augmented with its dimensions and band."""
    out = []
    for it in items:
        dims = OrderedDict(
            relevance=OrderedDict(score=round(it["relevance"][0], 3),
                                  reason=it["relevance"][1]),
            data_quality=OrderedDict(score=round(it["data_quality"][0], 3),
                                     reason=it["data_quality"][1]),
            comparability=OrderedDict(score=round(it["comparability"][0], 3),
                                      reason=it["comparability"][1]),
            statistical_strength=OrderedDict(score=round(it["statistical_strength"][0], 3),
                                             reason=it["statistical_strength"][1]),
        )
        band, rule = combine(dims)
        it = dict(it)
        it["dimensions"] = dims
        it["band"] = band
        it["banding_rule"] = rule
        out.append(it)
    return out