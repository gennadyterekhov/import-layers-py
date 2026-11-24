import argparse
import json
from pathlib import Path
import sys

from import_layers_py.analyzer.analyzer import Analyzer
from import_layers_py.analyzer.pipeline import check_graph
from import_layers_py.config.config_service import CONFIG_NAMES, find_config, read_config
from import_layers_py.project.project import Project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="import-layers-py",
        description="Check imports between layers in the current Python project.",
    )
    parser.add_argument("-c", "--config", type=Path, help="JSON or YAML config path")
    parser.add_argument("--graph", action="store_true", help="print the internal dependency graph as JSON")
    parser.add_argument("paths", type=Path, nargs="*", help="project files or directories to check")
    args = parser.parse_intermixed_args(argv)

    try:
        cwd = Path.cwd()
        default_config = find_config(cwd)
        config_file = cwd / args.config if args.config is not None else default_config
        if config_file is None:
            raise ValueError(f"could not find a config file ({', '.join(CONFIG_NAMES)})")
        root = default_config.parent if default_config is not None else cwd
        config = read_config(config_file)
        if config.root_dir is not None:
            directory = root / config.root_dir
            if not directory.is_dir():
                raise ValueError(f"rootDir is not a directory: {config.root_dir}")
            paths = [directory]
        else:
            paths = [cwd / path for path in args.paths] or [root]
        project = Project(root, ignore_tests=config.ignore_tests)
        result = Analyzer(project, config).analyze(
            paths, debug_output=sys.stderr if args.graph else None, defer_policy=True,
        )
        checked = check_graph(project.root, config.layers, result)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"import-layers-py: {error}", file=sys.stderr)
        return 2

    for error in (*result.errors, *checked["violations"]):
        print(error, file=sys.stderr)
    if args.graph:
        print(json.dumps({
            "nodes": sorted(result.nodes),
            "edges": checked["edges"],
        }))
    if result.errors:
        return 2
    if checked["violations"]:
        return 1
    if not args.graph:
        print("OK")
    return 0
