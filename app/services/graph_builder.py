from pathlib import PurePosixPath

from app.models.schemas import (
    Edge,
    Graph,
    MAX_GRAPH_EDGES,
    MAX_GRAPH_NODES,
    Node,
)


LAYER_KEYWORDS = {
    "API": ["api", "routes", "routers", "endpoints", "views", "controllers", "handlers"],
    "Business Logic": ["services", "logic", "core", "domain", "use_cases", "usecases"],
    "Data": ["models", "schemas", "entities", "database", "db", "migrations", "orm"],
    "Utility": ["utils", "helpers", "lib", "common", "shared", "tools"],
    "Config": ["config", "settings", "conf", "env"],
    "Tests": ["tests", "test", "spec", "specs", "__tests__"],
    "UI": ["components", "pages", "views", "templates", "layouts", "screens"],
}


def classify_layer(path: str) -> str:
    parts = set(PurePosixPath(path).parts)
    for layer, keywords in LAYER_KEYWORDS.items():
        if parts.intersection(keywords):
            return layer
    return "Core"


def build_graphs(file_infos: list[dict]) -> tuple[Graph, Graph, Graph]:
    return (
        _build_architecture_map(file_infos),
        _build_dependency_graph(file_infos),
        _build_knowledge_graph(file_infos),
    )


def _build_architecture_map(file_infos: list[dict]) -> Graph:
    nodes_map: dict[str, Node] = {}
    edges_set: set[tuple[str, str]] = set()

    for info in file_infos:
        path = PurePosixPath(info["file"])
        for index in range(len(path.parts) - 1):
            directory = str(PurePosixPath(*path.parts[: index + 1]))
            if directory in nodes_map:
                nodes_map[directory].metadata["file_count"] += 1
            elif len(nodes_map) < MAX_GRAPH_NODES:
                nodes_map[directory] = Node(
                    id=directory,
                    label=path.parts[index][:512],
                    type="directory",
                    metadata={
                        "layer": classify_layer(directory),
                        "file_count": 1,
                    },
                )

        if len(path.parts) == 1:
            if "." not in nodes_map and len(nodes_map) < MAX_GRAPH_NODES:
                nodes_map["."] = Node(
                    id=".",
                    label="root",
                    type="directory",
                    metadata={"layer": "Core", "file_count": 0},
                )
            if "." in nodes_map:
                nodes_map["."].metadata["file_count"] += 1

    file_to_dir = {}
    module_to_dir = {}
    for info in file_infos:
        path = PurePosixPath(info["file"])
        directory = str(path.parent) if len(path.parts) > 1 else "."
        file_to_dir[info["file"]] = directory
        module_to_dir[info["module"]] = directory

    for info in file_infos:
        source_dir = file_to_dir.get(info["file"], ".")
        if source_dir not in nodes_map:
            continue
        for imported in info["imports"]:
            target_dir = _resolve_import_to_dir(imported["module"], module_to_dir)
            if (
                target_dir
                and target_dir != source_dir
                and target_dir in nodes_map
                and len(edges_set) < MAX_GRAPH_EDGES
            ):
                edges_set.add((source_dir, target_dir))

        if info.get("is_entry_point"):
            nodes_map[source_dir].metadata["has_entry_point"] = True

    edges = [
        Edge(source=source, target=target, type="depends_on")
        for source, target in edges_set
    ]
    return Graph(nodes=list(nodes_map.values()), edges=edges)


def _build_dependency_graph(file_infos: list[dict]) -> Graph:
    nodes_map: dict[str, Node] = {}
    edges_map: dict[tuple[str, str], int] = {}
    external_packages: set[str] = set()
    module_to_file = {}

    for info in file_infos:
        if len(nodes_map) >= MAX_GRAPH_NODES:
            break
        module_to_file[info["module"]] = info["file"]
        nodes_map[info["file"]] = Node(
            id=info["file"],
            label=PurePosixPath(info["file"]).name[:512],
            type="file",
            metadata={
                "layer": classify_layer(info["file"]),
                "is_entry_point": info.get("is_entry_point", False),
                "module": info["module"][:1024],
            },
        )

    for info in file_infos:
        source_file = info["file"]
        if source_file not in nodes_map:
            continue
        for imported in info["imports"]:
            module = imported["module"]
            target_file = _resolve_import_to_file(module, module_to_file)
            if target_file:
                edge_key = (source_file, target_file)
            else:
                package = module.split(".")[0].split("/")[0][:256]
                if not package or package.startswith("."):
                    continue
                if len(external_packages) >= MAX_GRAPH_NODES:
                    continue
                external_packages.add(package)
                edge_key = (source_file, f"pkg:{package}")

            if edge_key in edges_map:
                edges_map[edge_key] += 1
            elif len(edges_map) < MAX_GRAPH_EDGES:
                edges_map[edge_key] = 1

    for package in sorted(external_packages):
        package_id = f"pkg:{package}"
        if len(nodes_map) >= MAX_GRAPH_NODES:
            break
        if package_id not in nodes_map:
            nodes_map[package_id] = Node(
                id=package_id,
                label=package,
                type="package",
                metadata={"external": True},
            )

    edges = [
        Edge(source=source, target=target, type="imports", weight=weight)
        for (source, target), weight in edges_map.items()
        if source in nodes_map and target in nodes_map
    ]
    return Graph(nodes=list(nodes_map.values()), edges=edges)


def _build_knowledge_graph(file_infos: list[dict]) -> Graph:
    nodes_map: dict[str, Node] = {}
    edge_keys: set[tuple[str, str, str]] = set()
    all_symbols: dict[str, str] = {}

    def add_node(node: Node) -> bool:
        if node.id in nodes_map:
            return True
        if len(nodes_map) >= MAX_GRAPH_NODES:
            return False
        nodes_map[node.id] = node
        return True

    def add_edge(source: str, target: str, edge_type: str) -> None:
        if len(edge_keys) >= MAX_GRAPH_EDGES:
            return
        key = (source, target, edge_type)
        if key not in edge_keys:
            edge_keys.add(key)

    for info in file_infos:
        file_id = f"file:{info['file']}"
        if not add_node(Node(
            id=file_id,
            label=PurePosixPath(info["file"]).name[:512],
            type="file",
            metadata={},
        )):
            break

        for cls in info["classes"]:
            fqn = cls["fqn"]
            if not add_node(Node(
                id=fqn,
                label=cls["name"][:512],
                type="class",
                metadata={
                    "bases": cls.get("bases", [])[:32],
                    "methods": [method["name"][:256] for method in cls.get("methods", [])[:32]],
                    "decorators": cls.get("decorators", [])[:32],
                },
            )):
                break
            all_symbols[cls["name"][:512]] = fqn
            add_edge(file_id, fqn, "defines")
            for base in cls.get("bases", [])[:32]:
                add_edge(fqn, f"ref:{base[:512]}", "inherits")
            for method in cls.get("methods", [])[:32]:
                for call in method.get("calls", [])[:32]:
                    add_edge(fqn, f"ref:{call[:512]}", "calls")
                if len(edge_keys) >= MAX_GRAPH_EDGES:
                    break
            if len(nodes_map) >= MAX_GRAPH_NODES or len(edge_keys) >= MAX_GRAPH_EDGES:
                break
        if len(nodes_map) >= MAX_GRAPH_NODES or len(edge_keys) >= MAX_GRAPH_EDGES:
            break

        for function in info["functions"]:
            fqn = function["fqn"]
            if not add_node(Node(
                id=fqn,
                label=function["name"][:512],
                type="function",
                metadata={
                    "params": function.get("params", [])[:32],
                    "decorators": function.get("decorators", [])[:32],
                    "is_async": function.get("is_async", False),
                },
            )):
                break
            all_symbols[function["name"][:512]] = fqn
            add_edge(file_id, fqn, "defines")
            for call in function.get("calls", [])[:32]:
                add_edge(fqn, f"ref:{call[:512]}", "calls")
            if len(nodes_map) >= MAX_GRAPH_NODES or len(edge_keys) >= MAX_GRAPH_EDGES:
                break
        if len(nodes_map) >= MAX_GRAPH_NODES or len(edge_keys) >= MAX_GRAPH_EDGES:
            break

        for variable in info["variables"]:
            fqn = variable["fqn"]
            if not add_node(Node(
                id=fqn,
                label=variable["name"][:512],
                type="variable",
                metadata={},
            )):
                break
            all_symbols[variable["name"][:512]] = fqn
            add_edge(file_id, fqn, "defines")
            if len(nodes_map) >= MAX_GRAPH_NODES or len(edge_keys) >= MAX_GRAPH_EDGES:
                break
        if len(nodes_map) >= MAX_GRAPH_NODES or len(edge_keys) >= MAX_GRAPH_EDGES:
            break

    resolved_edges = []
    for source, target, edge_type in sorted(edge_keys):
        if target.startswith("ref:"):
            resolved_target = all_symbols.get(target[4:])
            if resolved_target is None:
                continue
            target = resolved_target
        if source in nodes_map and target in nodes_map:
            resolved_edges.append(Edge(source=source, target=target, type=edge_type))

    return Graph(nodes=list(nodes_map.values()), edges=resolved_edges)


def _resolve_import_to_file(module: str, module_to_file: dict) -> str | None:
    if module in module_to_file:
        return module_to_file[module]
    parts = module.split(".")
    for index in range(len(parts), 0, -1):
        candidate = ".".join(parts[:index])
        if candidate in module_to_file:
            return module_to_file[candidate]
    return None


def _resolve_import_to_dir(module: str, module_to_dir: dict) -> str | None:
    if module in module_to_dir:
        return module_to_dir[module]
    parts = module.split(".")
    for index in range(len(parts), 0, -1):
        candidate = ".".join(parts[:index])
        if candidate in module_to_dir:
            return module_to_dir[candidate]
    return None
