"""Статическая проверка внутренних импортов (без запуска приложения)."""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def module_path(mod: str):
    p = ROOT / pathlib.Path(*mod.split("."))
    if p.with_suffix(".py").exists():
        return p.with_suffix(".py")
    if (p / "__init__.py").exists():
        return p / "__init__.py"
    return None


def defined_names(path: pathlib.Path) -> set[str]:
    names: set[str] = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names |= {t.id for t in targets if isinstance(t, ast.Name)}
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
    return names


errors = 0
for file in sorted((ROOT / "app").rglob("*.py")) + sorted((ROOT / "tests").rglob("*.py")):
    for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app"):
            target = module_path(node.module)
            if target is None:
                print(f"{file.relative_to(ROOT)}: модуль {node.module} не найден"); errors += 1; continue
            have = defined_names(target)
            for alias in node.names:
                sub = module_path(f"{node.module}.{alias.name}")
                if alias.name not in have and sub is None:
                    print(f"{file.relative_to(ROOT)}: {node.module} не содержит {alias.name}"); errors += 1
print("Ошибок:", errors)
sys.exit(1 if errors else 0)
