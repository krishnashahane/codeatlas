from pathlib import PurePosixPath
from app.models.schemas import Node, Edge, Graph

# Heuristic layer classification based on directory names
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
        if parts & set(keywords):
            return layer
    return "Core"


def build_graphs(file_infos: list[dict]) -> tuple[Graph, Graph, Graph]:
    """Build architecture map, dependency graph, and knowledge graph from parsed file info."""
    arch_map = _build_architecture_map(file_infos)
    dep_graph = _build_dependency_graph(file_infos)
    knowledge_graph = _build_knowledge_graph(file_infos)
    return arch_map, dep_graph, knowledge_graph


def _build_architecture_map(file_infos: list[dict]) -> Graph:
    """Build a graph of directories (modules) and their relationships."""
    nodes_map: dict[str, Node] = {}
    edges_set: set[tuple[str, str]] = set()

    # Collect all directories
    for info in file_infos:
        path = PurePosixPath(info["file"])
        # Add each directory level
        for i in range(len(path.parts) - 1):
            dir_path = str(PurePosixPath(*path.parts[: i + 1]))
            if dir_path not in nodes_map:
                layer = classify_layer(dir_path)
                nodes_map[dir_path] = Node(
                    id=dir_path,
                    label=path.parts[i],
                    type="directory",
                    metadata={"layer": layer, "file_count": 0},
                )
            nodes_map[dir_path].metadata["file_count"] += 1

    # Add root if files exist at top level
    for info in file_infos:
        path = PurePosixPath(info["file"])
        if len(path.parts) == 1:
            if "." not in nodes_map:
                nodes_map["."] = Node(
                    id=".",
                    label="root",
                    type="directory",
                    metadata={"layer": "Core", "file_count": 0},
                )
            nodes_map["."].metadata["file_count"] += 1

    # Build edges from imports between directories
    file_to_dir = {}
    for info in file_infos:
        path = PurePosixPath(info["file"])
        dir_path = str(path.parent) if len(path.parts) > 1 else "."
        file_to_dir[info["file"]] = dir_path

    # Map module names to directories
    module_to_dir = {}
    for info in file_infos:
        module_to_dir[info["module"]] = file_to_dir.get(info["file"], ".")

    for info in file_infos:
        src_dir = file_to_dir.get(info["file"], ".")
        for imp in info["imports"]:
            imp_module = imp["module"]
            # Try to find the target directory
            target_dir = _resolve_import_to_dir(imp_module, module_to_dir)
            if target_dir and target_dir != src_dir and target_dir in nodes_map:
                edge_key = (src_dir, target_dir)
                edges_set.add(edge_key)

    # Mark entry points
    for info in file_infos:
        if info.get("is_entry_point"):
            dir_path = file_to_dir.get(info["file"], ".")
            if dir_path in nodes_map:
                nodes_map[dir_path].metadata["has_entry_point"] = True

    edges = [
        Edge(source=src, target=tgt, type="depends_on")
        for src, tgt in edges_set
    ]

    return Graph(nodes=list(nodes_map.values()), edges=edges)


def _build_dependency_graph(file_infos: list[dict]) -> Graph:
    """Build a graph of file-to-file and file-to-package dependencies."""
    nodes_map: dict[str, Node] = {}
    edges_map: dict[tuple[str, str], int] = {}
    external_packages: set[str] = set()

    # Build module-to-file mapping
    module_to_file = {}
    for info in file_infos:
        module_to_file[info["module"]] = info["file"]

    # Add file nodes
    for info in file_infos:
        layer = classify_layer(info["file"])
        nodes_map[info["file"]] = Node(
            id=info["file"],
            label=PurePosixPath(info["file"]).name,
            type="file",
            metadata={
                "layer": layer,
                "is_entry_point": info.get("is_entry_point", False),
                "module": info["module"],
            },
        )

    # Build edges from imports
    for info in file_infos:
        src_file = info["file"]
        for imp in info["imports"]:
            imp_module = imp["module"]
            target_file = _resolve_import_to_file(imp_module, module_to_file)

            if target_file:
                edge_key = (src_file, target_file)
                edges_map[edge_key] = edges_map.get(edge_key, 0) + 1
            else:
                # External package
                pkg_name = imp_module.split(".")[0].split("/")[0]
                if pkg_name and not pkg_name.startswith("."):
                    external_packages.add(pkg_name)
                    edge_key = (src_file, f"pkg:{pkg_name}")
                    edges_map[edge_key] = edges_map.get(edge_key, 0) + 1

    # Add external package nodes
    for pkg in external_packages:
        nodes_map[f"pkg:{pkg}"] = Node(
            id=f"pkg:{pkg}",
            label=pkg,
            type="package",
            metadata={"external": True},
        )

    edges = [
        Edge(source=src, target=tgt, type="imports", weight=w)
        for (src, tgt), w in edges_map.items()
    ]

    return Graph(nodes=list(nodes_map.values()), edges=edges)


def _build_knowledge_graph(file_infos: list[dict]) -> Graph:
    """Build a graph of code symbols and their relationships."""
    nodes_map: dict[str, Node] = {}
    edges: list[Edge] = []
    all_symbols: dict[str, str] = {}  # name -> fqn

    for info in file_infos:
        # Add file node
        file_id = f"file:{info['file']}"
        nodes_map[file_id] = Node(
            id=file_id,
            label=PurePosixPath(info["file"]).name,
            type="file",
            metadata={},
        )

        # Add class nodes
        for cls in info["classes"]:
            fqn = cls["fqn"]
            nodes_map[fqn] = Node(
                id=fqn,
                label=cls["name"],
                type="class",
                metadata={
                    "bases": cls.get("bases", []),
                    "methods": [m["name"] for m in cls.get("methods", [])],
                    "decorators": cls.get("decorators", []),
                },
            )
            all_symbols[cls["name"]] = fqn
            edges.append(Edge(source=file_id, target=fqn, type="defines"))

            # Add inheritance edges
            for base in cls.get("bases", []):
                edges.append(Edge(source=fqn, target=f"ref:{base}", type="inherits"))

            # Add method call edges
            for method in cls.get("methods", []):
                for call in method.get("calls", []):
                    edges.append(Edge(source=fqn, target=f"ref:{call}", type="calls"))

        # Add function nodes
        for func in info["functions"]:
            fqn = func["fqn"]
            nodes_map[fqn] = Node(
                id=fqn,
                label=func["name"],
                type="function",
                metadata={
                    "params": func.get("params", []),
                    "decorators": func.get("decorators", []),
                    "is_async": func.get("is_async", False),
                },
            )
            all_symbols[func["name"]] = fqn
            edges.append(Edge(source=file_id, target=fqn, type="defines"))

            # Add call edges
            for call in func.get("calls", []):
                edges.append(Edge(source=fqn, target=f"ref:{call}", type="calls"))

        # Add variable nodes
        for var in info["variables"]:
            fqn = var["fqn"]
            nodes_map[fqn] = Node(
                id=fqn,
                label=var["name"],
                type="variable",
                metadata={},
            )
            all_symbols[var["name"]] = fqn
            edges.append(Edge(source=file_id, target=fqn, type="defines"))

    # Resolve reference edges to actual symbols where possible
    resolved_edges = []
    for edge in edges:
        if edge.target.startswith("ref:"):
            ref_name = edge.target[4:]
            if ref_name in all_symbols:
                edge = Edge(source=edge.source, target=all_symbols[ref_name], type=edge.type)
                resolved_edges.append(edge)
            # Drop unresolved refs to keep graph clean
        else:
            resolved_edges.append(edge)

    return Graph(nodes=list(nodes_map.values()), edges=resolved_edges)


def _resolve_import_to_file(module: str, module_to_file: dict) -> str | None:
    """Try to resolve an import module path to a file."""
    # Direct match
    if module in module_to_file:
        return module_to_file[module]
    # Try parent module (from foo.bar import baz -> look for foo.bar)
    parts = module.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in module_to_file:
            return module_to_file[candidate]
    return None


def _resolve_import_to_dir(module: str, module_to_dir: dict) -> str | None:
    """Try to resolve an import module path to a directory."""
    if module in module_to_dir:
        return module_to_dir[module]
    parts = module.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in module_to_dir:
            return module_to_dir[candidate]
    return None
