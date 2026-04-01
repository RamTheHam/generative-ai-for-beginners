"""
Apollo.io adapter — people search + contact enrichment.

Live endpoints used:
  POST https://api.apollo.io/v1/mixed_people/search
  POST https://api.apollo.io/v1/people/match

Docs: https://apolloio.github.io/apollo-api-docs/
"""
from __future__ import annotations
import httpx
from datetime import date
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter

_BASE = "https://api.apollo.io/v1"

# Apollo seniority labels that indicate exec-level
_EXEC_SENIORITIES = ["c_suite", "vp", "director", "partner", "owner", "founder"]

# Map Apollo seniority → lane hypothesis
_SENIORITY_LANE = {
    "c_suite": "transition",
    "vp": "both",
    "director": "both",
    "partner": "successor",
    "owner": "transition",
    "founder": "transition",
}


class ApolloAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "apollo"

    async def search_executives(
        self,
        companies: list[str],
        sectors: list[str],
        countries: list[str],
        lane: str = "both",
    ) -> list[ExecutiveCreate]:
        if not self.is_configured:
            return []

        # Apollo uses ISO alpha-2 country codes; map Nordic names
        country_codes = _to_iso2(countries)

        payload: dict = {
            "api_key": self.api_key,
            "page": 1,
            "per_page": 25,
            "seniorities": _EXEC_SENIORITIES,
            "person_locations": country_codes or ["SE", "NO", "DK", "FI"],
        }
        if companies:
            payload["organization_names"] = companies[:10]  # Apollo limits
        if sectors:
            payload["q_keywords"] = " OR ".join(sectors[:5])

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{_BASE}/mixed_people/search", json=payload)
            resp.raise_for_status()
            data = resp.json()

        results: list[ExecutiveCreate] = []
        for person in data.get("people", []):
            results.append(_person_to_exec(person))
        return results

    async def enrich_executive(
        self,
        executive_id: str,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company: str | None = None,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        if not self.is_configured:
            return ExecutiveCreate(full_name=full_name or ""), []

        payload: dict = {"api_key": self.api_key, "reveal_personal_emails": False}
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        elif full_name:
            payload["name"] = full_name
            if company:
                payload["organization_name"] = company

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{_BASE}/people/match", json=payload)
            resp.raise_for_status()
            data = resp.json()

        person = data.get("person", {})
        if not person:
            return ExecutiveCreate(full_name=full_name or ""), []

        exec_data = _person_to_exec(person)

        evidence: list[EvidenceCreate] = []
        # Emit a LinkedIn evidence item if we have a URL
        if person.get("linkedin_url"):
            evidence.append(self._make_evidence(
                executive_id=executive_id,
                source_type="linkedin",
                source_url=person["linkedin_url"],
                headline=f"{exec_data.full_name} — LinkedIn profile via Apollo",
                snippet=f"Title: {exec_data.current_title or ''} at {exec_data.current_company or ''}",
                signal_type="network_edge",
                confidence=0.85,
                structured_fields={"apollo_id": person.get("id")},
            ))

        # Emit evidence for each employment history entry that looks exec-level
        for job in (person.get("employment_history") or [])[:3]:
            if not job.get("title"):
                continue
            evidence.append(self._make_evidence(
                executive_id=executive_id,
                source_type="linkedin",
                source_url=person.get("linkedin_url"),
                headline=f"{job.get('title')} at {job.get('organization_name', '')}",
                snippet=f"From {job.get('start_date', '?')} to {job.get('end_date', 'present')}",
                date_observed=_parse_apollo_date(job.get("start_date")),
                signal_type="role_change" if not job.get("end_date") else "network_edge",
                confidence=0.75,
                structured_fields=job,
            ))

        return exec_data, evidence


def _person_to_exec(person: dict) -> ExecutiveCreate:
    org = (person.get("organization") or {})
    seniority = person.get("seniority", "")
    return ExecutiveCreate(
        full_name=person.get("name", ""),
        current_title=person.get("title"),
        current_company=org.get("name") or person.get("organization_name"),
        country=person.get("country"),
        sector_tags=_extract_sectors(person),
        lane=_SENIORITY_LANE.get(seniority, "both"),
        linkedin_url=person.get("linkedin_url"),
        apollo_id=person.get("id"),
        emails=_collect(person, "email", "personal_emails", "work_emails"),
        phones=_collect_phones(person),
    )


def _collect(person: dict, *keys: str) -> list[str]:
    out: list[str] = []
    for k in keys:
        v = person.get(k)
        if isinstance(v, str) and v:
            out.append(v)
        elif isinstance(v, list):
            out.extend(x for x in v if x)
    return list(dict.fromkeys(out))  # deduplicate preserving order


def _collect_phones(person: dict) -> list[str]:
    phones: list[str] = []
    for ph in person.get("phone_numbers") or []:
        if isinstance(ph, dict):
            n = ph.get("sanitized_number") or ph.get("raw_number")
            if n:
                phones.append(n)
        elif isinstance(ph, str):
            phones.append(ph)
    return phones


def _extract_sectors(person: dict) -> list[str]:
    org = person.get("organization") or {}
    industries = org.get("industry_tag_values") or org.get("industries") or []
    keywords = person.get("keywords") or []
    return list({s for s in (industries + keywords) if s})[:8]


def _to_iso2(country_names: list[str]) -> list[str]:
    _map = {
        "sweden": "SE", "norway": "NO", "denmark": "DK",
        "finland": "FI", "iceland": "IS",
        "germany": "DE", "netherlands": "NL", "france": "FR",
        "united kingdom": "GB", "uk": "GB",
    }
    out = []
    for c in country_names:
        code = _map.get(c.lower(), c.upper()[:2])
        out.append(code)
    return out


def _parse_apollo_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        parts = s.split("-")
        return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1, 1)
    except Exception:
        return None
