"""
Export service.

Generates CSV and JSON exports of executive shortlists and dossiers.
CRM / Drive sync slots are stubbed for Phase 2.
"""
from __future__ import annotations
import csv
import io
import json
from sqlalchemy.orm import Session
from ..models import Executive, EvidenceItem, Dossier


def export_executives_csv(db: Session, executive_ids: list[str] | None = None) -> str:
    q = db.query(Executive)
    if executive_ids:
        q = q.filter(Executive.id.in_(executive_ids))
    executives = q.order_by(Executive.total_score.desc()).all()

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=[
        "full_name", "current_title", "current_company", "country",
        "lane", "total_score", "transition_score", "pe_fit_score",
        "network_score", "reachability_score", "emails", "phones",
        "linkedin_url", "dossier_status", "signal_flags", "last_signal_date",
    ])
    writer.writeheader()
    for ex in executives:
        writer.writerow({
            "full_name": ex.full_name,
            "current_title": ex.current_title or "",
            "current_company": ex.current_company or "",
            "country": ex.country or "",
            "lane": ex.lane,
            "total_score": ex.total_score,
            "transition_score": ex.transition_score,
            "pe_fit_score": ex.pe_fit_score,
            "network_score": ex.network_score,
            "reachability_score": ex.reachability_score,
            "emails": "; ".join(ex.emails or []),
            "phones": "; ".join(ex.phones or []),
            "linkedin_url": ex.linkedin_url or "",
            "dossier_status": ex.dossier_status,
            "signal_flags": ", ".join(ex.signal_flags or []),
            "last_signal_date": str(ex.last_signal_date) if ex.last_signal_date else "",
        })
    return out.getvalue()


def export_executives_json(db: Session, executive_ids: list[str] | None = None) -> str:
    q = db.query(Executive)
    if executive_ids:
        q = q.filter(Executive.id.in_(executive_ids))
    executives = q.order_by(Executive.total_score.desc()).all()
    data = []
    for ex in executives:
        d = {c.name: getattr(ex, c.name) for c in ex.__table__.columns}
        # convert non-serialisable types
        for k in ("created_at", "updated_at", "last_signal_date"):
            if d.get(k):
                d[k] = str(d[k])
        data.append(d)
    return json.dumps(data, indent=2)


# ── Future CRM sync stubs ──────────────────────────────────────────────────────

async def sync_to_hubspot(db: Session, executive_ids: list[str]) -> dict:
    raise NotImplementedError("HubSpot sync is a Phase 2 feature.")


async def sync_to_affinity(db: Session, executive_ids: list[str]) -> dict:
    raise NotImplementedError("Affinity sync is a Phase 3 feature.")


async def sync_to_google_drive(db: Session, executive_ids: list[str]) -> dict:
    raise NotImplementedError("Google Drive sync is a Phase 2 feature.")
