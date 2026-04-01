"""
Open-web enrichment service.

Uses Firecrawl to pull evidence from:
  - Conference and event speaker pages
  - Company leadership pages
  - Press releases and newsrooms
  - Board pages
  - Podcast pages

Evidence items created here feed directly into the scoring model.
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from ..models import Executive, EvidenceItem, SourceConfig
from ..adapters.firecrawl import FirecrawlAdapter

_SPEAKER_SITES = [
    "https://www.investorsummit.se/speakers",
    "https://www.nordicbusinessforum.com/speakers",
    "https://www.dealmaker.tech/speakers",
]


async def enrich_executive_web(db: Session, executive: Executive) -> int:
    cfg_row = db.query(SourceConfig).filter(SourceConfig.provider == "firecrawl").first()
    if not cfg_row or not cfg_row.enabled or not cfg_row.api_key:
        return 0

    adapter = FirecrawlAdapter(api_key=cfg_row.api_key, settings=cfg_row.settings or {})
    _, evidence_list = await adapter.enrich_executive(
        executive_id=executive.id,
        full_name=executive.full_name,
        company=executive.current_company,
    )

    added = 0
    for ev in evidence_list:
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

    db.commit()
    return added


async def scrape_specific_url(
    db: Session,
    executive_id: str,
    url: str,
    source_type: str = "company_news",
) -> int:
    cfg_row = db.query(SourceConfig).filter(SourceConfig.provider == "firecrawl").first()
    if not cfg_row or not cfg_row.api_key:
        return 0

    adapter = FirecrawlAdapter(api_key=cfg_row.api_key)
    evidence_list = await adapter.scrape_url(executive_id, url, source_type)

    for ev in evidence_list:
        db.add(EvidenceItem(
            executive_id=executive_id,
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
    db.commit()
    return len(evidence_list)
