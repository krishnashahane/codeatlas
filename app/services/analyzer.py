import os
from pathlib import Path

from app.models.schemas import AnalysisResult, MAX_GRAPH_EDGES, MAX_GRAPH_NODES
from app.services import js_parser, python_parser
from app.services.graph_builder import build_graphs


SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", "vendor", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "egg-info",
    ".idea", ".vscode", "coverage", ".nyc_output",
}
PYTHON_EXTS = {".py"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs"}

MAX_FILES = 5000
MAX_SOURCE_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 50 * 1024 * 1024
MAX_PATH_DEPTH = 30
MAX_ANALYZED_PATH_CHARS = 1024
MAX_WALK_ENTRIES = 25_000


def analyze(repo_path: Path) -> AnalysisResult:
    """Analyze a repository with explicit file, byte, and graph limits."""
    file_infos = []
    file_count = 0
    source_bytes = 0
    languages = set()
    truncated = False

    walk_limited = False
    for filepath in _walk_files(repo_path):
        if filepath is None:
            walk_limited = True
            break
        if file_count >= MAX_FILES:
            truncated = True
            break

        try:
            relative_path = filepath.relative_to(repo_path)
            file_size = filepath.stat(follow_symlinks=False).st_size
        except (OSError, ValueError):
            continue

        if len(relative_path.parts) > MAX_PATH_DEPTH or len(str(relative_path)) > MAX_ANALYZED_PATH_CHARS:
            truncated = True
            continue
        if file_size > MAX_SOURCE_FILE_BYTES:
            truncated = True
            continue
        if source_bytes + file_size > MAX_TOTAL_SOURCE_BYTES:
            truncated = True
            break

        extension = filepath.suffix.lower()
        try:
            if extension in PYTHON_EXTS:
                info = python_parser.parse_file(filepath, repo_path)
                languages.add("Python")
            elif extension in JS_EXTS:
                info = js_parser.parse_file(filepath, repo_path)
                languages.add("JavaScript/TypeScript")
            else:
                continue
        except (OSError, ValueError, RecursionError, UnicodeError):
            truncated = True
            continue

        file_infos.append(info)
        file_count += 1
        source_bytes += file_size

    architecture_map, dependency_graph, knowledge_graph = build_graphs(file_infos)

    total_classes = sum(len(info["classes"]) for info in file_infos)
    total_functions = sum(len(info["functions"]) for info in file_infos)
    total_variables = sum(len(info["variables"]) for info in file_infos)
    total_imports = sum(len(info["imports"]) for info in file_infos)

    graphs = (architecture_map, dependency_graph, knowledge_graph)
    graph_limited = any(
        len(graph.nodes) >= MAX_GRAPH_NODES or len(graph.edges) >= MAX_GRAPH_EDGES
        for graph in graphs
    )

    summary = {
        "file_count": file_count,
        "class_count": total_classes,
        "function_count": total_functions,
        "variable_count": total_variables,
        "import_count": total_imports,
        "languages": sorted(languages),
        "architecture_nodes": len(architecture_map.nodes),
        "dependency_nodes": len(dependency_graph.nodes),
        "knowledge_nodes": len(knowledge_graph.nodes),
        "truncated": truncated or graph_limited or walk_limited,
        "graph_limited": graph_limited,
        "walk_limited": walk_limited,
        "source_bytes": source_bytes,
    }

    return AnalysisResult(
        architecture_map=architecture_map,
        dependency_graph=dependency_graph,
        knowledge_graph=knowledge_graph,
        summary=summary,
    )


def _walk_files(root: Path):
    """Iteratively walk regular files without following symlinks."""
    try:
        root_resolved = root.resolve(strict=True)
        pending = [(root_resolved, 0)]
    except OSError:
        return

    visited_entries = 0
    while pending:
        directory, depth = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = []
                for entry in iterator:
                    visited_entries += 1
                    if visited_entries > MAX_WALK_ENTRIES:
                        yield None
                        return
                    entries.append(entry)
            entries.sort(key=lambda entry: entry.name, reverse=True)
        except OSError:
            continue

        for entry in entries:
            if entry.name in SKIP_DIRS:
                continue
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.startswith(".") or depth >= MAX_PATH_DEPTH:
                        continue
                    pending.append((Path(entry.path), depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    yield Path(entry.path)
            except OSError:
                continue
