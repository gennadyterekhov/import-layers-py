import json
from pathlib import Path

from import_layers_py.dto.config import Config


def read_config(path: Path) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")

        layers = data.get("layers")
        if (
            not isinstance(layers, list)
            or not layers
            or any(
                not isinstance(layer, str)
                or not all(part.isidentifier() for part in layer.split("."))
                for layer in layers
            )
            or len(set(layers)) != len(layers)
        ):
            raise ValueError("layers must be a non-empty list of unique dotted module names")

        debug = data.get("debug", False)
        if not isinstance(debug, bool):
            raise ValueError("debug must be a boolean")

        root_dir = data.get("rootDir", "")
        if not isinstance(root_dir, str):
            raise ValueError("rootDir must be a directory path")
        return Config(tuple(layers), debug, Path(root_dir) if root_dir else None)
    except (OSError, ValueError) as error:
        raise ValueError(f"{path}: {error}") from error
