"""
Company intake service.

Accepts company names, domains, or bulk CSV imports and normalises them
into the companies table for use in search runs.
"""
from __future__ import annotations
import csv
import io
from sqlalchemy.orm import Session
from ..models import Company
from ..schemas import CompanyCreate


def upsert_company(db: Session, data: CompanyCreate) -> Company:
    existing = db.query(Company).filter(Company.name == data.name).first()
    if existing:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def import_csv(db: Session, raw_csv: str) -> list[Company]:
    reader = csv.DictReader(io.StringIO(raw_csv))
    results = []
    for row in reader:
        data = CompanyCreate(
            name=row.get("name") or row.get("company") or "",
            domain=row.get("domain"),
            country=row.get("country"),
            sector=row.get("sector"),
            hq_city=row.get("city") or row.get("hq_city"),
        )
        if not data.name:
            continue
        results.append(upsert_company(db, data))
    return results


def seed_nordic_sectors(db: Session):
    """Pre-populate the 7 target sectors as company-less sector anchors."""
    pass  # sectors live on executives; no separate sector table needed for v1
