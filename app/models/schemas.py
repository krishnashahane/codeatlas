from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


MAX_GRAPH_NODES = 5_000
MAX_GRAPH_EDGES = 10_000


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=2048)
    label: str = Field(min_length=1, max_length=512)
    type: str = Field(min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=2048)
    target: str = Field(min_length=1, max_length=2048)
    type: str = Field(min_length=1, max_length=64)
    weight: int = Field(default=1, ge=1, le=1_000_000)


class Graph(BaseModel):
    nodes: list[Node] = Field(max_length=MAX_GRAPH_NODES)
    edges: list[Edge] = Field(max_length=MAX_GRAPH_EDGES)


class AnalysisResult(BaseModel):
    architecture_map: Graph
    dependency_graph: Graph
    knowledge_graph: Graph
    summary: dict[str, Any]


class UploadResponse(BaseModel):
    session_id: str


class GithubUrlRequest(BaseModel):
    github_url: HttpUrl

    @field_validator("github_url", mode="before")
    @classmethod
    def validate_url_length(cls, value):
        if len(str(value)) > 2048:
            raise ValueError("GitHub URL must be 2,048 characters or fewer.")
        return value
