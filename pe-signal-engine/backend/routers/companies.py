from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Company
from ..schemas import CompanyCreate, CompanyRead
from ..services.company_intake import upsert_company, import_csv

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead)
def create_company(data: CompanyCreate, db: Session = Depends(get_db)):
    return upsert_company(db, data)


@router.post("/import", response_model=list[CompanyRead])
async def import_companies(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = (await file.read()).decode("utf-8")
    return import_csv(db, raw)


@router.post("/import-list", response_model=list[CompanyRead])
def import_list(names: list[str], db: Session = Depends(get_db)):
    results = []
    for name in names:
        results.append(upsert_company(db, CompanyCreate(name=name)))
    return results


@router.get("", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).order_by(Company.name).all()


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: str, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404)
    return c


@router.delete("/{company_id}")
def delete_company(company_id: str, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()
    return {"deleted": company_id}
