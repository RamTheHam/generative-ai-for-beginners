"""
BoardEx adapter — Phase 3 upgrade slot.

BoardEx provides deep board composition, career history, and
network-relationship data.  This adapter is a stub that will be
wired up when the BoardEx Data API becomes accessible.

Ref: https://boardex.com
"""
from __future__ import annotations
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter


class BoardExAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "boardex"

    async def search_executives(self, *args, **kwargs) -> list[ExecutiveCreate]:
        # TODO: implement POST /api/v1/people/search
        raise NotImplementedError("BoardEx adapter is a Phase 3 upgrade slot.")

    async def enrich_executive(self, *args, **kwargs) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        # TODO: implement GET /api/v1/people/{id}
        raise NotImplementedError("BoardEx adapter is a Phase 3 upgrade slot.")
