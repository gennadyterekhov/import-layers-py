import ast
from pathlib import Path
import tokenize

from import_layers_py.analyzer.import_checker import ImportChecker
from import_layers_py.dto.analysis_result import AnalysisResult
from import_layers_py.dto.config import Config
from import_layers_py.project.project import Project


class Analyzer:
    def __init__(self, project: Project, config: Config):
        self.project = project
        self.config = config
        self.checker = ImportChecker(project, config.layers)

    def analyze(self, directories: list[Path]) -> AnalysisResult:
        result = AnalysisResult()
        for path in self.project.source_files(directories):
            relative_path = path.relative_to(self.project.root).as_posix()
            if self.config.debug:
                print(f"processing file {relative_path}")

            try:
                with tokenize.open(path) as source:
                    tree = ast.parse(source.read(), filename=relative_path)
            except SyntaxError as error:
                location = f"{relative_path}:{error.lineno}" if error.lineno else relative_path
                result.errors.append(f"{location}: {error.msg}")
            except (OSError, UnicodeError) as error:
                result.errors.append(f"{relative_path}: {error}")
            else:
                result.violations.extend(self.checker.check(path, tree))

        return result
