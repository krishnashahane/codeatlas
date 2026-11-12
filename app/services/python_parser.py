import ast
from pathlib import Path


MAX_AST_NODES = 100_000
MAX_SYMBOL_REFERENCES = 500
MAX_IDENTIFIER_CHARS = 256


def _safe_name(value: str) -> str:
    return value[:MAX_IDENTIFIER_CHARS]


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


def _ast_within_limit(root: ast.AST) -> bool:
    pending = [root]
    count = 0
    while pending:
        node = pending.pop()
        count += 1
        if count > MAX_AST_NODES:
            return False
        pending.extend(ast.iter_child_nodes(node))
    return True


def parse_file(filepath: Path, repo_root: Path) -> dict:
    """Parse Python syntax with bounds on AST traversal and extracted references."""
    rel_path = str(filepath.relative_to(repo_root))
    module_path = rel_path.replace("/", ".").removesuffix(".py")

    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
        if not _ast_within_limit(tree):
            return _empty_result(rel_path, module_path)
    except (OSError, SyntaxError, ValueError, RecursionError):
        return _empty_result(rel_path, module_path)

    imports = []
    classes = []
    functions = []
    variables = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names[:MAX_SYMBOL_REFERENCES]:
                imports.append({
                    "module": _safe_name(alias.name),
                    "name": _safe_name(alias.asname or alias.name),
                    "type": "import",
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level > 0:
                parts = module_path.split(".")
                if len(parts) > node.level:
                    base = ".".join(parts[:-node.level])
                    module = f"{base}.{module}" if module else base
                else:
                    module = module or module_path

            for alias in (node.names or [])[:MAX_SYMBOL_REFERENCES]:
                imports.append({
                    "module": _safe_name(module),
                    "name": _safe_name(alias.name),
                    "type": "from_import",
                })

        elif isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases[:MAX_SYMBOL_REFERENCES]:
                try:
                    bases.append(ast.unparse(base)[:MAX_IDENTIFIER_CHARS])
                except (RecursionError, ValueError):
                    continue

            methods = []
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                methods.append({
                    "name": _safe_name(item.name),
                    "params": [
                        _safe_name(arg.arg)
                        for arg in item.args.args[:MAX_SYMBOL_REFERENCES]
                    ],
                    "calls": _extract_calls(item),
                })
                if len(methods) >= MAX_SYMBOL_REFERENCES:
                    break

            classes.append({
                "name": _safe_name(node.name),
                "fqn": f"{module_path}.{_safe_name(node.name)}",
                "bases": bases,
                "methods": methods,
                "decorators": [
                    _get_decorator_name(d)
                    for d in node.decorator_list[:MAX_SYMBOL_REFERENCES]
                ],
            })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": _safe_name(node.name),
                "fqn": f"{module_path}.{_safe_name(node.name)}",
                "params": [
                    _safe_name(arg.arg)
                    for arg in node.args.args[:MAX_SYMBOL_REFERENCES]
                ],
                "calls": _extract_calls(node),
                "decorators": [
                    _get_decorator_name(d)
                    for d in node.decorator_list[:MAX_SYMBOL_REFERENCES]
                ],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })

        elif isinstance(node, ast.Assign):
            for target in node.targets[:MAX_SYMBOL_REFERENCES]:
                if isinstance(target, ast.Name):
                    name = _safe_name(target.id)
                    variables.append({
                        "name": name,
                        "fqn": f"{module_path}.{name}",
                    })

        if (
            len(imports) >= MAX_SYMBOL_REFERENCES
            or len(classes) >= MAX_SYMBOL_REFERENCES
            or len(functions) >= MAX_SYMBOL_REFERENCES
            or len(variables) >= MAX_SYMBOL_REFERENCES
        ):
            break

    is_entry_point = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in ast.iter_child_nodes(tree)
    )

    return {
        "file": rel_path,
        "module": module_path,
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "variables": variables,
        "is_entry_point": is_entry_point,
    }


def _extract_calls(node: ast.AST) -> list[str]:
    """Extract unique call names up to a per-symbol bound."""
    calls = set()
    pending = [node]
    while pending and len(calls) < MAX_SYMBOL_REFERENCES:
        current = pending.pop()
        if isinstance(current, ast.Call):
            if isinstance(current.func, ast.Name):
                calls.add(_safe_name(current.func.id))
            elif isinstance(current.func, ast.Attribute):
                calls.add(_safe_name(current.func.attr))
        pending.extend(ast.iter_child_nodes(current))
    return sorted(calls)


def _get_decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return _safe_name(node.id)
    if isinstance(node, ast.Attribute):
        try:
            return ast.unparse(node)[:512]
        except (RecursionError, ValueError):
            return ""
    if isinstance(node, ast.Call):
        return _get_decorator_name(node.func)
    return ""
