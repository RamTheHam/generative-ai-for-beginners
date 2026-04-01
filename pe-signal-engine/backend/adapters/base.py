"""
Base adapter interface.  Every data source implements this contract.
The rest of the application never touches vendor-specific fields — only
the canonical ExecutiveCreate and EvidenceCreate schemas flow downstream.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from ..schemas import ExecutiveCreate, EvidenceCreate


class BaseAdapter(ABC):
    """
    Abstract base for all data-source adapters.

    Subclasses must implement:
        search_executives  — return a list of ExecutiveCreate
        enrich_executive   — return an updated ExecutiveCreate + list of EvidenceCreate
        provider_name      — string identifier matching source_provider in EvidenceCreate
    """

    def __init__(self, api_key: str | None = None, settings: dict[str, Any] | None = None):
        self.api_key = api_key
        self.settings = settings or {}

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Canonical provider name, e.g. 'apollo'."""
        ...

    @property
    def is_configured(self) -> bool:
        """True when the adapter has the credentials it needs to make live calls."""
        return bool(self.api_key)

    @abstractmethod
    async def search_executives(
        self,
        companies: list[str],
        sectors: list[str],
        countries: list[str],
        lane: str = "both",
    ) -> list[ExecutiveCreate]:
        """
        Discover executives matching the search parameters.
        Returns a list of ExecutiveCreate objects with whatever fields the
        provider can supply at discovery time.
        """
        ...

    @abstractmethod
    async def enrich_executive(
        self,
        executive_id: str,
        linkedin_url: str | None = None,
        full_name: str | None = None,
        company: str | None = None,
    ) -> tuple[ExecutiveCreate, list[EvidenceCreate]]:
        """
        Enrich a known executive with additional data from this provider.
        Returns an updated ExecutiveCreate (partial — caller merges) and any
        new evidence items.
        """
        ...

    def _make_evidence(self, executive_id: str, **kwargs) -> EvidenceCreate:
        """Helper to construct an EvidenceCreate stamped with this provider."""
        return EvidenceCreate(executive_id=executive_id, source_provider=self.provider_name, **kwargs)
