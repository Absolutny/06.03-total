"""Поиск неопределённых глобальных имён (упрощённый аналог pyflakes, без внешних пакетов)."""
import builtins
import dis
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent


def walk(code: types.CodeType):
    yield code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from walk(const)


bad = 0
for file in sorted(list((ROOT / "app").rglob("*.py")) + list((ROOT / "tests").rglob("*.py"))):
    code = compile(file.read_text(encoding="utf-8"), str(file), "exec")
    module_names = set(code.co_names) & {i.argval for i in dis.get_instructions(code) if i.opname in ("STORE_NAME", "STORE_GLOBAL", "IMPORT_FROM", "IMPORT_NAME")}
    defined = {i.argval for i in dis.get_instructions(code) if i.opname in ("STORE_NAME",)}
    # импорты вида "import a.b" сохраняют имя "a" через STORE_NAME — уже учтено
    for c in walk(code):
        for ins in dis.get_instructions(c):
            if ins.opname in ("LOAD_GLOBAL", "LOAD_NAME"):
                name = ins.argval
                if name not in defined and not hasattr(builtins, name) and name not in ("__file__", "__name__"):
                    print(f"{file.relative_to(ROOT)}: неопределённое имя '{name}' (функция {c.co_name})")
                    bad += 1
print("Найдено проблем:", bad)
sys.exit(1 if bad else 0)
