"""BioGraph curator dashboard — Streamlit internal ops tool.

Runs against the same Postgres the FastAPI app uses. Direct
SQLAlchemy-model reads (no HTTP layer, no CORS, curator is trusted).

Purpose: make curator workflow fast enough that content expansion
(more T1 landscapes, auto-narrative QA, merge-conflict triage) stops
being the bottleneck.

Launch:
    cd backend && source .venv/bin/activate
    streamlit run dashboard.py --server.port 8501
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Claim,
    ClinicalTrial,
    Company,
    Drug,
    Event,
    Lesson,
    MergeConflict,
    RegulatoryDecision,
    Target,
)
from app.services.landscape_engine import list_curated_slugs, load_landscape

st.set_page_config(
    page_title="BioGraph · Curator",
    page_icon="🧬",
    layout="wide",
)


# ── Shared state ─────────────────────────────────────────────────────

@st.cache_resource
def engine():
    return create_engine(settings.database_url_sync, pool_pre_ping=True)


def session() -> Session:
    return Session(engine())


# ── Header ───────────────────────────────────────────────────────────

st.title("BioGraph · Curator dashboard")
st.caption(
    f"Internal ops tool · DB: {settings.database_url_sync.split('@')[-1]} · "
    f"updated {datetime.utcnow():%Y-%m-%d %H:%M} UTC"
)

tab_drugs, tab_landscape, tab_conflicts, tab_summary = st.tabs(
    ["Drug browser", "Landscape coverage", "Merge conflicts", "Summary"]
)


# ── Tab 1: Drug browser + completeness ───────────────────────────────

with tab_drugs:
    st.header("Drugs")
    st.caption(
        "Pick a next golden-entity or landscape candidate. Completeness "
        "flags what's missing."
    )

    with session() as s:
        rows = s.execute(
            select(
                Drug.id,
                Drug.chembl_id,
                Drug.generic_name,
                Drug.modality,
                Drug.status,
                Drug.max_phase,
                Drug.revenue_peak_usd,
                Drug.discovery_narrative,
                func.coalesce(
                    select(func.count())
                    .where(ClinicalTrial.drug_id == Drug.id)
                    .scalar_subquery(),
                    0,
                ).label("trials"),
                func.coalesce(
                    select(func.count())
                    .where(RegulatoryDecision.drug_id == Drug.id)
                    .scalar_subquery(),
                    0,
                ).label("regulatory"),
            )
        ).all()

    df = pd.DataFrame(
        [
            {
                "id": str(r.id),
                "chembl_id": r.chembl_id,
                "generic_name": r.generic_name,
                "modality": r.modality,
                "status": r.status,
                "max_phase": r.max_phase,
                "peak_revenue_usd": r.revenue_peak_usd,
                "narrative?": bool(r.discovery_narrative),
                "trials": r.trials,
                "regulatory": r.regulatory,
            }
            for r in rows
        ]
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        modalities = sorted({m for m in df["modality"].dropna().unique()})
        modality_filter = st.multiselect("Modality", modalities, default=[])
    with c2:
        min_trials = st.number_input("Min trials", min_value=0, value=0, step=10)
    with c3:
        only_with_narrative = st.checkbox("Has narrative", value=False)
    with c4:
        only_with_revenue = st.checkbox("Has revenue", value=False)

    view = df.copy()
    if modality_filter:
        view = view[view["modality"].isin(modality_filter)]
    if min_trials > 0:
        view = view[view["trials"] >= min_trials]
    if only_with_narrative:
        view = view[view["narrative?"]]
    if only_with_revenue:
        view = view[view["peak_revenue_usd"].notna()]

    st.write(f"{len(view)} of {len(df)} drugs match")
    st.dataframe(
        view.sort_values(["peak_revenue_usd", "trials"], ascending=[False, False]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "peak_revenue_usd": st.column_config.NumberColumn(
                "Peak rev USD", format="$%d"
            ),
        },
    )

    st.divider()
    st.subheader("Drill-down")
    drill_id = st.text_input(
        "Drug UUID",
        help="Paste a row's id to see its full curation state",
    )
    if drill_id:
        with session() as s:
            drug = s.get(Drug, drill_id)
        if drug is None:
            st.error("Drug not found")
        else:
            cols = st.columns(5)
            cols[0].metric("Targets", len(drug.targets))
            cols[1].metric("Indications", len(drug.indications))
            cols[2].metric("Trials", len(drug.trials))
            cols[3].metric("Reg decisions", len(drug.regulatory_decisions))
            cols[4].metric("Patents", len(drug.patents))

            cols = st.columns(5)
            cols[0].metric("Events", len(drug.events))
            cols[1].metric("Claims", len(drug.claims))
            cols[2].metric("Lessons", len(drug.lessons))
            cols[3].metric("Deals", len(drug.deals))
            cols[4].metric("Biosimilars", len(drug.biosimilars))

            with st.expander("Discovery narrative"):
                if drug.discovery_narrative:
                    st.write(drug.discovery_narrative)
                else:
                    st.warning("No discovery_narrative curated yet")
            with st.expander("Mechanism of action"):
                if drug.mechanism_of_action:
                    st.write(drug.mechanism_of_action)
                else:
                    st.warning("No mechanism_of_action curated yet")


# ── Tab 2: Landscape coverage ────────────────────────────────────────

with tab_landscape:
    st.header("T1 landscape coverage")
    st.caption(
        f"Currently curated: {len(list_curated_slugs())} landscapes."
    )

    priority = [
        ("nash", "NASH/MASH"),
        ("glp1-obesity", "GLP-1 / Obesity"),
        ("pd1-pdl1", "PD-1/PD-L1 (Immuno-oncology)"),
        ("adc", "ADC (Antibody-Drug Conjugates)"),
        ("car-t", "CAR-T / Cell Therapy"),
        ("egfr-nsclc", "EGFR NSCLC"),
        ("alzheimers", "Alzheimer's Disease"),
        ("her2", "HER2 (Breast Cancer + Beyond)"),
        ("crispr", "CRISPR / Gene Therapy"),
        ("mrna-therapeutics", "mRNA Therapeutics"),
        ("jak-inhibitors", "JAK inhibitors"),
        ("bispecifics", "Bispecific Antibodies"),
        ("kras", "KRAS"),
        ("pcsk9", "PCSK9"),
        ("obesity-beyond-glp1", "Obesity beyond GLP-1"),
    ]

    shipped = set(list_curated_slugs())
    coverage_rows = []
    for slug, label in priority:
        is_shipped = slug in shipped
        completeness = None
        if is_shipped:
            doc = load_landscape(slug) or {}
            # Rough curator-eye completeness — same score the backend computes.
            checks = [
                bool(doc.get("disease_overview")) and len(doc.get("disease_overview", "")) > 200,
                bool(doc.get("mechanism_map")),
                bool(doc.get("pipeline")),
                bool(doc.get("companies")) and len(doc.get("companies") or []) >= 3,
                bool(doc.get("key_trials")),
                bool(doc.get("scientific_bottlenecks")) and len(doc.get("scientific_bottlenecks") or []) >= 3,
                bool(doc.get("market_dynamics")),
                bool(doc.get("regulatory_context")),
                bool(doc.get("hot_targets")) and len(doc.get("hot_targets") or []) >= 4,
                bool(doc.get("literature")) and len(doc.get("literature") or []) >= 3,
            ]
            completeness = round(sum(checks) / len(checks), 2)
        coverage_rows.append(
            {
                "slug": slug,
                "name": label,
                "shipped": is_shipped,
                "completeness": completeness,
            }
        )
    st.dataframe(
        pd.DataFrame(coverage_rows),
        use_container_width=True,
        hide_index=True,
    )

    st.info("Coverage table is generated from curated landscape YAML files.")


# ── Tab 3: Merge conflicts inspector ─────────────────────────────────

with tab_conflicts:
    st.header("Merge conflicts — audit trail")
    st.caption(
        "Each row is a field where two sources disagreed. "
        "Review to confirm source-precedence decisions."
    )

    limit = st.slider("Rows to load", min_value=10, max_value=500, value=50, step=10)

    with session() as s:
        rows = s.execute(
            select(MergeConflict)
            .order_by(MergeConflict.detected_at.desc())
            .limit(limit)
        ).scalars().all()

    if not rows:
        st.info("No merge conflicts recorded yet.")
    else:
        df = pd.DataFrame(
            [
                {
                    "detected_at": r.detected_at,
                    "entity_type": r.entity_type,
                    "entity_id": str(r.entity_id)[:8],
                    "field": r.field_name,
                    "category": r.field_category,
                    "source_a": r.source_a,
                    "source_b": r.source_b,
                    "resolution": r.resolution_reason,
                    "value_a": (str(r.value_a) or "")[:80],
                    "value_b": (str(r.value_b) or "")[:80],
                }
                for r in rows
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── Tab 4: Summary ───────────────────────────────────────────────────

with tab_summary:
    st.header("System snapshot")

    with session() as s:
        counts = {
            "Drugs": s.scalar(select(func.count()).select_from(Drug)),
            "Targets": s.scalar(select(func.count()).select_from(Target)),
            "Clinical trials": s.scalar(select(func.count()).select_from(ClinicalTrial)),
            "Regulatory decisions": s.scalar(
                select(func.count()).select_from(RegulatoryDecision)
            ),
            "Companies": s.scalar(select(func.count()).select_from(Company)),
            "Events": s.scalar(select(func.count()).select_from(Event)),
            "Claims": s.scalar(select(func.count()).select_from(Claim)),
            "Lessons": s.scalar(select(func.count()).select_from(Lesson)),
        }

    c = st.columns(4)
    for i, (k, v) in enumerate(counts.items()):
        c[i % 4].metric(k, f"{v:,}")

    st.divider()

    with session() as s:
        # Drugs that would benefit from curation: high trial count + no narrative
        high_trial_no_narr = s.execute(
            select(Drug.generic_name, Drug.chembl_id)
            .where(Drug.discovery_narrative.is_(None))
            .order_by(
                select(func.count())
                .where(ClinicalTrial.drug_id == Drug.id)
                .scalar_subquery()
                .desc()
            )
            .limit(10)
        ).all()

    st.subheader("Curation backlog — top drugs missing a narrative")
    st.dataframe(
        pd.DataFrame(
            [{"generic_name": r[0], "chembl_id": r[1]} for r in high_trial_no_narr]
        ),
        use_container_width=True,
        hide_index=True,
    )
