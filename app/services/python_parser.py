import ast
from pathlib import Path


def parse_file(filepath: Path, repo_root: Path) -> dict:
    """Parse a Python file using AST and extract structural information."""
    rel_path = str(filepath.relative_to(repo_root))
    module_path = rel_path.replace("/", ".").removesuffix(".py")

    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return {
            "file": rel_path,
            "module": module_path,
            "imports": [],
            "classes": [],
            "functions": [],
            "variables": [],
        }

    imports = []
    classes = []
    functions = []
    variables = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name,
                    "name": alias.asname or alias.name,
                    "type": "import",
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Handle relative imports
            if node.level > 0:
                parts = module_path.split(".")
                if len(parts) > node.level:
                    base = ".".join(parts[:-node.level])
                    module = f"{base}.{module}" if module else base
                else:
                    module = module or module_path

            for alias in (node.names or []):
                imports.append({
                    "module": module,
                    "name": alias.name,
                    "type": "from_import",
                })

        elif isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))

            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    calls = _extract_calls(item)
                    methods.append({
                        "name": item.name,
                        "params": [arg.arg for arg in item.args.args],
                        "calls": calls,
                    })

            classes.append({
                "name": node.name,
                "fqn": f"{module_path}.{node.name}",
                "bases": bases,
                "methods": methods,
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
            })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = _extract_calls(node)
            functions.append({
                "name": node.name,
                "fqn": f"{module_path}.{node.name}",
                "params": [arg.arg for arg in node.args.args],
                "calls": calls,
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    variables.append({
                        "name": target.id,
                        "fqn": f"{module_path}.{target.id}",
                    })

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
    """Extract function/method call names from an AST node."""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(set(calls))


def _get_decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return ast.unparse(node)
    elif isinstance(node, ast.Call):
        return _get_decorator_name(node.func)
    return ""
