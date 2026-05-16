"""Graph neighbor response schema (ADR-0002 view)."""

from uuid import UUID

from pydantic import BaseModel


class GraphNode(BaseModel):
    type: str
    id: UUID
    label: str | None
    link: str
    distance: int


class GraphEdge(BaseModel):
    source_type: str
    source_id: UUID
    target_type: str
    target_id: UUID
    relationship_type: str


class GraphData(BaseModel):
    source: GraphNode
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphMeta(BaseModel):
    entity_type: str  # always "graph"
    root_type: str
    depth: int
    node_count: int
    edge_count: int


class GraphEnvelope(BaseModel):
    data: GraphData
    meta: GraphMeta
