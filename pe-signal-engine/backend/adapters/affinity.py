"""
Affinity CRM adapter — Phase 3 upgrade slot.

Affinity provides relationship intelligence and deal sourcing for PE / VC.
When enabled, relationship edges and warm-path data will be imported from
the Affinity graph into the local relationship_edges table.

Ref: https://www.affinity.co / Affinity Sourcing product
"""
from __future__ import annotations
from ..schemas import ExecutiveCreate, EvidenceCreate
from .base import BaseAdapter


class AffinityAdapter(BaseAdapter):

    @property
    def provider_name(self) -> str:
        return "affinity"

    async def search_executives(self, *args, **kwargs) -> list[ExecutiveCreate]:
        raise NotImplementedError("Affinity adapter is a Phase 3 upgrade slot.")

    async def enrich_executive(self, *args, **kwargs) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        raise NotImplementedError("Affinity adapter is a Phase 3 upgrade slot.")
