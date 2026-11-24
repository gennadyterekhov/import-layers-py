import json
from pathlib import Path, PurePosixPath

import yaml

from import_layers_py.dto.config import Config


CONFIG_NAMES = ("import_layers.json", "import_layers.yaml", "import_layers.yml")


def find_config(start: Path) -> Path | None:
    for directory in (start, *start.parents):
        for name in CONFIG_NAMES:
            path = directory / name
            if path.is_file():
                return path
    return None


def read_config(path: Path) -> Config:
    try:
        contents = path.read_text(encoding="utf-8")
        data = yaml.safe_load(contents) if path.suffix.lower() in {".yaml", ".yml"} else json.loads(contents)
        if not isinstance(data, dict):
            raise ValueError("expected a configuration object")

        layers = data.get("layers")
        if (
            not isinstance(layers, list)
            or not layers
            or any(not isinstance(layer, str) or not layer.strip() for layer in layers)
            or len(set(layers)) != len(layers)
        ):
            raise ValueError("layers must be a non-empty list of unique strings")
        for layer in layers:
            if "/" in layer:
                selector = PurePosixPath(layer)
                if selector.is_absolute() or not selector.parts or ".." in selector.parts:
                    raise ValueError(f"layer path must be relative to the project root: {layer}")

        debug = data.get("debug", False)
        if not isinstance(debug, bool):
            raise ValueError("debug must be a boolean")

        root_dir = data.get("rootDir", "")
        if not isinstance(root_dir, str):
            raise ValueError("rootDir must be a directory path")
        ignore_tests = data.get("ignoreTests", data.get("ignore_tests", False))
        if not isinstance(ignore_tests, bool):
            raise ValueError("ignoreTests must be a boolean")
        return Config(tuple(layers), debug, Path(root_dir) if root_dir else None, ignore_tests)
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f"{path}: {error}") from error
