from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SourceConfig, ScoreRule
from ..schemas import SourceConfigUpsert, SourceConfigRead, ScoreRuleUpsert, ScoreRuleRead
from ..services.scoring import seed_default_rules

router = APIRouter(prefix="/config", tags=["config"])

_KNOWN_PROVIDERS = [
    "apollo", "scrupp", "phantombuster", "firecrawl", "manual",
    "boardex", "execatlas", "affinity",
]

# ── Source configs ─────────────────────────────────────────────────────────────

@router.get("/sources", response_model=list[SourceConfigRead])
def list_sources(db: Session = Depends(get_db)):
    existing = {r.provider: r for r in db.query(SourceConfig).all()}
    # Ensure all known providers appear even if not yet configured
    for p in _KNOWN_PROVIDERS:
        if p not in existing:
            stub = SourceConfig(provider=p, enabled=False)
            db.add(stub)
    db.commit()
    return db.query(SourceConfig).order_by(SourceConfig.provider).all()


@router.post("/source", response_model=SourceConfigRead)
def upsert_source(data: SourceConfigUpsert, db: Session = Depends(get_db)):
    row = db.query(SourceConfig).filter(SourceConfig.provider == data.provider).first()
    if row:
        row.enabled = data.enabled
        if data.api_key:
            row.api_key = data.api_key
        row.settings = data.settings
    else:
        row = SourceConfig(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/source/{provider}")
def delete_source(provider: str, db: Session = Depends(get_db)):
    row = db.query(SourceConfig).filter(SourceConfig.provider == provider).first()
    if not row:
        raise HTTPException(404)
    db.delete(row)
    db.commit()
    return {"deleted": provider}


# ── Score rules ────────────────────────────────────────────────────────────────

@router.get("/score-rules", response_model=list[ScoreRuleRead])
def list_rules(db: Session = Depends(get_db)):
    seed_default_rules(db)
    return db.query(ScoreRule).order_by(ScoreRule.bucket, ScoreRule.name).all()


@router.post("/score-rules", response_model=ScoreRuleRead)
def upsert_rule(data: ScoreRuleUpsert, db: Session = Depends(get_db)):
    row = db.query(ScoreRule).filter(ScoreRule.condition_key == data.condition_key).first()
    if row:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
    else:
        row = ScoreRule(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/score-rules/{rule_id}", response_model=ScoreRuleRead)
def patch_rule(rule_id: str, data: dict, db: Session = Depends(get_db)):
    row = db.query(ScoreRule).filter(ScoreRule.id == rule_id).first()
    if not row:
        raise HTTPException(404)
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/score-rules/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    row = db.query(ScoreRule).filter(ScoreRule.id == rule_id).first()
    if not row:
        raise HTTPException(404)
    db.delete(row)
    db.commit()
    return {"deleted": rule_id}
