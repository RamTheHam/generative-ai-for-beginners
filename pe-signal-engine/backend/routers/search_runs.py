from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SearchRun, Executive
from ..schemas import SearchRunCreate, SearchRunRead
from ..services import person_discovery, contact_enrichment, open_web_enrichment, scoring

router = APIRouter(prefix="/search-runs", tags=["search-runs"])


@router.post("", response_model=SearchRunRead)
def create_run(data: SearchRunCreate, db: Session = Depends(get_db)):
    run = SearchRun(**data.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[SearchRunRead])
def list_runs(db: Session = Depends(get_db)):
    return db.query(SearchRun).order_by(SearchRun.created_at.desc()).all()


@router.get("/{run_id}", response_model=SearchRunRead)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(SearchRun).filter(SearchRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/{run_id}/start")
async def start_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(SearchRun).filter(SearchRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status == "running":
        raise HTTPException(409, "Run already in progress")

    run.status = "running"
    run.stats = {**run.stats, "stage": "discovery"}
    db.add(run)
    db.commit()

    try:
        # Stage 1: discovery
        new_execs = await person_discovery.discover(db, run)
        run.stats = {**run.stats, "executives_found": new_execs, "stage": "enrichment"}
        db.add(run)
        db.commit()

        # Stage 2: contact enrichment
        await contact_enrichment.enrich_run(db, run.id)
        run.stats = {**run.stats, "stage": "web_enrichment"}
        db.add(run)
        db.commit()

        # Stage 3: open-web enrichment
        executives = db.query(Executive).filter(Executive.search_run_id == run.id).all()
        for ex in executives:
            await open_web_enrichment.enrich_executive_web(db, ex)

        # Stage 4: scoring
        run.stats = {**run.stats, "stage": "scoring"}
        db.add(run)
        db.commit()
        scoring.score_all(db, run.id, run.score_weights)

        # Finalize stats
        total_exec = db.query(Executive).filter(Executive.search_run_id == run.id).count()
        with_contact = db.query(Executive).filter(
            Executive.search_run_id == run.id,
            Executive.contact_confidence > 0,
        ).count()
        run.stats = {
            "stage": "complete",
            "executives_found": total_exec,
            "companies_processed": len(run.target_companies or []),
            "contact_coverage": round(with_contact / total_exec * 100) if total_exec else 0,
            "evidence_items": sum(
                db.query(Executive).filter(Executive.id == ex.id).count()
                for ex in executives
            ),
        }
        run.status = "completed"
        run.completed_at = datetime.utcnow()

    except Exception as exc:
        run.status = "failed"
        run.stats = {**run.stats, "error": str(exc)}

    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/pause")
def pause_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(SearchRun).filter(SearchRun.id == run_id).first()
    if not run:
        raise HTTPException(404)
    run.status = "paused"
    db.add(run)
    db.commit()
    return {"status": "paused"}


@router.delete("/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(SearchRun).filter(SearchRun.id == run_id).first()
    if not run:
        raise HTTPException(404)
    db.delete(run)
    db.commit()
    return {"deleted": run_id}
