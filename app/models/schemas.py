from pydantic import BaseModel


class Node(BaseModel):
    id: str
    label: str
    type: str  # "file", "directory", "class", "function", "variable", "package"
    metadata: dict = {}


class Edge(BaseModel):
    source: str
    target: str
    type: str  # "imports", "contains", "inherits", "calls"
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
    github_url: str
