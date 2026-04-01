"""
Person discovery service.

Orchestrates one or more adapters to find executives matching a search run.
Deduplicates by LinkedIn URL and full name before persisting.
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import Executive, SearchRun, SourceConfig
from ..schemas import ExecutiveCreate
from ..adapters import ADAPTER_REGISTRY


async def discover(db: Session, run: SearchRun) -> int:
    """
    Run all enabled adapters for the given SearchRun.
    Returns the number of new executives inserted.
    """
    source_cfg: dict = run.source_config or {}
    companies: list[str] = run.target_companies or []
    sectors: list[str] = run.target_sectors or []
    countries: list[str] = run.target_countries or ["Sweden", "Norway", "Denmark", "Finland"]

    all_found: list[ExecutiveCreate] = []

    for provider, enabled in source_cfg.items():
        if not enabled:
            continue
        adapter_cls = ADAPTER_REGISTRY.get(provider)
        if not adapter_cls:
            continue

        cfg_row = db.query(SourceConfig).filter(SourceConfig.provider == provider).first()
        api_key = cfg_row.api_key if cfg_row else None
        settings = cfg_row.settings if cfg_row else {}

        adapter = adapter_cls(api_key=api_key, settings=settings)
        try:
            found = await adapter.search_executives(companies, sectors, countries, run.lane)
            all_found.extend(found)
        except Exception:
            pass  # log in production; don't abort run for one adapter failure

    new_count = 0
    for exec_data in all_found:
        if _is_duplicate(db, exec_data, run.id):
            continue
        db.add(_to_model(exec_data, run.id))
        new_count += 1

    db.commit()
    return new_count


def _is_duplicate(db: Session, data: ExecutiveCreate, run_id: str) -> bool:
    q = db.query(Executive).filter(Executive.search_run_id == run_id)
    if data.linkedin_url:
        if q.filter(Executive.linkedin_url == data.linkedin_url).first():
            return True
    if q.filter(Executive.full_name == data.full_name).first():
        return True
    return False


def _to_model(data: ExecutiveCreate, run_id: str) -> Executive:
    return Executive(
        full_name=data.full_name,
        current_title=data.current_title,
        current_company=data.current_company,
        country=data.country,
        sector_tags=data.sector_tags or [],
        lane=data.lane,
        linkedin_url=data.linkedin_url,
        apollo_id=data.apollo_id,
        emails=data.emails or [],
        phones=data.phones or [],
        availability_hypothesis=data.availability_hypothesis,
        best_role_hypothesis=data.best_role_hypothesis,
        search_run_id=run_id,
    )
