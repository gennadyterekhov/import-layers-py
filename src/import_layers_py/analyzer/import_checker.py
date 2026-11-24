import ast
from collections.abc import Iterator
from pathlib import Path

from import_layers_py.project.project import Project


class ImportChecker:
    def __init__(self, project: Project, layers: tuple[str, ...]):
        self.project = project
        self.layers = layers
        self.layer_parts = [tuple(layer.split(".")) for layer in layers]

    def layer_index(self, parts: tuple[str, ...]) -> int | None:
        for index, layer in enumerate(self.layer_parts):
            if any(parts[start:start + len(layer)] == layer for start in range(len(parts))):
                return index
        return None

    def targets(
        self, node: ast.Import | ast.ImportFrom, path: Path, package: tuple[str, ...]
    ) -> Iterator[tuple[str, Path]]:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (target := self.project.resolve_module(alias.name)) is not None:
                    yield alias.name, target
            return

        prefix = ()
        within = None
        if node.level:
            if node.level > len(package):
                return
            prefix = package[:len(package) - node.level + 1]
            within = path.parents[node.level - 1]
        base = node.module or ""
        seen = set()
        for alias in node.names:
            # The imported name can be a submodule or an attribute of the base module.
            imported = f"{base}.{alias.name}" if base else alias.name
            target = self.project.resolve_module(imported, within=within)
            if target is None:
                imported = base
                target = self.project.resolve_module(base, within=within)
            if target is not None and imported not in seen:
                seen.add(imported)
                name = ".".join(part for part in (*prefix, imported) if part)
                yield name, target

    def check(self, path: Path, tree: ast.AST) -> Iterator[str]:
        parts = self.project.module_parts(path)
        source_index = self.layer_index(parts)
        if source_index is None:
            return

        package = parts if path.name == "__init__.py" else parts[:-1]
        imports = sorted(
            (node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))),
            key=lambda node: (node.lineno, node.col_offset),
        )
        source = path.relative_to(self.project.root).as_posix()
        for node in imports:
            for module, target in self.targets(node, path, package):
                target_parts = (
                    self.project.module_parts(target)
                    if target.is_file()
                    else self.project.module_parts(target / "__init__.py")
                )
                target_index = self.layer_index(target_parts)
                if target_index is not None and source_index < target_index:
                    yield (
                        f"{source}:{node.lineno} -> {module}: cannot import package from lower "
                        f"layer ({self.layers[source_index]} -> {self.layers[target_index]})"
                    )
