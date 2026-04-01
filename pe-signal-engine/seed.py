"""
Seed script — populates the database with Nordic PE-relevant demo data.
Run once after first startup:
    python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DATABASE_URL", "sqlite:///./pe_signal.db")

from backend.database import SessionLocal, init_db
from backend.models import (
    Company, Executive, EvidenceItem, RelationshipEdge,
    SearchRun, SourceConfig, ScoreRule,
)
from backend.services.scoring import seed_default_rules
from datetime import date, datetime
from uuid import uuid4

def uid(): return str(uuid4())

def run():
    init_db()
    db = SessionLocal()
    seed_default_rules(db)

    # ── Source configs ─────────────────────────────────────────────────────────
    for provider, enabled in [
        ("apollo", False), ("scrupp", False), ("phantombuster", False),
        ("firecrawl", False), ("manual", True),
        ("boardex", False), ("execatlas", False), ("affinity", False),
    ]:
        if not db.query(SourceConfig).filter_by(provider=provider).first():
            db.add(SourceConfig(provider=provider, enabled=enabled))
    db.commit()

    # ── Demo search run ────────────────────────────────────────────────────────
    run_id = uid()
    demo_run = SearchRun(
        id=run_id,
        name="Nordics — Vertical SaaS + TICC Q2 2026",
        status="completed",
        lane="both",
        target_companies=["Visma", "Pagero", "AddSecure", "Azets", "Formpipe"],
        target_sectors=["Vertical SaaS", "Testing, Inspection & Certification"],
        target_countries=["Sweden", "Norway", "Denmark", "Finland"],
        source_config={"apollo": True, "firecrawl": True, "manual": True},
        score_weights={"transition": 0.30, "pe_fit": 0.35, "network": 0.20, "reachability": 0.15},
        stats={
            "stage": "complete",
            "companies_processed": 5,
            "executives_found": 8,
            "contact_coverage": 62,
            "evidence_items": 22,
        },
        completed_at=datetime.utcnow(),
    )
    db.add(demo_run)
    db.commit()

    # ── Companies ──────────────────────────────────────────────────────────────
    companies = [
        Company(id=uid(), name="Visma", domain="visma.com", country="Norway",
                sector="Vertical SaaS", hq_city="Oslo", employee_count=15000),
        Company(id=uid(), name="AddSecure", domain="addsecure.com", country="Sweden",
                sector="IT Services", hq_city="Gothenburg", employee_count=600),
        Company(id=uid(), name="Azets", domain="azets.com", country="Denmark",
                sector="Vertical SaaS", hq_city="Copenhagen", employee_count=7000),
        Company(id=uid(), name="Inspecta", domain="inspecta.com", country="Sweden",
                sector="Testing, Inspection & Certification", hq_city="Stockholm", employee_count=900),
        Company(id=uid(), name="Ramboll", domain="ramboll.com", country="Denmark",
                sector="Environmental & Compliance Services", hq_city="Copenhagen", employee_count=18000),
    ]
    for c in companies: db.add(c)
    db.commit()

    # ── Executives ─────────────────────────────────────────────────────────────
    execs_data = [
        dict(full_name="Lars Eriksson", current_title="CEO", current_company="Visma",
             country="Norway", lane="transition",
             sector_tags=["Vertical SaaS", "ERP", "SMB Software"],
             linkedin_url="https://linkedin.com/in/lars-eriksson-demo",
             emails=["l.eriksson@example.com"], phones=["+47 900 12 345"],
             transition_score=82, pe_fit_score=88, network_score=74, reachability_score=71, total_score=83,
             signal_flags=["recent_role_change", "contact_verified", "pe_m_and_a"],
             best_role_hypothesis="portfolio_ceo", dossier_status="drafted",
             availability_hypothesis="Stepped down as CEO after PE exit; currently in 6-month gardening period.",
             last_signal_date=date(2026, 2, 14)),
        dict(full_name="Maria Lindqvist", current_title="VP Operations", current_company="AddSecure",
             country="Sweden", lane="both",
             sector_tags=["IT Services", "IoT", "Critical Infrastructure"],
             linkedin_url="https://linkedin.com/in/maria-lindqvist-demo",
             emails=["m.lindqvist@example.com"],
             transition_score=61, pe_fit_score=79, network_score=66, reachability_score=58, total_score=70,
             signal_flags=["pe_integration", "event_speaker"],
             best_role_hypothesis="operating_partner",
             last_signal_date=date(2026, 1, 28)),
        dict(full_name="Søren Bak Nielsen", current_title="CFO", current_company="Azets",
             country="Denmark", lane="transition",
             sector_tags=["Vertical SaaS", "Accounting", "Finance SaaS"],
             linkedin_url="https://linkedin.com/in/soren-bak-demo",
             emails=["sbak@example.com"], phones=["+45 2312 4567"],
             transition_score=73, pe_fit_score=81, network_score=62, reachability_score=76, total_score=75,
             signal_flags=["recent_role_change", "contact_verified"],
             best_role_hypothesis="nex",
             last_signal_date=date(2026, 3, 3)),
        dict(full_name="Anna-Karin Holm", current_title="Managing Director, Nordics", current_company="Inspecta",
             country="Sweden", lane="successor",
             sector_tags=["TICC", "Regulatory Compliance", "Industrial Services"],
             linkedin_url="https://linkedin.com/in/anna-karin-holm-demo",
             transition_score=44, pe_fit_score=86, network_score=79, reachability_score=50, total_score=67,
             signal_flags=["event_speaker", "board_adjacency", "pe_turnaround"],
             best_role_hypothesis="portfolio_ceo",
             last_signal_date=date(2025, 11, 19)),
        dict(full_name="Jukka Mäkinen", current_title="CEO", current_company="Ramboll",
             country="Finland", lane="successor",
             sector_tags=["Environmental Services", "Infrastructure", "Compliance"],
             linkedin_url="https://linkedin.com/in/jukka-makinen-demo",
             transition_score=38, pe_fit_score=74, network_score=85, reachability_score=42, total_score=62,
             signal_flags=["event_speaker", "board_adjacency"],
             best_role_hypothesis="chair",
             last_signal_date=date(2026, 1, 5)),
        dict(full_name="Ingrid Vassdal", current_title="COO", current_company="Visma",
             country="Norway", lane="both",
             sector_tags=["Vertical SaaS", "Operational Excellence"],
             transition_score=56, pe_fit_score=77, network_score=69, reachability_score=63, total_score=68,
             signal_flags=["pe_integration", "contact_verified"],
             best_role_hypothesis="operating_partner",
             last_signal_date=date(2026, 2, 22)),
        dict(full_name="Erik Thorvald", current_title="Head of Product", current_company="Pagero",
             country="Sweden", lane="both",
             sector_tags=["Vertical SaaS", "e-Invoicing", "B2B Networks"],
             transition_score=49, pe_fit_score=68, network_score=54, reachability_score=57, total_score=59,
             signal_flags=["recent_role_change"],
             best_role_hypothesis="advisor",
             last_signal_date=date(2026, 1, 10)),
        dict(full_name="Camilla Rosen", current_title="Non-Executive Director",
             current_company="Multiple Boards", country="Denmark", lane="successor",
             sector_tags=["Healthcare SaaS", "Behavioural Health", "Digital Health"],
             linkedin_url="https://linkedin.com/in/camilla-rosen-demo",
             emails=["c.rosen@example.com"],
             transition_score=34, pe_fit_score=82, network_score=91, reachability_score=66, total_score=68,
             signal_flags=["board_adjacency", "event_speaker", "board_or_advisor_role"],
             best_role_hypothesis="chair",
             last_signal_date=date(2026, 3, 12)),
    ]

    exec_ids = []
    for d in execs_data:
        eid = uid()
        exec_ids.append(eid)
        db.add(Executive(
            id=eid, search_run_id=run_id,
            contact_confidence=0.7 if d.get("emails") else 0.1,
            source_mix=["apollo", "manual"] if d.get("emails") else ["manual"],
            vendor_ids={}, **d,
        ))
    db.commit()

    # ── Evidence items ─────────────────────────────────────────────────────────
    ev_seed = [
        (0, "role_change", "linkedin", "apollo", "Lars Eriksson exits as CEO of Visma following Vista Equity exit",
         "After seven years leading Visma through two PE cycles, Lars has stepped back from the CEO role and entered a transition period.", date(2026, 2, 14), 0.85),
        (0, "m_and_a", "press_release", "firecrawl", "Visma completes €2.4bn recapitalisation with KKR",
         "Transaction marks the third ownership change in ten years; integration workstream underway across 60+ product entities.", date(2026, 1, 20), 0.90),
        (1, "speaker", "conference", "firecrawl", "Maria Lindqvist — Keynote: Scaling IoT infrastructure across regulated markets",
         "Presented at Nordic Infrastructure Tech Summit 2026 on integrating IoT with critical-infrastructure compliance requirements.", date(2026, 1, 28), 0.80),
        (1, "integration", "company_news", "firecrawl", "AddSecure completes acquisition of SafeFleet Nordics",
         "Post-merger integration led by VP Operations; Maria Lindqvist credited with consolidating ERP and field-ops tooling within 90 days.", date(2025, 11, 10), 0.75),
        (2, "role_change", "linkedin", "apollo", "Søren Bak Nielsen joins Azets as CFO",
         "Azets appoints Søren Bak Nielsen as Group CFO following the departure of incumbent. Background includes Visma and EY Nordic M&A advisory.", date(2026, 3, 3), 0.85),
        (3, "speaker", "conference", "firecrawl", "Anna-Karin Holm — Panel: TIC sector consolidation in the Nordics",
         "Moderated at InspectionWorld Stockholm 2025; positioned as the leading voice on regulatory-driven M&A in the Nordic TIC space.", date(2025, 11, 19), 0.80),
        (3, "board_role", "board_page", "firecrawl", "Anna-Karin Holm appointed to board of Intertek Nordic Advisory Council",
         "Non-executive position announced Q4 2025; brings regulatory expertise to global TIC group.", date(2025, 10, 5), 0.70),
        (4, "speaker", "conference", "firecrawl", "Jukka Mäkinen — Opening keynote at Nordic Sustainability Leaders Forum 2026",
         "Addressed 400+ attendees on environmental compliance as a growth driver in infrastructure services.", date(2026, 1, 5), 0.80),
        (7, "board_role", "board_page", "firecrawl", "Camilla Rosen joins board of Mentimeter",
         "Camilla expands her board portfolio with a SaaS-native appointment; previous boards include Systematic A/S and PracticeFirst.", date(2026, 3, 1), 0.80),
        (7, "speaker", "conference", "firecrawl", "Camilla Rosen — Fireside: Scaling behavioural health platforms in the Nordics",
         "Delivered at Nordic Digital Health Forum, Copenhagen. Discussed margin dynamics and capacity constraints in outpatient specialty care.", date(2026, 3, 12), 0.85),
    ]

    ev_ids = []
    for exec_idx, sig, stype, provider, headline, snippet, dt, conf in ev_seed:
        eid = uid()
        ev_ids.append(eid)
        db.add(EvidenceItem(
            id=eid, executive_id=exec_ids[exec_idx],
            source_provider=provider, source_type=stype,
            headline=headline, snippet=snippet,
            date_observed=dt, signal_type=sig, confidence=conf,
            structured_fields={},
        ))
    db.commit()

    # ── Relationship edges ─────────────────────────────────────────────────────
    edges = [
        (0, "company", "Visma", "works_at", 0.9),
        (0, "investor", "KKR", "shares_event_with", 0.7),
        (0, "investor", "Vista Equity", "shares_event_with", 0.8),
        (1, "company", "AddSecure", "works_at", 0.9),
        (1, "event", "Nordic Infrastructure Tech Summit 2026", "speaks_at", 0.8),
        (2, "company", "Azets", "works_at", 0.9),
        (2, "company", "Visma", "worked_at", 0.8),
        (3, "board", "Intertek Nordic Advisory Council", "sits_on_board_of", 0.75),
        (3, "event", "InspectionWorld Stockholm 2025", "speaks_at", 0.8),
        (4, "company", "Ramboll", "works_at", 0.9),
        (4, "event", "Nordic Sustainability Leaders Forum 2026", "speaks_at", 0.8),
        (7, "board", "Mentimeter Board", "sits_on_board_of", 0.85),
        (7, "board", "Systematic A/S Board", "sits_on_board_of", 0.80),
        (7, "board", "PracticeFirst Board", "sits_on_board_of", 0.75),
        (7, "event", "Nordic Digital Health Forum 2026", "speaks_at", 0.85),
    ]

    for exec_idx, ttype, tname, etype, conf in edges:
        db.add(RelationshipEdge(
            source_id=exec_ids[exec_idx], source_type="executive",
            target_id=f"{ttype}::{tname.lower().replace(' ','_')}",
            target_type=ttype, target_name=tname,
            edge_type=etype, confidence=conf,
        ))
    db.commit()
    db.close()

    print(f"Seeded: 5 companies, {len(execs_data)} executives, {len(ev_seed)} evidence items, {len(edges)} edges.")
    print(f"Search run ID: {run_id}")


if __name__ == "__main__":
    run()
