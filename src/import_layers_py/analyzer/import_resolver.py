import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from import_layers_py.analyzer.dynamic_imports import literal_import_calls
from import_layers_py.project.project import Project


@dataclass(frozen=True)
class LocalImport:
    line: int
    name: str
    target: Path | None


class ImportResolver:
    def __init__(self, project: Project):
        self.project = project

    def imports_in(self, path: Path, tree: ast.Module) -> Iterator[LocalImport]:
        parts = self.project.module_parts(path)
        package = parts if path.name == "__init__.py" else parts[:-1]
        nodes = list(ast.walk(tree))
        statements = [node for node in nodes if isinstance(node, (ast.Import, ast.ImportFrom))]
        calls = dict(literal_import_calls(tree, nodes))
        imports = sorted((*statements, *calls), key=lambda node: (node.lineno, node.col_offset))

        for node in imports:
            if isinstance(node, ast.ImportFrom):
                targets = self._from_import_targets(node, path, package)
            else:
                names = [calls[node]] if isinstance(node, ast.Call) else [alias.name for alias in node.names]
                targets = ((name, self.project.resolve_module(name)) for name in names)

            relative = isinstance(node, ast.ImportFrom) and node.level > 0
            for name, target in targets:
                if target is not None or relative or self._has_local_module_root(name):
                    yield LocalImport(node.lineno, name, target)

    def _from_import_targets(
        self, node: ast.ImportFrom, path: Path, package: tuple[str, ...]
    ) -> Iterator[tuple[str, Path | None]]:
        prefix = ()
        within = None
        if node.level:
            if node.level > len(package):
                yield f"{'.' * node.level}{node.module or ''}", None
                return
            prefix = package[:len(package) - node.level + 1]
            within = path.parents[node.level - 1]

        base = node.module or ""
        seen = set()
        for alias in node.names:
            # An imported name can be a submodule or an attribute of the base module.
            imported = f"{base}.{alias.name}" if base else alias.name
            target = self.project.resolve_module(imported, within=within)
            if target is None:
                imported = base
                if imported in seen:
                    continue
                target = self.project.resolve_module(base, within=within)
            elif imported in seen:
                continue
            seen.add(imported)
            name = ".".join(part for part in (*prefix, imported) if part)
            yield name, target

    def _has_local_module_root(self, name: str) -> bool:
        parent = self.project.resolve_module(name.split(".", 1)[0])
        return parent is not None and self.project.module_file(parent) is not None
