"""
Contact enrichment service.

For each executive without verified contact data, call enabled enrichment
adapters (Apollo first, then Scrupp) and merge results back.
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import Executive, EvidenceItem, SourceConfig
from ..adapters import ADAPTER_REGISTRY

_ENRICHMENT_PROVIDERS = ["apollo", "scrupp", "phantombuster", "manual"]


async def enrich_executive(db: Session, executive: Executive) -> int:
    """
    Enrich one executive.  Returns number of new evidence items added.
    """
    added = 0
    source_mix: list[str] = list(executive.source_mix or [])

    for provider in _ENRICHMENT_PROVIDERS:
        adapter_cls = ADAPTER_REGISTRY.get(provider)
        if not adapter_cls:
            continue

        cfg_row = db.query(SourceConfig).filter(SourceConfig.provider == provider).first()
        if not cfg_row or not cfg_row.enabled:
            continue

        adapter = adapter_cls(api_key=cfg_row.api_key, settings=cfg_row.settings or {})
        try:
            updated_exec, evidence_items = await adapter.enrich_executive(
                executive_id=executive.id,
                linkedin_url=executive.linkedin_url,
                full_name=executive.full_name,
                company=executive.current_company,
            )
        except Exception:
            continue

        # Merge contact data
        existing_emails = set(executive.emails or [])
        for e in (updated_exec.emails or []):
            if e and e not in existing_emails:
                existing_emails.add(e)
        executive.emails = list(existing_emails)

        existing_phones = set(executive.phones or [])
        for p in (updated_exec.phones or []):
            if p and p not in existing_phones:
                existing_phones.add(p)
        executive.phones = list(existing_phones)

        # Fill blanks
        if not executive.current_title and updated_exec.current_title:
            executive.current_title = updated_exec.current_title
        if not executive.current_company and updated_exec.current_company:
            executive.current_company = updated_exec.current_company
        if not executive.country and updated_exec.country:
            executive.country = updated_exec.country
        if not executive.apollo_id and updated_exec.apollo_id:
            executive.apollo_id = updated_exec.apollo_id

        # Persist evidence
        for ev in evidence_items:
            db.add(EvidenceItem(
                executive_id=executive.id,
                source_provider=ev.source_provider,
                source_type=ev.source_type,
                source_url=ev.source_url,
                headline=ev.headline,
                snippet=ev.snippet,
                date_observed=ev.date_observed,
                signal_type=ev.signal_type,
                confidence=ev.confidence,
                structured_fields=ev.structured_fields or {},
            ))
            added += 1

        if provider not in source_mix:
            source_mix.append(provider)

    executive.source_mix = source_mix
    executive.contact_confidence = _calc_confidence(executive)
    db.add(executive)
    db.commit()
    return added


async def enrich_run(db: Session, run_id: str) -> int:
    executives = db.query(Executive).filter(Executive.search_run_id == run_id).all()
    total = 0
    for ex in executives:
        total += await enrich_executive(db, ex)
    return total


def _calc_confidence(executive: Executive) -> float:
    score = 0.0
    if executive.emails:
        score += 0.6
    if executive.phones:
        score += 0.3
    if executive.linkedin_url:
        score += 0.1
    return round(min(1.0, score), 2)
