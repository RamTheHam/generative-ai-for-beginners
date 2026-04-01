"""
Scrupp adapter — LinkedIn and Apollo CSV export enrichment.

Scrupp operates as a Chrome extension / web app that exports LinkedIn
search results and Apollo contact lists to CSV/JSON.  This adapter
ingests those exports rather than calling a live API, because Scrupp
does not publish a developer API at the time of writing.

Usage:
  1. Export from Scrupp as JSON (preferred) or CSV.
  2. POST the file contents to /executives/enrich?source=scrupp, or
     place the file path in the source_config settings.

Scrupp JSON row shape (approximate):
  {
    "firstName": "...", "lastName": "...", "title": "...",
    "company": "...", "email": "...", "linkedInUrl": "...",
    "country": "...", "connectionDegree": "1st"
  }
"""
from __future__ import annotations
import json
import csv
import io
from datetime import date
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter


class ScruppAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "scrupp"

    async def search_executives(
        self,
        companies: list[str],
        sectors: list[str],
        countries: list[str],
        lane: str = "both",
    ) -> list[ExecutiveCreate]:
        # Scrupp is export-only — discovery happens in the browser.
        # Caller should use ingest_export() directly.
        return []

    async def enrich_executive(
        self,
        executive_id: str,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company: str | None = None,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        # Single-record enrichment not supported without live API.
        return ExecutiveCreate(full_name=full_name or ""), []

    def ingest_export(
        self,
        raw: str,
        fmt: str = "json",
    ) -> tuple[list[ExecutiveCreate], list[EvidenceCreate]]:
        """
        Parse a Scrupp export (JSON array or CSV) into canonical records.
        Returns (executives, evidence_items).  Evidence is created after
        the caller has persisted the executive and has real IDs.
        """
        if fmt == "json":
            rows = json.loads(raw)
        else:
            reader = csv.DictReader(io.StringIO(raw))
            rows = list(reader)

        executives: list[ExecutiveCreate] = []
        for row in rows:
            executives.append(_row_to_exec(row))
        return executives, []

    def build_evidence(
        self,
        executive_id: str,
        row: dict,
    ) -> list[EvidenceCreate]:
        ev = self._make_evidence(
            executive_id=executive_id,
            source_type="linkedin",
            source_url=row.get("linkedInUrl") or row.get("linkedin_url"),
            headline=f"{row.get('firstName', '')} {row.get('lastName', '')} — Scrupp LinkedIn export",
            snippet=f"{row.get('title', '')} at {row.get('company', '')}",
            signal_type="network_edge",
            confidence=0.70,
            structured_fields={
                "connection_degree": row.get("connectionDegree"),
                "location": row.get("location"),
            },
        )
        return [ev]


def _row_to_exec(row: dict) -> ExecutiveCreate:
    first = row.get("firstName") or row.get("first_name") or ""
    last = row.get("lastName") or row.get("last_name") or ""
    full = row.get("fullName") or row.get("name") or f"{first} {last}".strip()

    emails: list[str] = []
    for key in ("email", "workEmail", "personalEmail"):
        v = row.get(key)
        if v and "@" in v:
            emails.append(v)

    return ExecutiveCreate(
        full_name=full,
        current_title=row.get("title") or row.get("headline"),
        current_company=row.get("company") or row.get("companyName"),
        country=row.get("country") or row.get("location"),
        linkedin_url=row.get("linkedInUrl") or row.get("linkedin_url"),
        emails=emails,
        lane="both",
    )
