from pathlib import PurePosixPath


class LayerPolicy:
    def __init__(self, layers: tuple[str, ...]):
        self.layers = layers
        self.path_layers = [
            (index, PurePosixPath(layer).parts) for index, layer in enumerate(layers) if "/" in layer
        ]
        self.module_layers = [
            (index, tuple(layer.split("."))) for index, layer in enumerate(layers) if "/" not in layer
        ]

    def layer_index(self, directory: tuple[str, ...], module: tuple[str, ...]) -> int | None:
        for index, parts in self.path_layers:
            if directory[:len(parts)] == parts:
                return index

        for index, parts in self.module_layers:
            if any(module[start:start + len(parts)] == parts for start in range(len(module))):
                return index
        return None
