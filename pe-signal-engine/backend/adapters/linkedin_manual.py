"""
Manual / paste-in LinkedIn adapter.

When no automation budget exists, analysts paste LinkedIn profile data
or Google search results directly into the UI.  This adapter normalises
that free-text into the canonical schema.

Also handles raw JSON pasted from LinkedIn Sales Navigator exports
or any LinkedIn-like dict structure.
"""
from __future__ import annotations
from datetime import date
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter


class LinkedInManualAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "manual"

    @property
    def is_configured(self) -> bool:
        return True  # always available — no API key needed

    async def search_executives(self, *args, **kwargs) -> list[ExecutiveCreate]:
        return []

    async def enrich_executive(
        self,
        executive_id: str,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company: str | None = None,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        exec_data = ExecutiveCreate(
            full_name=full_name or "",
            linkedin_url=linkedin_url,
            current_company=company,
        )
        evidence: list[EvidenceCreate] = []
        if linkedin_url:
            evidence.append(self._make_evidence(
                executive_id=executive_id,
                source_type="linkedin",
                source_url=linkedin_url,
                headline=f"Manual LinkedIn entry — {full_name}",
                snippet=f"Manually entered profile for {full_name} at {company or 'unknown company'}",
                signal_type="network_edge",
                confidence=0.60,
            ))
        return exec_data, evidence

    def ingest_manual_note(
        self,
        executive_id: str,
        note: str,
        signal_type: str = "network_edge",
        source_url: str | None = None,
    ) -> EvidenceCreate:
        return self._make_evidence(
            executive_id=executive_id,
            source_type="manual_note",
            source_url=source_url,
            headline="Analyst note",
            snippet=note[:1000],
            date_observed=date.today(),
            signal_type=signal_type,
            confidence=0.90,  # high — analyst-sourced
        )

    def ingest_profile_dict(
        self,
        executive_id: str,
        profile: dict,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        """
        Accept a dict that resembles a LinkedIn profile response
        (Sales Navigator export, browser extension grab, etc.).
        """
        full_name = (
            profile.get("fullName")
            or f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        )
        exec_data = ExecutiveCreate(
            full_name=full_name,
            current_title=profile.get("title") or profile.get("headline"),
            current_company=profile.get("company") or profile.get("companyName"),
            country=profile.get("location") or profile.get("country"),
            linkedin_url=profile.get("linkedInUrl") or profile.get("profileUrl"),
            emails=[profile["email"]] if profile.get("email") else [],
            lane="both",
        )
        evidence = [self._make_evidence(
            executive_id=executive_id,
            source_type="linkedin",
            source_url=exec_data.linkedin_url,
            headline=f"{full_name} — manual profile import",
            snippet=f"{exec_data.current_title} at {exec_data.current_company}",
            signal_type="network_edge",
            confidence=0.70,
            structured_fields=profile,
        )]
        return exec_data, evidence
