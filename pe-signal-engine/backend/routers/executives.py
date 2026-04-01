from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Executive, EvidenceItem, Dossier, OutreachAction
from ..schemas import (
    ExecutiveCreate, ExecutiveRead, ExecutiveScoreOverride,
    EvidenceCreate, EvidenceRead, DossierRead, OutreachCreate, OutreachRead,
)
from ..services import contact_enrichment, open_web_enrichment, scoring, dossier as dossier_svc
from ..services.relationship_mapping import build_edges_from_evidence, get_graph, add_manual_edge
from ..services.export import export_executives_csv, export_executives_json

router = APIRouter(prefix="/executives", tags=["executives"])


# ── List / search ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[ExecutiveRead])
def list_executives(
    run_id: str | None = Query(None),
    lane: str | None = Query(None),
    country: str | None = Query(None),
    sector: str | None = Query(None),
    min_score: float = Query(0),
    dossier_status: str | None = Query(None),
    has_contact: bool | None = Query(None),
    sort_by: str = Query("total_score"),
    sort_dir: str = Query("desc"),
    limit: int = Query(200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    q = db.query(Executive)
    if run_id:
        q = q.filter(Executive.search_run_id == run_id)
    if lane:
        q = q.filter(Executive.lane.in_([lane, "both"]))
    if country:
        q = q.filter(Executive.country.ilike(f"%{country}%"))
    if min_score:
        q = q.filter(Executive.total_score >= min_score)
    if dossier_status:
        q = q.filter(Executive.dossier_status == dossier_status)
    if has_contact is True:
        q = q.filter(Executive.contact_confidence > 0)
    if has_contact is False:
        q = q.filter(Executive.contact_confidence == 0)

    col = getattr(Executive, sort_by, Executive.total_score)
    if sort_dir == "desc":
        q = q.order_by(col.desc())
    else:
        q = q.order_by(col.asc())

    return q.offset(offset).limit(limit).all()


@router.get("/export/csv", response_class=PlainTextResponse)
def export_csv(run_id: str | None = Query(None), db: Session = Depends(get_db)):
    ids = None
    if run_id:
        ids = [e.id for e in db.query(Executive.id).filter(Executive.search_run_id == run_id)]
    return export_executives_csv(db, ids)


@router.get("/export/json")
def export_json(run_id: str | None = Query(None), db: Session = Depends(get_db)):
    ids = None
    if run_id:
        ids = [e.id for e in db.query(Executive.id).filter(Executive.search_run_id == run_id)]
    return export_executives_json(db, ids)


# ── Single executive ───────────────────────────────────────────────────────────

@router.post("", response_model=ExecutiveRead)
def create_executive(data: ExecutiveCreate, db: Session = Depends(get_db)):
    exec_obj = Executive(**data.model_dump())
    db.add(exec_obj)
    db.commit()
    db.refresh(exec_obj)
    return exec_obj


@router.get("/{exec_id}", response_model=ExecutiveRead)
def get_executive(exec_id: str, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    return ex


@router.patch("/{exec_id}", response_model=ExecutiveRead)
def patch_executive(exec_id: str, data: dict, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    allowed = {
        "current_title", "current_company", "country", "sector_tags",
        "lane", "linkedin_url", "availability_hypothesis",
        "best_role_hypothesis", "dossier_status",
    }
    for k, v in data.items():
        if k in allowed:
            setattr(ex, k, v)
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


@router.delete("/{exec_id}")
def delete_executive(exec_id: str, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    db.delete(ex)
    db.commit()
    return {"deleted": exec_id}


# ── Enrichment ─────────────────────────────────────────────────────────────────

@router.post("/{exec_id}/enrich")
async def enrich_executive(exec_id: str, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    contact_added = await contact_enrichment.enrich_executive(db, ex)
    web_added = await open_web_enrichment.enrich_executive_web(db, ex)
    build_edges_from_evidence(db, ex)
    scores = scoring.score_executive(db, ex)
    return {"contact_evidence_added": contact_added, "web_evidence_added": web_added, **scores}


# ── Scoring ────────────────────────────────────────────────────────────────────

@router.post("/{exec_id}/score")
def rescore(exec_id: str, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    return scoring.score_executive(db, ex)


@router.post("/{exec_id}/override-score", response_model=ExecutiveRead)
def override_score(exec_id: str, data: ExecutiveScoreOverride, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    if data.transition_score is not None:
        ex.transition_score = data.transition_score
    if data.pe_fit_score is not None:
        ex.pe_fit_score = data.pe_fit_score
    if data.network_score is not None:
        ex.network_score = data.network_score
    if data.reachability_score is not None:
        ex.reachability_score = data.reachability_score
    # Recalculate total using equal weights for manual overrides
    ex.total_score = round(
        (ex.transition_score * 0.30 + ex.pe_fit_score * 0.35 +
         ex.network_score * 0.20 + ex.reachability_score * 0.15), 1
    )
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


# ── Evidence ───────────────────────────────────────────────────────────────────

@router.get("/{exec_id}/evidence", response_model=list[EvidenceRead])
def get_evidence(exec_id: str, db: Session = Depends(get_db)):
    return (
        db.query(EvidenceItem)
        .filter(EvidenceItem.executive_id == exec_id)
        .order_by(EvidenceItem.date_observed.desc())
        .all()
    )


@router.post("/{exec_id}/evidence", response_model=EvidenceRead)
def add_evidence(exec_id: str, data: EvidenceCreate, db: Session = Depends(get_db)):
    ev = EvidenceItem(**data.model_dump())
    ev.executive_id = exec_id
    db.add(ev)
    db.commit()
    db.refresh(ev)
    # Re-score after new evidence
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if ex:
        scoring.score_executive(db, ex)
    return ev


# ── Graph ──────────────────────────────────────────────────────────────────────

@router.get("/{exec_id}/graph")
def get_exec_graph(exec_id: str, db: Session = Depends(get_db)):
    return get_graph(db, exec_id)


@router.post("/{exec_id}/graph/edges")
def add_edge(exec_id: str, data: dict, db: Session = Depends(get_db)):
    edge = add_manual_edge(
        db,
        source_id=exec_id,
        target_type=data.get("target_type", "company"),
        target_name=data.get("target_name", ""),
        edge_type=data.get("edge_type", "works_at"),
        evidence_id=data.get("evidence_id"),
        confidence=data.get("confidence", 0.8),
    )
    return {"id": edge.id}


# ── Dossier ────────────────────────────────────────────────────────────────────

@router.post("/{exec_id}/dossier", response_model=DossierRead)
async def generate_dossier(exec_id: str, db: Session = Depends(get_db)):
    ex = db.query(Executive).filter(Executive.id == exec_id).first()
    if not ex:
        raise HTTPException(404)
    return await dossier_svc.generate_dossier(db, ex)


@router.get("/{exec_id}/dossier", response_model=DossierRead)
def get_dossier(exec_id: str, db: Session = Depends(get_db)):
    d = db.query(Dossier).filter(Dossier.executive_id == exec_id).first()
    if not d:
        raise HTTPException(404, "No dossier yet — call POST to generate")
    return d


# ── Outreach ───────────────────────────────────────────────────────────────────

@router.get("/{exec_id}/outreach", response_model=list[OutreachRead])
def list_outreach(exec_id: str, db: Session = Depends(get_db)):
    return db.query(OutreachAction).filter(OutreachAction.executive_id == exec_id).all()


@router.post("/{exec_id}/outreach", response_model=OutreachRead)
def add_outreach(exec_id: str, data: OutreachCreate, db: Session = Depends(get_db)):
    action = OutreachAction(**data.model_dump())
    action.executive_id = exec_id
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
