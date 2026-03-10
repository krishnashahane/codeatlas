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


def analyze(repo_path: Path) -> AnalysisResult:
    """Analyze a repository and return architecture, dependency, and knowledge graphs."""
    file_infos = []
    file_count = 0
    languages = set()

    for filepath in _walk_files(repo_path):
        if file_count >= MAX_FILES:
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
    }

    return AnalysisResult(
        architecture_map=arch_map,
        dependency_graph=dep_graph,
        knowledge_graph=knowledge_graph,
        summary=summary,
    )


def _walk_files(root: Path):
    """Walk directory tree, skipping ignored directories."""
    for item in sorted(root.iterdir()):
        if item.name.startswith(".") and item.is_dir():
            continue
        if item.name in SKIP_DIRS:
            continue
        if item.is_dir():
            yield from _walk_files(item)
        elif item.is_file():
            yield item
