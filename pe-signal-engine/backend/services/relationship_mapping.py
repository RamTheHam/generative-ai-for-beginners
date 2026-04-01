"""
Relationship mapping service.

Builds the lightweight graph from evidence items and any existing edges.
All edges land in the relationship_edges table — no separate graph DB needed.

Node types handled:
  Executive, Company, Board, Event, Association, Investor, Advisor, Podcast

Edge types:
  works_at | worked_at | speaks_at | sits_on_board_of | advises |
  member_of | quoted_by | shares_event_with | shares_employer_with | introduced_by
"""
from __future__ import annotations
from datetime import date
from uuid import uuid4
from sqlalchemy.orm import Session
from ..models import Executive, EvidenceItem, RelationshipEdge


def build_edges_from_evidence(db: Session, executive: Executive) -> int:
    """
    Derive relationship edges from evidence items already on record.
    Idempotent — skips edges that already exist for the same (source, target, type).
    """
    evidence = (
        db.query(EvidenceItem)
        .filter(EvidenceItem.executive_id == executive.id)
        .all()
    )
    added = 0
    for ev in evidence:
        edges = _evidence_to_edges(executive, ev)
        for edge_dict in edges:
            if not _edge_exists(db, edge_dict):
                db.add(RelationshipEdge(**edge_dict))
                added += 1
    db.commit()
    return added


def add_manual_edge(
    db: Session,
    source_id: str,
    target_type: str,
    target_name: str,
    edge_type: str,
    evidence_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    confidence: float = 0.8,
) -> RelationshipEdge:
    target_id = f"{target_type}::{target_name.lower().replace(' ', '_')}"
    edge = RelationshipEdge(
        source_id=source_id,
        source_type="executive",
        target_id=target_id,
        target_type=target_type,
        target_name=target_name,
        edge_type=edge_type,
        date_from=date_from,
        date_to=date_to,
        evidence_id=evidence_id,
        confidence=confidence,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


def get_graph(db: Session, executive_id: str) -> dict:
    """
    Return a serialisable graph dict for the frontend visualisation.
    Nodes include the executive + all distinct targets.
    Edges are all edges for this executive.
    """
    exec_obj = db.query(Executive).filter(Executive.id == executive_id).first()
    if not exec_obj:
        return {"nodes": [], "edges": []}

    edges = (
        db.query(RelationshipEdge)
        .filter(RelationshipEdge.source_id == executive_id)
        .all()
    )

    nodes: dict[str, dict] = {
        executive_id: {
            "id": executive_id,
            "label": exec_obj.full_name,
            "type": "executive",
        }
    }
    edge_list = []
    for e in edges:
        if e.target_id not in nodes:
            nodes[e.target_id] = {
                "id": e.target_id,
                "label": e.target_name,
                "type": e.target_type,
            }
        edge_list.append({
            "id": e.id,
            "source": e.source_id,
            "target": e.target_id,
            "edge_type": e.edge_type,
            "confidence": e.confidence,
        })

    return {"nodes": list(nodes.values()), "edges": edge_list}


# ── Internal ───────────────────────────────────────────────────────────────────

def _evidence_to_edges(executive: Executive, ev: EvidenceItem) -> list[dict]:
    base = {
        "source_id": executive.id,
        "source_type": "executive",
        "evidence_id": ev.id,
        "confidence": ev.confidence,
    }
    edges = []

    if ev.signal_type == "role_change" and ev.structured_fields.get("organization_name"):
        org = ev.structured_fields["organization_name"]
        edges.append({**base,
            "target_id": f"company::{_slug(org)}",
            "target_type": "company",
            "target_name": org,
            "edge_type": "works_at" if not ev.structured_fields.get("end_date") else "worked_at",
            "date_from": ev.date_observed,
        })

    elif ev.signal_type == "speaker":
        event_name = ev.structured_fields.get("event_name") or ev.headline or "Unknown Event"
        edges.append({**base,
            "target_id": f"event::{_slug(event_name)}",
            "target_type": "event",
            "target_name": event_name,
            "edge_type": "speaks_at",
            "date_from": ev.date_observed,
        })

    elif ev.signal_type == "board_role":
        org = ev.structured_fields.get("organization_name") or executive.current_company or "Unknown"
        edges.append({**base,
            "target_id": f"board::{_slug(org)}",
            "target_type": "board",
            "target_name": f"Board of {org}",
            "edge_type": "sits_on_board_of",
            "date_from": ev.date_observed,
        })

    elif ev.signal_type == "advisor_role":
        org = ev.structured_fields.get("organization_name") or "Unknown"
        edges.append({**base,
            "target_id": f"company::{_slug(org)}",
            "target_type": "company",
            "target_name": org,
            "edge_type": "advises",
            "date_from": ev.date_observed,
        })

    # Current employer edge from employment facts
    if executive.current_company and ev.source_type == "linkedin":
        edges.append({**base,
            "target_id": f"company::{_slug(executive.current_company)}",
            "target_type": "company",
            "target_name": executive.current_company,
            "edge_type": "works_at",
        })

    return edges


def _edge_exists(db: Session, edge_dict: dict) -> bool:
    return db.query(RelationshipEdge).filter(
        RelationshipEdge.source_id == edge_dict["source_id"],
        RelationshipEdge.target_id == edge_dict["target_id"],
        RelationshipEdge.edge_type == edge_dict["edge_type"],
    ).first() is not None


def _slug(s: str) -> str:
    return s.lower().replace(" ", "_").replace("-", "_")[:60]
