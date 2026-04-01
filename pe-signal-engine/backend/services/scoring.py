"""
Scoring service.

Produces the four score buckets and a weighted total for a given executive
based on their evidence items and relationship edges.  All rules are
loaded from the score_rules table so they can be edited in the admin UI
without a redeploy.

Default rule set mirrors the brief exactly:
  Transition  30 %  |  PE Fit  35 %  |  Network  20 %  |  Reachability  15 %

Scores are clamped 0–100.  Total is the weighted sum.
"""
from __future__ import annotations
from datetime import date
from sqlalchemy.orm import Session
from ..models import Executive, EvidenceItem, RelationshipEdge, ScoreRule

_DEFAULT_WEIGHTS = {
    "transition": 0.30,
    "pe_fit": 0.35,
    "network": 0.20,
    "reachability": 0.15,
}

_BASE = {
    "transition": 40,
    "pe_fit": 40,
    "network": 30,
    "reachability": 30,
}


def score_executive(
    db: Session,
    executive: Executive,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Recalculate scores for one executive.  Mutates the executive ORM object
    and returns a dict with the score breakdown.
    """
    evidence = db.query(EvidenceItem).filter(EvidenceItem.executive_id == executive.id).all()
    edges = db.query(RelationshipEdge).filter(RelationshipEdge.source_id == executive.id).all()
    rules = {r.condition_key: r for r in db.query(ScoreRule).filter(ScoreRule.enabled == True).all()}

    w = weights or _DEFAULT_WEIGHTS
    scores = {k: float(v) for k, v in _BASE.items()}
    flags: list[str] = []

    today = date.today()

    # ── Evidence-based scoring ─────────────────────────────────────────────────
    has_contact = bool(executive.emails or executive.phones)
    has_operational = False
    most_recent_date: date | None = None

    for ev in evidence:
        if ev.date_observed and (most_recent_date is None or ev.date_observed > most_recent_date):
            most_recent_date = ev.date_observed

        sig = ev.signal_type or ""

        if sig == "role_change":
            if ev.date_observed and (today - ev.date_observed).days <= 180:
                scores["transition"] += _rule(rules, "recent_role_change", 20)
                _flag(flags, "recent_role_change")
            else:
                scores["transition"] += 8

        elif sig in ("board_role", "advisor_role"):
            scores["transition"] += _rule(rules, "board_or_advisor_role", 15)
            _flag(flags, "board_or_advisor_role")

        elif sig == "speaker":
            scores["network"] += _rule(rules, "event_speaker", 15)
            _flag(flags, "event_speaker")

        elif sig in ("m_and_a", "integration", "pricing", "turnaround", "international_scale"):
            scores["pe_fit"] += _rule(rules, "pe_operational_signal", 15)
            has_operational = True
            _flag(flags, f"pe_{sig}")

        elif sig == "network_edge":
            scores["network"] += 3

    # ── Contact coverage ───────────────────────────────────────────────────────
    if has_contact:
        scores["reachability"] += _rule(rules, "contact_data_present", 10)
        _flag(flags, "contact_verified")

    # ── Graph adjacency ────────────────────────────────────────────────────────
    board_edges = [e for e in edges if e.edge_type in ("sits_on_board_of", "advises")]
    if len(board_edges) >= 2:
        scores["network"] += _rule(rules, "board_adjacency", 10)
        _flag(flags, "board_adjacency")

    warm_edges = [e for e in edges if e.edge_type == "introduced_by"]
    if warm_edges:
        scores["reachability"] += 12
        _flag(flags, "warm_intro_path")

    # ── Penalties ─────────────────────────────────────────────────────────────
    if not has_operational:
        scores["pe_fit"] += _rule(rules, "no_operational_ownership", -15)

    if most_recent_date and (today - most_recent_date).days > 365:
        scores["transition"] += _rule(rules, "stale_evidence", -10)
        scores["pe_fit"] += _rule(rules, "stale_evidence", -5)
        _flag(flags, "stale_evidence")

    # Clamp
    for k in scores:
        scores[k] = max(0, min(100, scores[k]))

    total = sum(scores[k] * w.get(k, 0) for k in scores)
    total = max(0, min(100, total))

    # Persist
    executive.transition_score = round(scores["transition"], 1)
    executive.pe_fit_score = round(scores["pe_fit"], 1)
    executive.network_score = round(scores["network"], 1)
    executive.reachability_score = round(scores["reachability"], 1)
    executive.total_score = round(total, 1)
    executive.signal_flags = list(set(flags))
    if most_recent_date:
        executive.last_signal_date = most_recent_date

    db.add(executive)
    db.commit()
    db.refresh(executive)

    return {
        "transition_score": executive.transition_score,
        "pe_fit_score": executive.pe_fit_score,
        "network_score": executive.network_score,
        "reachability_score": executive.reachability_score,
        "total_score": executive.total_score,
        "signal_flags": executive.signal_flags,
    }


def score_all(db: Session, search_run_id: str, weights: dict | None = None):
    execs = db.query(Executive).filter(Executive.search_run_id == search_run_id).all()
    for ex in execs:
        score_executive(db, ex, weights)


def _rule(rules: dict, key: str, default: float) -> float:
    r = rules.get(key)
    return r.delta if r else default


def _flag(flags: list[str], name: str):
    if name not in flags:
        flags.append(name)


def seed_default_rules(db: Session):
    """Insert default scoring rules if the table is empty."""
    if db.query(ScoreRule).count() > 0:
        return
    defaults = [
        ("recent_role_change",      "transition",   20, "Role change within 180 days"),
        ("board_or_advisor_role",   "transition",   15, "Board or advisor role added"),
        ("event_speaker",           "network",      15, "Speaker or panellist at relevant event"),
        ("pe_operational_signal",   "pe_fit",       15, "Evidence of pricing / M&A / turnaround / scale ownership"),
        ("contact_data_present",    "reachability", 10, "Apollo or Scrupp returned good contact data"),
        ("board_adjacency",         "network",      10, "Repeated board or investor adjacency in graph"),
        ("no_operational_ownership","pe_fit",      -15, "No operating ownership visible in evidence"),
        ("stale_evidence",          "transition",  -10, "Most recent evidence is older than 12 months"),
    ]
    for name, bucket, delta, desc in defaults:
        db.add(ScoreRule(
            name=name,
            bucket=bucket,
            condition_key=name,
            delta=delta,
            description=desc,
            enabled=True,
        ))
    db.commit()
