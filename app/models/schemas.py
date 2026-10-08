from pydantic import BaseModel, Field, HttpUrl


class Node(BaseModel):
    id: str
    label: str
    type: str
    metadata: dict = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    type: str
    weight: int = 1


class Graph(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class AnalysisResult(BaseModel):
    architecture_map: Graph
    dependency_graph: Graph
    knowledge_graph: Graph
    summary: dict


class UploadResponse(BaseModel):
    session_id: str


class GithubUrlRequest(BaseModel):
    github_url: HttpUrl
