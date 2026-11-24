import ast
from pathlib import Path
import tokenize
from typing import TextIO

from import_layers_py.analyzer.import_checker import ImportChecker
from import_layers_py.dto.analysis_result import AnalysisResult
from import_layers_py.dto.config import Config
from import_layers_py.project.project import Project


class Analyzer:
    def __init__(self, project: Project, config: Config):
        self.project = project
        self.config = config
        self.checker = ImportChecker(project, config.layers)

    def analyze(self, paths: list[Path], *, debug_output: TextIO | None = None) -> AnalysisResult:
        result = AnalysisResult()
        for path in self.project.source_files(paths):
            relative_path = self.project.relative_path(path)
            result.nodes.add(relative_path)
            if self.config.debug:
                print(f"processing file {relative_path}", file=debug_output)

            try:
                with tokenize.open(path) as source:
                    tree = ast.parse(source.read(), filename=relative_path)
            except SyntaxError as error:
                location = f"{relative_path}:{error.lineno}" if error.lineno else relative_path
                result.errors.append(f"{location}: {error.msg}")
            except (OSError, UnicodeError) as error:
                result.errors.append(f"{relative_path}: {error}")
            else:
                self.checker.check(path, tree, result)

        return result
