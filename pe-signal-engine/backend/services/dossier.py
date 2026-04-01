"""
Dossier generation service.

Uses Claude (claude-sonnet-4-6) to generate a structured dossier for a
given executive, including:
  - Professional summary
  - PE fit assessment
  - Transition hypothesis
  - Suggested outreach angle
  - Talking points

Falls back to a template-filled dossier if the Anthropic API key is absent.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Executive, EvidenceItem, Dossier, RelationshipEdge
import os

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


async def generate_dossier(db: Session, executive: Executive) -> Dossier:
    evidence = (
        db.query(EvidenceItem)
        .filter(EvidenceItem.executive_id == executive.id)
        .order_by(EvidenceItem.date_observed.desc())
        .limit(20)
        .all()
    )
    edges = (
        db.query(RelationshipEdge)
        .filter(RelationshipEdge.source_id == executive.id)
        .limit(15)
        .all()
    )

    # Delete existing draft if present
    db.query(Dossier).filter(Dossier.executive_id == executive.id).delete()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if _ANTHROPIC_AVAILABLE and api_key:
        content_md, outreach, talking = await _generate_with_claude(
            executive, evidence, edges, api_key
        )
    else:
        content_md, outreach, talking = _generate_template(executive, evidence, edges)

    dossier = Dossier(
        executive_id=executive.id,
        content_md=content_md,
        outreach_angle=outreach,
        talking_points=talking,
        generated_at=datetime.utcnow(),
        status="draft",
    )
    db.add(dossier)
    executive.dossier_status = "drafted"
    db.add(executive)
    db.commit()
    db.refresh(dossier)
    return dossier


async def _generate_with_claude(
    executive: Executive,
    evidence: list[EvidenceItem],
    edges: list[RelationshipEdge],
    api_key: str,
) -> tuple[str, str, list[str]]:
    client = anthropic.Anthropic(api_key=api_key)

    evidence_text = "\n".join(
        f"- [{ev.signal_type}] {ev.headline or ''}: {ev.snippet[:200]}"
        for ev in evidence
    )
    edges_text = "\n".join(
        f"- {e.edge_type.replace('_', ' ')} → {e.target_name} ({e.target_type})"
        for e in edges
    )

    prompt = f"""You are a PE origination analyst. Write a concise executive dossier.

EXECUTIVE
Name: {executive.full_name}
Title: {executive.current_title or 'Unknown'}
Company: {executive.current_company or 'Unknown'}
Country: {executive.country or 'Unknown'}
Sector tags: {', '.join(executive.sector_tags or [])}
Lane: {executive.lane}
Scores: Transition {executive.transition_score} | PE Fit {executive.pe_fit_score} | Network {executive.network_score} | Reachability {executive.reachability_score}
Signal flags: {', '.join(executive.signal_flags or [])}
Best role hypothesis: {executive.best_role_hypothesis or 'Not set'}

EVIDENCE ({len(evidence)} items)
{evidence_text or 'None on record'}

RELATIONSHIPS ({len(edges)} edges)
{edges_text or 'None on record'}

Write the dossier in this exact markdown structure:

## Professional Summary
[2-3 sentences: who they are, what they've built, what they're known for]

## PE Fit Assessment
[2-3 sentences: why they matter for PE portfolio work, value creation angle]

## Transition Hypothesis
[1-2 sentences: why they might be open to a conversation now]

## Best Role Hypothesis
[1 sentence: what role at a portfolio company would fit them best]

## Network Notes
[1-2 sentences: notable board/investor connections or warm paths]

Then output ONLY the following JSON after the markdown (no other text):
{{
  "outreach_angle": "one sentence describing the best outreach hook",
  "talking_points": ["point 1", "point 2", "point 3"]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text

    # Split markdown from JSON
    import json, re
    json_match = re.search(r'\{[\s\S]+\}', raw)
    md_part = raw[:json_match.start()].strip() if json_match else raw.strip()
    outreach = ""
    talking: list[str] = []
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            outreach = parsed.get("outreach_angle", "")
            talking = parsed.get("talking_points", [])
        except Exception:
            pass

    return md_part, outreach, talking


def _generate_template(
    executive: Executive,
    evidence: list[EvidenceItem],
    edges: list[RelationshipEdge],
) -> tuple[str, str, list[str]]:
    flags_text = ", ".join(executive.signal_flags or []) or "none captured"
    recent = evidence[0] if evidence else None
    recent_text = f'Most recent signal: {recent.headline or recent.snippet[:80]}' if recent else "No signals on record."

    md = f"""## Professional Summary
{executive.full_name} is currently {executive.current_title or 'in an executive role'} at {executive.current_company or 'an undisclosed company'} ({executive.country or 'unknown location'}).

## PE Fit Assessment
Sector tags: {', '.join(executive.sector_tags or ['not tagged'])}. Signal flags include {flags_text}. PE fit score: {executive.pe_fit_score}/100.

## Transition Hypothesis
{executive.availability_hypothesis or 'No transition hypothesis on record. Review evidence and add a manual note.'}

## Best Role Hypothesis
{executive.best_role_hypothesis or 'Not yet assessed.'}

## Network Notes
{len(edges)} relationship edges recorded. {recent_text}
"""
    outreach = f"Reach out to {executive.full_name} via their most recent signal touchpoint."
    talking = [
        f"Their work in {(executive.sector_tags or ['this sector'])[0]}",
        f"Value creation opportunities in {executive.current_company or 'their current company'}",
        "Potential fit for portfolio operating roles",
    ]
    return md, outreach, talking
