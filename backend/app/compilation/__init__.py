"""Knowledge compilation engine — design doc §7.

Modes:
  1. Anchored Narrative Generation (narrative.py) — LLM output anchored
     to structured facts. For non-golden drugs in Phase 2+ batch.
  2. Claim Extraction (claims.py — future) — structured assertions from
     curated articles.
  3. Lesson Mining (lessons.py — future) — transferable insights across
     cases, human-approved.

Golden entities (Humira, Keytruda, Ozempic) do NOT go through Mode 1;
they're hand-authored in data/curated/<drug>_narrative.yml per
design doc §14.1 "manually compiled and verified to the highest
quality standard."
"""
