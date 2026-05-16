"""Mode 2 — Claim Extraction (design doc §7.1).

Extract structured Claims from article text using an LLM. For non-golden
drugs at scale in Phase 3+; Humira claims are hand-curated
(data/curated/humira_claims.yml) per §14.1 golden-entity doctrine.

Phase 2 P2-D2: scaffolding only. Prompt template + function signature.
Not invoked today.
"""

import json
from dataclasses import dataclass
from typing import Any

from app.compilation.claude_client import ClaudeClient


CLAIM_EXTRACTION_PROMPT = """You are extracting structured claims from a biopharma article.

For each distinct assertion in the article, extract:
1. statement: the specific claim (one sentence, precise)
2. claim_type: verified_fact | attributed_analysis | prediction | opinion | disputed
3. evidence_basis: what type of evidence supports this claim
4. entities_mentioned: list of drug names, target names, company names mentioned
5. confidence: high | medium | low

Rules:
- Separate facts from opinions. "AbbVie reported $20.7B in Humira revenue" is a verified_fact.
  "AbbVie's patent strategy was anticompetitive" is an attributed_analysis or opinion.
- If the author is making a prediction ("ADC market will reach $50B by 2030"), mark as prediction.
- If two sources disagree, mark as disputed.
- Do NOT extract claims that are just background/context.
- Extract 3-10 claims per article. Quality over quantity.

Article:
Title: {title}
Source: {source_name} ({source_type})
Date: {publish_date}
Content: {content}

Return JSON array of claims, nothing else.
"""


@dataclass
class ExtractedClaim:
    statement: str
    claim_type: str
    evidence_basis: str | None
    confidence: str | None
    entities_mentioned: list[str]


async def extract_claims_from_article(
    client: ClaudeClient,
    *,
    title: str,
    source_name: str,
    source_type: str,
    publish_date: str,
    content: str,
) -> list[ExtractedClaim]:
    """Invoke Mode 2 on a single article, return parsed ExtractedClaim list."""
    user = CLAIM_EXTRACTION_PROMPT.format(
        title=title,
        source_name=source_name,
        source_type=source_type,
        publish_date=publish_date,
        content=content,
    )

    text, _usage = await client.messages_create(
        system="You output only valid JSON.",
        user=user,
    )

    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: strip code fences if Claude added them
        stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        raw = json.loads(stripped)

    out: list[ExtractedClaim] = []
    for c in raw:
        out.append(
            ExtractedClaim(
                statement=c.get("statement", ""),
                claim_type=c.get("claim_type", "opinion"),
                evidence_basis=c.get("evidence_basis"),
                confidence=c.get("confidence"),
                entities_mentioned=c.get("entities_mentioned") or [],
            )
        )
    return out
