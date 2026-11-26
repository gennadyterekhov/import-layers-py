import ast
from pathlib import Path
from typing import TextIO

from import_layers_py.analyzer.pipeline import check_graph, parse_project
from import_layers_py.analyzer.reference_collector import ReferenceCollector
from import_layers_py.dto.analysis_result import AnalysisResult
from import_layers_py.dto.config import Config
from import_layers_py.project.project import Project


class Analyzer:
    def __init__(self, project: Project, config: Config):
        self.project = project
        self.config = config
        self.collector = ReferenceCollector(project, config.layers)

    def analyze(self, paths: list[Path], *, debug_output: TextIO | None = None) -> AnalysisResult:
        result = AnalysisResult()
        sources = list(self.project.source_files(paths))
        snapshot = parse_project(self.project.root, [self.project.relative_path(path) for path in sources])
        for path in sources:
            relative_path = self.project.relative_path(path)
            result.nodes.add(relative_path)
            if self.config.debug:
                print(f"processing file {relative_path}", file=debug_output)

            result.errors.extend(snapshot["errors"].get(relative_path, []))
            if relative_path in snapshot["trees"]:
                tree = decode_ast(snapshot["trees"][relative_path])
                self.collector.collect(path, tree, result)

        checked = check_graph(self.config.layers, snapshot["trees"], result)
        result.violations = checked["violations"]
        result.edges = {(edge["from"], edge["to"]) for edge in checked["edges"]}
        result.nodes.update(target for _, target in result.edges)

        return result


def decode_ast(value):
    if isinstance(value, list):
        return [decode_ast(item) for item in value]
    if not isinstance(value, dict):
        return value

    kind = value["_type"]
    if kind == "bytes":
        return bytes.fromhex(value["hex"])
    if kind == "complex":
        return complex(decode_ast(value["real"]), decode_ast(value["imag"]))
    if kind == "float":
        return float(value["value"])
    if kind == "ellipsis":
        return Ellipsis

    node_type = getattr(ast, kind, None)
    if not isinstance(node_type, type) or not issubclass(node_type, ast.AST):
        raise ValueError(f"Unknown Python AST node {kind}")
    return node_type(**{name: decode_ast(item) for name, item in value.items() if name != "_type"})
