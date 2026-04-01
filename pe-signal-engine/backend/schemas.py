from __future__ import annotations
from datetime import datetime, date
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from uuid import uuid4


# ── Canonical Executive ────────────────────────────────────────────────────────

class ExecutiveSignals(BaseModel):
    transition_score: float = 0
    pe_fit_score: float = 0
    network_score: float = 0
    reachability_score: float = 0
    total_score: float = 0


class ExecutiveProfiles(BaseModel):
    linkedin_url: Optional[str] = None
    apollo_id: Optional[str] = None
    vendor_ids: dict[str, str] = Field(default_factory=dict)


class ExecutiveContacts(BaseModel):
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    contact_confidence: float = 0


class ExecutiveBase(BaseModel):
    full_name: str
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    country: Optional[str] = None
    sector_tags: list[str] = Field(default_factory=list)
    lane: str = "both"  # transition|successor|both
    linkedin_url: Optional[str] = None
    apollo_id: Optional[str] = None
    availability_hypothesis: Optional[str] = None
    best_role_hypothesis: Optional[str] = None  # portfolio_ceo|chair|operating_partner|nex|advisor


class ExecutiveCreate(ExecutiveBase):
    search_run_id: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)


class ExecutiveRead(ExecutiveBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    contact_confidence: float = 0
    transition_score: float = 0
    pe_fit_score: float = 0
    network_score: float = 0
    reachability_score: float = 0
    total_score: float = 0
    signal_flags: list[str] = Field(default_factory=list)
    dossier_status: str = "none"
    source_mix: list[str] = Field(default_factory=list)
    last_signal_date: Optional[date] = None
    search_run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExecutiveScoreOverride(BaseModel):
    transition_score: Optional[float] = None
    pe_fit_score: Optional[float] = None
    network_score: Optional[float] = None
    reachability_score: Optional[float] = None
    note: Optional[str] = None


# ── Canonical Evidence ─────────────────────────────────────────────────────────

class EvidenceBase(BaseModel):
    source_provider: str  # apollo|scrupp|phantombuster|firecrawl|manual|boardex|execatlas|affinity
    source_type: str      # linkedin|company_news|conference|association|podcast|board_page|press_release|crm|manual_note
    source_url: Optional[str] = None
    headline: Optional[str] = None
    snippet: str
    date_observed: Optional[date] = None
    signal_type: str      # role_change|speaker|board_role|advisor_role|m_and_a|integration|pricing|turnaround|international_scale|network_edge
    confidence: float = 0.0
    structured_fields: dict[str, Any] = Field(default_factory=dict)


class EvidenceCreate(EvidenceBase):
    executive_id: str


class EvidenceRead(EvidenceBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    executive_id: str
    created_at: datetime


# ── Relationship Edge ──────────────────────────────────────────────────────────

class EdgeCreate(BaseModel):
    source_id: str
    source_type: str = "executive"
    target_id: str
    target_type: str
    target_name: str
    edge_type: str  # works_at|worked_at|speaks_at|sits_on_board_of|advises|member_of|quoted_by|shares_event_with|shares_employer_with|introduced_by
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    evidence_id: Optional[str] = None
    confidence: float = 0.0


class EdgeRead(EdgeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ── Company ────────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None
    employee_count: Optional[int] = None
    hq_city: Optional[str] = None


class CompanyRead(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ── Search Run ─────────────────────────────────────────────────────────────────

class SearchRunCreate(BaseModel):
    name: str
    lane: str = "both"
    target_companies: list[str] = Field(default_factory=list)
    target_sectors: list[str] = Field(default_factory=list)
    target_countries: list[str] = Field(default_factory=list)
    source_config: dict[str, bool] = Field(default_factory=lambda: {
        "apollo": True,
        "scrupp": False,
        "phantombuster": False,
        "firecrawl": True,
        "manual": True,
    })
    score_weights: dict[str, float] = Field(default_factory=lambda: {
        "transition": 0.30,
        "pe_fit": 0.35,
        "network": 0.20,
        "reachability": 0.15,
    })
    template_name: Optional[str] = None


class SearchRunRead(SearchRunCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    stats: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


# ── Dossier ────────────────────────────────────────────────────────────────────

class DossierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    executive_id: str
    content_md: Optional[str] = None
    outreach_angle: Optional[str] = None
    talking_points: list[str] = Field(default_factory=list)
    status: str
    generated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


# ── Source Config ──────────────────────────────────────────────────────────────

class SourceConfigUpsert(BaseModel):
    provider: str
    enabled: bool = False
    api_key: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)


class SourceConfigRead(SourceConfigUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: str
    updated_at: datetime


# ── Score Rule ─────────────────────────────────────────────────────────────────

class ScoreRuleUpsert(BaseModel):
    name: str
    bucket: str
    condition_key: str
    delta: float
    enabled: bool = True
    description: Optional[str] = None


class ScoreRuleRead(ScoreRuleUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: str
    updated_at: datetime


# ── Outreach ───────────────────────────────────────────────────────────────────

class OutreachCreate(BaseModel):
    executive_id: str
    action_type: str
    notes: Optional[str] = None


class OutreachRead(OutreachCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_at: datetime
