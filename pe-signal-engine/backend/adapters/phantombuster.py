"""
PhantomBuster adapter — LinkedIn employee export automation.

Relevant phantoms:
  - LinkedIn Company Employees Export   (agentId in settings)
  - LinkedIn Search Export

API docs: https://phantombuster.com/api-documentation

This adapter:
  1. Launches a pre-configured phantom with a company list.
  2. Polls until the phantom finishes.
  3. Fetches and parses the output JSON.

Set up phantoms manually in PhantomBuster UI first, then paste their
agent IDs into source_config.settings.agent_ids.
"""
from __future__ import annotations
import asyncio
import httpx
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter

_BASE = "https://api.phantombuster.com/api/v2"


class PhantomBusterAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "phantombuster"

    async def search_executives(
        self,
        companies: list[str],
        sectors: list[str],
        countries: list[str],
        lane: str = "both",
    ) -> list[ExecutiveCreate]:
        if not self.is_configured:
            return []

        agent_ids: list[str] = self.settings.get("agent_ids", [])
        if not agent_ids:
            return []

        results: list[ExecutiveCreate] = []
        for agent_id in agent_ids:
            output = await self._run_and_fetch(agent_id)
            results.extend(_parse_output(output))
        return results

    async def enrich_executive(
        self,
        executive_id: str,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company: str | None = None,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        # PhantomBuster enrichment requires a dedicated profile-scraper phantom
        # configured per user.  For now return empty; add agent_id for profile
        # scraper in settings to enable.
        enrich_agent = self.settings.get("profile_agent_id")
        if not self.is_configured or not enrich_agent or not linkedin_url:
            return ExecutiveCreate(full_name=full_name or ""), []

        output = await self._run_and_fetch(enrich_agent, argument={"linkedInUrl": linkedin_url})
        rows = output if isinstance(output, list) else [output]
        if not rows:
            return ExecutiveCreate(full_name=full_name or ""), []

        exec_data = _row_to_exec(rows[0])
        evidence = [self._make_evidence(
            executive_id=executive_id,
            source_type="linkedin",
            source_url=linkedin_url,
            headline=f"{exec_data.full_name} — PhantomBuster profile scrape",
            snippet=f"{exec_data.current_title} at {exec_data.current_company}",
            signal_type="network_edge",
            confidence=0.80,
            structured_fields=rows[0],
        )]
        return exec_data, evidence

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _run_and_fetch(
        self,
        agent_id: str,
        argument: dict | None = None,
        max_wait_secs: int = 120,
    ) -> list[dict]:
        headers = {"X-Phantombuster-Key": self.api_key}
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            # Launch phantom
            payload: dict = {"id": agent_id}
            if argument:
                payload["argument"] = argument
            launch = await client.post(f"{_BASE}/agents/launch", json=payload)
            launch.raise_for_status()
            container_id = launch.json().get("containerId")

            # Poll for completion
            waited = 0
            while waited < max_wait_secs:
                await asyncio.sleep(5)
                waited += 5
                status_resp = await client.get(
                    f"{_BASE}/containers/fetch-output",
                    params={"id": container_id},
                )
                status_resp.raise_for_status()
                data = status_resp.json()
                if data.get("status") in ("finished", "error"):
                    output = data.get("output") or []
                    return output if isinstance(output, list) else []

        return []


def _parse_output(rows: list[dict]) -> list[ExecutiveCreate]:
    return [_row_to_exec(r) for r in rows if r.get("fullName") or r.get("name")]


def _row_to_exec(row: dict) -> ExecutiveCreate:
    return ExecutiveCreate(
        full_name=row.get("fullName") or row.get("name") or "",
        current_title=row.get("title") or row.get("headline"),
        current_company=row.get("company") or row.get("companyName"),
        country=row.get("location") or row.get("country"),
        linkedin_url=row.get("linkedInUrl") or row.get("profileUrl"),
        emails=[row["email"]] if row.get("email") else [],
        lane="both",
    )
