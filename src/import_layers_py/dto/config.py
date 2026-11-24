from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    layers: tuple[str, ...]
    debug: bool = False
    root_dir: Path | None = None
