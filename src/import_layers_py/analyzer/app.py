import argparse
from pathlib import Path
import sys

from import_layers_py.analyzer.analyzer import Analyzer
from import_layers_py.config.config_service import read_config
from import_layers_py.project.project import Project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="import-layers-py",
        description="Check imports between layers in the current Python project.",
    )
    parser.add_argument("-c", type=Path, default=Path("import_layers.json"), help="JSON config path")
    parser.add_argument("directories", type=Path, nargs="*", help="project directories to check")
    args = parser.parse_intermixed_args(argv)

    try:
        config = read_config(args.c)
        directories = [config.root_dir] if config.root_dir else args.directories or [Path(".")]
        result = Analyzer(Project(Path.cwd()), config).analyze(directories)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"import-layers-py: {error}", file=sys.stderr)
        return 2

    for error in (*result.errors, *result.violations):
        print(error, file=sys.stderr)
    if result.errors:
        return 2
    if result.violations:
        return 1
    print("OK")
    return 0
