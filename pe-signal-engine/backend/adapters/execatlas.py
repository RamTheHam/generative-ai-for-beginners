"""
ExecAtlas adapter — Phase 3 upgrade slot.

ExecAtlas provides executive data and relationship intelligence for GTM teams.

Ref: https://www.execatlas.com
"""
from __future__ import annotations
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter


class ExecAtlasAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "execatlas"

    async def search_executives(self, *args, **kwargs) -> list[ExecutiveCreate]:
        raise NotImplementedError("ExecAtlas adapter is a Phase 3 upgrade slot.")

    async def enrich_executive(self, *args, **kwargs) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        raise NotImplementedError("ExecAtlas adapter is a Phase 3 upgrade slot.")
