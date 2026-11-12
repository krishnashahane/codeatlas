import re
from pathlib import Path


MAX_EXTRACTED_ITEMS = 500
MAX_IDENTIFIER_CHARS = 256

IMPORT_FROM_RE = re.compile(
    r"""import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+(?:\s*,\s*\{[^}]*\})?)\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
REQUIRE_RE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
DYNAMIC_IMPORT_RE = re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)""")
CLASS_RE = re.compile(r"""(?:export\s+(?:default\s+)?)?class\s+(\w+)(?:\s+extends\s+(\w+))?""")
FUNC_RE = re.compile(r"""(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)""")
ARROW_RE = re.compile(
    r"""(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("""
)
CONST_RE = re.compile(r"""(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(\w+)\s*=""")
COMMENT_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)


def _empty_result(rel_path: str, module_path: str) -> dict:
    return {
        "file": rel_path,
        "module": module_path,
        "imports": [],
        "classes": [],
        "functions": [],
        "variables": [],
        "is_entry_point": False,
    }


def _find_bounded(pattern, source: str, limit: int = MAX_EXTRACTED_ITEMS):
    for index, match in enumerate(pattern.finditer(source)):
        if index >= limit:
            break
        yield match


def parse_file(filepath: Path, repo_root: Path) -> dict:
    """Extract a bounded set of JS/TS declarations from a source file."""
    rel_path = str(filepath.relative_to(repo_root))
    module_path = rel_path.replace("/", ".").removesuffix(".js").removesuffix(".ts")
    module_path = module_path.removesuffix(".jsx").removesuffix(".tsx")

    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        clean_source = COMMENT_RE.sub("", source)
    except (OSError, ValueError, RecursionError):
        return _empty_result(rel_path, module_path)

    imports = []
    for pattern, import_type in (
        (IMPORT_FROM_RE, "import"),
        (REQUIRE_RE, "require"),
        (DYNAMIC_IMPORT_RE, "dynamic_import"),
    ):
        for match in _find_bounded(pattern, clean_source):
            imports.append({
                "module": match.group(1)[:512],
                "name": "*",
                "type": import_type,
            })
            if len(imports) >= MAX_EXTRACTED_ITEMS:
                break
        if len(imports) >= MAX_EXTRACTED_ITEMS:
            break

    classes = []
    for match in _find_bounded(CLASS_RE, clean_source):
        name = match.group(1)[:MAX_IDENTIFIER_CHARS]
        parent = match.group(2)[:MAX_IDENTIFIER_CHARS] if match.group(2) else None
        classes.append({
            "name": name,
            "fqn": f"{module_path}.{name}",
            "bases": [parent] if parent else [],
            "methods": [],
            "decorators": [],
        })

    functions = []
    seen_names = set()
    for pattern in (FUNC_RE, ARROW_RE):
        for match in _find_bounded(pattern, clean_source):
            name = match.group(1)[:MAX_IDENTIFIER_CHARS]
            if name in seen_names:
                continue
            seen_names.add(name)
            functions.append({
                "name": name,
                "fqn": f"{module_path}.{name}",
                "params": [],
                "calls": [],
                "decorators": [],
                "is_async": "async" in match.group(0),
            })
            if len(functions) >= MAX_EXTRACTED_ITEMS:
                break
        if len(functions) >= MAX_EXTRACTED_ITEMS:
            break

    variables = []
    for match in _find_bounded(CONST_RE, clean_source):
        name = match.group(1)[:MAX_IDENTIFIER_CHARS]
        if name not in seen_names:
            variables.append({"name": name, "fqn": f"{module_path}.{name}"})
        if len(variables) >= MAX_EXTRACTED_ITEMS:
            break

    return {
        "file": rel_path,
        "module": module_path,
        "imports": imports,
        "classes": classes[:MAX_EXTRACTED_ITEMS],
        "functions": functions,
        "variables": variables,
        "is_entry_point": "index" in filepath.stem or "main" in filepath.stem,
    }
