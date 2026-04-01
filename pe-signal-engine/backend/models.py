from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import (
    Column, String, Float, Boolean, Text, DateTime, Date,
    ForeignKey, JSON, Integer
)
from .database import Base


def _uuid():
    return str(uuid4())


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    domain = Column(String)
    country = Column(String)
    sector = Column(String)
    description = Column(Text)
    employee_count = Column(Integer)
    hq_city = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Executive(Base):
    __tablename__ = "executives"

    id = Column(String, primary_key=True, default=_uuid)
    full_name = Column(String, nullable=False)
    current_title = Column(String)
    current_company = Column(String)
    current_company_id = Column(String, ForeignKey("companies.id"))
    country = Column(String)
    sector_tags = Column(JSON, default=list)
    lane = Column(String, default="both")  # transition | successor | both

    # Profiles
    linkedin_url = Column(String)
    apollo_id = Column(String)
    vendor_ids = Column(JSON, default=dict)

    # Contact
    emails = Column(JSON, default=list)
    phones = Column(JSON, default=list)
    contact_confidence = Column(Float, default=0.0)

    # Scores
    transition_score = Column(Float, default=0.0)
    pe_fit_score = Column(Float, default=0.0)
    network_score = Column(Float, default=0.0)
    reachability_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)

    signal_flags = Column(JSON, default=list)
    availability_hypothesis = Column(Text)
    best_role_hypothesis = Column(String)  # portfolio_ceo|chair|operating_partner|nex|advisor
    dossier_status = Column(String, default="none")  # none|drafted|reviewed|sent

    search_run_id = Column(String, ForeignKey("search_runs.id"))
    source_mix = Column(JSON, default=list)  # which adapters contributed data

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_signal_date = Column(Date)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(String, primary_key=True, default=_uuid)
    executive_id = Column(String, ForeignKey("executives.id"), nullable=False)

    source_provider = Column(String)  # apollo|scrupp|phantombuster|firecrawl|manual|boardex|execatlas|affinity
    source_type = Column(String)      # linkedin|company_news|conference|association|podcast|board_page|press_release|crm|manual_note
    source_url = Column(String)
    headline = Column(String)
    snippet = Column(Text)
    date_observed = Column(Date)
    signal_type = Column(String)      # role_change|speaker|board_role|advisor_role|m_and_a|integration|pricing|turnaround|international_scale|network_edge
    confidence = Column(Float, default=0.0)
    structured_fields = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class RelationshipEdge(Base):
    __tablename__ = "relationship_edges"

    id = Column(String, primary_key=True, default=_uuid)
    source_id = Column(String, nullable=False)       # executive_id
    source_type = Column(String, default="executive")
    target_id = Column(String, nullable=False)        # any node id or synthetic key
    target_type = Column(String)                      # executive|company|board|event|association|investor|advisor|podcast
    target_name = Column(String)
    edge_type = Column(String)                        # works_at|worked_at|speaks_at|sits_on_board_of|advises|member_of|quoted_by|shares_event_with|shares_employer_with|introduced_by
    date_from = Column(Date)
    date_to = Column(Date)
    evidence_id = Column(String, ForeignKey("evidence_items.id"))
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class SearchRun(Base):
    __tablename__ = "search_runs"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String)
    status = Column(String, default="pending")  # pending|running|completed|failed|paused
    lane = Column(String, default="both")

    target_companies = Column(JSON, default=list)
    target_sectors = Column(JSON, default=list)
    target_countries = Column(JSON, default=list)
    source_config = Column(JSON, default=dict)   # {apollo: true, scrupp: false, ...}
    score_weights = Column(JSON, default=dict)

    # Runtime stats
    stats = Column(JSON, default=lambda: {
        "companies_processed": 0,
        "executives_found": 0,
        "contact_coverage": 0,
        "evidence_items": 0,
        "stage": "idle",
    })

    template_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class Dossier(Base):
    __tablename__ = "dossiers"

    id = Column(String, primary_key=True, default=_uuid)
    executive_id = Column(String, ForeignKey("executives.id"), nullable=False)
    content_md = Column(Text)          # markdown body
    outreach_angle = Column(Text)
    talking_points = Column(JSON, default=list)
    generated_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    status = Column(String, default="draft")  # draft|reviewed|sent


class OutreachAction(Base):
    __tablename__ = "outreach_actions"

    id = Column(String, primary_key=True, default=_uuid)
    executive_id = Column(String, ForeignKey("executives.id"), nullable=False)
    action_type = Column(String)  # email|linkedin|intro|call
    notes = Column(Text)
    status = Column(String, default="planned")  # planned|sent|replied|dead
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceConfig(Base):
    __tablename__ = "source_configs"

    id = Column(String, primary_key=True, default=_uuid)
    provider = Column(String, unique=True, nullable=False)
    enabled = Column(Boolean, default=False)
    api_key = Column(String)
    settings = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScoreRule(Base):
    __tablename__ = "score_rules"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    bucket = Column(String)      # transition|pe_fit|network|reachability
    condition_key = Column(String)
    delta = Column(Float, default=0.0)
    enabled = Column(Boolean, default=True)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
