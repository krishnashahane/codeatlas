from pathlib import Path
from app.models.schemas import AnalysisResult
from app.services import python_parser, js_parser
from app.services.graph_builder import build_graphs

# Directories to skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", "vendor", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "egg-info",
    ".idea", ".vscode", "coverage", ".nyc_output",
}

# File extensions to parse
PYTHON_EXTS = {".py"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs"}

MAX_FILES = 5000
MAX_SOURCE_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 50 * 1024 * 1024
MAX_PATH_DEPTH = 30


def analyze(repo_path: Path) -> AnalysisResult:
    """Analyze a repository and return architecture, dependency, and knowledge graphs."""
    file_infos = []
    file_count = 0
    source_bytes = 0
    languages = set()
    truncated = False

    for filepath in _walk_files(repo_path):
        if file_count >= MAX_FILES:
            truncated = True
            break

        if len(filepath.relative_to(repo_path).parts) > MAX_PATH_DEPTH:
            continue

        try:
            file_size = filepath.stat().st_size
        except OSError:
            continue

        if file_size > MAX_SOURCE_FILE_BYTES:
            continue
        if source_bytes + file_size > MAX_TOTAL_SOURCE_BYTES:
            truncated = True
            break

        ext = filepath.suffix.lower()

        if ext in PYTHON_EXTS:
            info = python_parser.parse_file(filepath, repo_path)
            languages.add("Python")
        elif ext in JS_EXTS:
            info = js_parser.parse_file(filepath, repo_path)
            languages.add("JavaScript/TypeScript")
        else:
            continue

        file_infos.append(info)
        file_count += 1
        source_bytes += file_size

    arch_map, dep_graph, knowledge_graph = build_graphs(file_infos)

    # Compute summary stats
    total_classes = sum(len(info["classes"]) for info in file_infos)
    total_functions = sum(len(info["functions"]) for info in file_infos)
    total_variables = sum(len(info["variables"]) for info in file_infos)
    total_imports = sum(len(info["imports"]) for info in file_infos)

    summary = {
        "file_count": file_count,
        "class_count": total_classes,
        "function_count": total_functions,
        "variable_count": total_variables,
        "import_count": total_imports,
        "languages": sorted(languages),
        "architecture_nodes": len(arch_map.nodes),
        "dependency_nodes": len(dep_graph.nodes),
        "knowledge_nodes": len(knowledge_graph.nodes),
        "truncated": truncated,
        "source_bytes": source_bytes,
    }

    return AnalysisResult(
        architecture_map=arch_map,
        dependency_graph=dep_graph,
        knowledge_graph=knowledge_graph,
        summary=summary,
    )


def _walk_files(root: Path):
    """Walk only regular files inside the analysis root."""
    try:
        items = sorted(root.iterdir())
    except OSError:
        return
    root_resolved = root.resolve()
    for item in items:
        if item.name.startswith(".") and item.is_dir():
            continue
        if item.name in SKIP_DIRS:
            continue
        try:
            resolved = item.resolve(strict=False)
        except OSError:
            continue
        if resolved != root_resolved and root_resolved not in resolved.parents:
            continue
        if item.is_symlink():
            continue
        if item.is_dir():
            yield from _walk_files(item)
        elif item.is_file():
            yield item
