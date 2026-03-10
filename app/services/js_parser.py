import re
from pathlib import Path

# Import patterns
IMPORT_FROM_RE = re.compile(
    r"""import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+(?:\s*,\s*\{[^}]*\})?)\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
REQUIRE_RE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
DYNAMIC_IMPORT_RE = re.compile(r"""import\(\s*['"]([^'"]+)['"]\s*\)""")

# Export/declaration patterns
CLASS_RE = re.compile(r"""(?:export\s+(?:default\s+)?)?class\s+(\w+)(?:\s+extends\s+(\w+))?""")
FUNC_RE = re.compile(r"""(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)""")
ARROW_RE = re.compile(
    r"""(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("""
)
CONST_RE = re.compile(r"""(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(\w+)\s*=""")

# Comment stripping
COMMENT_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
STRING_RE = re.compile(r"""(['"`])(?:(?!\1|\\).|\\.)*\1""", re.DOTALL)


def parse_file(filepath: Path, repo_root: Path) -> dict:
    """Parse a JS/TS file using regex and extract structural information."""
    rel_path = str(filepath.relative_to(repo_root))
    module_path = rel_path.replace("/", ".").removesuffix(".js").removesuffix(".ts")
    module_path = module_path.removesuffix(".jsx").removesuffix(".tsx")

    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return _empty_result(rel_path, module_path)

    # Strip comments to reduce false positives
    clean_source = COMMENT_RE.sub("", source)

    # Extract imports
    imports = []
    for match in IMPORT_FROM_RE.finditer(clean_source):
        imports.append({"module": match.group(1), "name": "*", "type": "import"})
    for match in REQUIRE_RE.finditer(clean_source):
        imports.append({"module": match.group(1), "name": "*", "type": "require"})
    for match in DYNAMIC_IMPORT_RE.finditer(clean_source):
        imports.append({"module": match.group(1), "name": "*", "type": "dynamic_import"})

    # Extract classes
    classes = []
    for match in CLASS_RE.finditer(clean_source):
        classes.append({
            "name": match.group(1),
            "fqn": f"{module_path}.{match.group(1)}",
            "bases": [match.group(2)] if match.group(2) else [],
            "methods": [],
            "decorators": [],
        })

    # Extract functions (named functions and arrow functions)
    functions = []
    seen_names = set()

    for match in FUNC_RE.finditer(clean_source):
        name = match.group(1)
        if name not in seen_names:
            seen_names.add(name)
            functions.append({
                "name": name,
                "fqn": f"{module_path}.{name}",
                "params": [],
                "calls": [],
                "decorators": [],
                "is_async": "async" in match.group(0),
            })

    for match in ARROW_RE.finditer(clean_source):
        name = match.group(1)
        if name not in seen_names:
            seen_names.add(name)
            functions.append({
                "name": name,
                "fqn": f"{module_path}.{name}",
                "params": [],
                "calls": [],
                "decorators": [],
                "is_async": "async" in match.group(0),
            })

    # Extract top-level variables (const/let/var not already captured as functions)
    variables = []
    for match in CONST_RE.finditer(clean_source):
        name = match.group(1)
        if name not in seen_names:
            variables.append({
                "name": name,
                "fqn": f"{module_path}.{name}",
            })

    is_entry_point = "index" in filepath.stem or "main" in filepath.stem

    return {
        "file": rel_path,
        "module": module_path,
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "variables": variables,
        "is_entry_point": is_entry_point,
    }


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
