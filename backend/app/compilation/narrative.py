"""Mode 1 — Anchored Narrative Generation (design doc §7.1).

Generates narrative text from verified structured facts, with source_refs
tracking. Used for non-golden drugs in Phase 2+ batch; golden entities
(Humira et al.) are hand-authored via data/curated/<drug>_narrative.yml.

Phase 1 Day 8: scaffolding only. First real usage is Phase 2+.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.compilation.claude_client import ClaudeClient


NARRATIVE_SYSTEM_PROMPT = """You are a biopharma knowledge compiler. Your job is to write
accurate, insightful narrative text based ONLY on the verified facts provided below.

Rules:
1. Every sentence must be traceable to at least one fact in the input.
2. Do NOT hallucinate dates, numbers, company names, or drug names.
3. Do NOT add information beyond what is provided — if something is missing, note the gap.
4. Write in a style that explains WHY things happened, not just WHAT happened.
5. Use specific numbers and dates from the input.
6. Write in {language} (en or zh).
"""

NARRATIVE_USER_PROMPT = """Based on the following verified facts about {entity_type} "{entity_name}",
write a {field_name} narrative.

VERIFIED FACTS:
{facts_json}

RELATED CONTEXT:
{context_json}

Write a {min_words}-{max_words} word narrative. Every claim must be supported by the facts above.
"""


@dataclass
class NarrativeResult:
    text: str
    source_refs: list[str]
    model: str
    generated_at: str


async def generate_narrative(
    client: ClaudeClient,
    *,
    entity_type: str,
    entity_name: str,
    field_name: str,
    facts: dict[str, Any],
    context: dict[str, Any] | None = None,
    language: str = "en",
    min_words: int = 100,
    max_words: int = 300,
) -> NarrativeResult:
    """Generate an anchored narrative. Returns text + source_refs."""
    system = NARRATIVE_SYSTEM_PROMPT.format(language=language)
    user = NARRATIVE_USER_PROMPT.format(
        entity_type=entity_type,
        entity_name=entity_name,
        field_name=field_name,
        facts_json=json.dumps(facts, indent=2, default=str),
        context_json=json.dumps(context, indent=2, default=str) if context else "None",
        min_words=min_words,
        max_words=max_words,
    )

    text, _usage = await client.messages_create(system=system, user=user)

    return NarrativeResult(
        text=text,
        source_refs=list(facts.keys()),
        model=client.model,
        generated_at=datetime.utcnow().isoformat(),
    )
