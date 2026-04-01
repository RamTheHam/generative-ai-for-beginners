"""
Firecrawl adapter — open-web enrichment.

Used for:
  - Conference speaker pages
  - Company leadership / team pages
  - Board member pages
  - Press releases and newsrooms
  - Podcast guest lists
  - Association membership directories

API docs: https://docs.firecrawl.dev/

Two modes:
  scrape  — single URL → markdown + metadata
  search  — natural language query → list of URLs + snippets (Firecrawl Search)
"""
from __future__ import annotations
import httpx
import re
from datetime import date
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter

_BASE = "https://api.firecrawl.dev/v1"

_SIGNAL_KEYWORDS = {
    "role_change": ["joins", "appointed", "named", "promoted", "steps down", "leaves", "exits"],
    "speaker": ["speaker", "keynote", "panelist", "moderator", "presenting", "session chair"],
    "board_role": ["board of directors", "board member", "non-executive", "chair", "chairman"],
    "advisor_role": ["advisor", "advisory board", "strategic advisor", "venture partner"],
    "m_and_a": ["acquisition", "merger", "acquired", "takeover", "deal"],
    "integration": ["integration", "post-merger", "carve-out", "transition"],
    "pricing": ["pricing", "monetisation", "revenue model", "arpu", "price increase"],
    "turnaround": ["turnaround", "restructure", "cost reduction", "transformation", "rightsizing"],
    "international_scale": ["expansion", "international", "market entry", "cross-border", "global"],
}


class FirecrawlAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "firecrawl"

    async def search_executives(
        self,
        companies: list[str],
        sectors: list[str],
        countries: list[str],
        lane: str = "both",
    ) -> list[ExecutiveCreate]:
        """
        Use Firecrawl Search to find executive mentions across public web.
        Returns skeleton ExecutiveCreate objects — caller enriches further.
        """
        if not self.is_configured:
            return []

        queries = _build_queries(companies, sectors, countries, lane)
        results: list[ExecutiveCreate] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for q in queries[:5]:  # limit API spend
                resp = await client.post(
                    f"{_BASE}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"query": q, "limit": 10},
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json().get("data", []):
                    exec_data = _item_to_exec(item)
                    if exec_data:
                        results.append(exec_data)

        return results

    async def enrich_executive(
        self,
        executive_id: str,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company: str | None = None,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        if not self.is_configured or not full_name:
            return ExecutiveCreate(full_name=full_name or ""), []

        evidence: list[EvidenceCreate] = []
        queries = [f'"{full_name}" {company or ""} executive']
        if company:
            queries.append(f'site:{_company_domain(company)} {full_name}')

        async with httpx.AsyncClient(timeout=30) as client:
            for q in queries[:3]:
                resp = await client.post(
                    f"{_BASE}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"query": q, "limit": 5},
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json().get("data", []):
                    ev = _item_to_evidence(executive_id, item, self.provider_name)
                    if ev:
                        evidence.append(ev)

        return ExecutiveCreate(full_name=full_name), evidence

    async def scrape_url(
        self,
        executive_id: str,
        url: str,
        source_type: str = "company_news",
    ) -> list[EvidenceCreate]:
        """Scrape a specific URL and extract evidence."""
        if not self.is_configured:
            return []

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{_BASE}/scrape",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"url": url, "formats": ["markdown"]},
            )
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", {})

        md = data.get("markdown", "")
        meta = data.get("metadata", {})
        signal = _detect_signal(md)

        return [self._make_evidence(
            executive_id=executive_id,
            source_type=source_type,
            source_url=url,
            headline=meta.get("title") or url,
            snippet=md[:500],
            date_observed=_parse_date(meta.get("publishedDate")),
            signal_type=signal,
            confidence=0.65,
            structured_fields={"word_count": len(md.split())},
        )]


def _build_queries(
    companies: list[str],
    sectors: list[str],
    countries: list[str],
    lane: str,
) -> list[str]:
    qs = []
    geo = " OR ".join(countries[:3]) if countries else "Sweden OR Nordics"
    for co in companies[:3]:
        qs.append(f'"{co}" CEO OR CFO OR COO OR "VP" leadership team')
    for sector in sectors[:2]:
        qs.append(f'{sector} executive speaker {geo} 2024 OR 2025')
    if lane in ("transition", "both"):
        qs.append(f'executive transition appointment announcement {geo}')
    if lane in ("successor", "both"):
        qs.append(f'keynote speaker industry conference {geo} {" ".join(sectors[:2])}')
    return qs


def _item_to_exec(item: dict) -> ExecutiveCreate | None:
    title_str = item.get("title") or ""
    snippet = item.get("description") or item.get("snippet") or ""
    # Heuristic: extract a name from the title if it looks like "Name - Company"
    name = _extract_name_heuristic(title_str)
    if not name:
        return None
    return ExecutiveCreate(full_name=name, linkedin_url=None, lane="both")


def _item_to_evidence(executive_id: str, item: dict, provider: str) -> EvidenceCreate | None:
    url = item.get("url") or ""
    snippet = item.get("description") or item.get("snippet") or ""
    if not snippet:
        return None
    signal = _detect_signal(snippet)
    return EvidenceCreate(
        executive_id=executive_id,
        source_provider=provider,
        source_type=_infer_source_type(url),
        source_url=url,
        headline=item.get("title"),
        snippet=snippet[:400],
        signal_type=signal,
        confidence=0.55,
    )


def _detect_signal(text: str) -> str:
    t = text.lower()
    for sig, keywords in _SIGNAL_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return sig
    return "network_edge"


def _infer_source_type(url: str) -> str:
    u = url.lower()
    if "linkedin" in u:
        return "linkedin"
    if any(x in u for x in ["podcast", "spotify", "soundcloud"]):
        return "podcast"
    if any(x in u for x in ["conference", "summit", "event", "agenda"]):
        return "conference"
    if any(x in u for x in ["press", "news", "newsroom", "announcement"]):
        return "press_release"
    if "board" in u:
        return "board_page"
    return "company_news"


def _extract_name_heuristic(title: str) -> str | None:
    # Looks for "Firstname Lastname" at start of title
    m = re.match(r"^([A-Z][a-z]+ [A-Z][a-z]+(?:-[A-Z][a-z]+)?)", title)
    return m.group(1) if m else None


def _company_domain(company: str) -> str:
    return company.lower().replace(" ", "") + ".com"


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None
