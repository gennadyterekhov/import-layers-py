import ast
from pathlib import Path

from import_layers_py.analyzer.import_resolver import ImportResolver
from import_layers_py.analyzer.layer_policy import LayerPolicy
from import_layers_py.dto.analysis_result import AnalysisResult
from import_layers_py.project.project import Project


class ReferenceCollector:
    def __init__(self, project: Project, layers: tuple[str, ...]):
        self.project = project
        self.resolver = ImportResolver(project)
        self.policy = LayerPolicy(layers)

    def layer_index(self, path: Path) -> int | None:
        module = path / "__init__.py" if path.is_dir() else path
        directory = module.parent.relative_to(self.project.root).parts
        return self.policy.layer_index(directory, self.project.module_parts(module))

    def collect(self, path: Path, tree: ast.Module, result: AnalysisResult) -> None:
        source_layer = self.layer_index(path)
        source = self.project.relative_path(path)

        for imported in self.resolver.imports_in(path, tree):
            target = imported.target
            if target is None:
                result.errors.append(f"{source}:{imported.line}: unresolved import {imported.name}")
                continue
            if self.project.is_ignored_test(target):
                continue

            destination = ""
            target_file = self.project.module_file(target)
            if target_file is not None and not self.project.is_ignored_test(target_file):
                destination = self.project.relative_path(target_file)

            target_layer = self.layer_index(target)
            result.references.append({
                "from": source,
                "to": destination if destination != source else "",
                "line": imported.line,
                "specifier": imported.name,
                "fromLayer": self.policy.layers[source_layer] if source_layer is not None else "",
                "toLayer": self.policy.layers[target_layer] if target_layer is not None else "",
                "resolvedLayers": True,
            })
