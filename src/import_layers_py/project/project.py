import os
from collections.abc import Iterator
from pathlib import Path


EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox",
    "build", "dist", "node_modules", "site-packages",
}


def raise_walk_error(error: OSError) -> None:
    raise error


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.src = self.root / "src"

    def source_files(self, directories: list[Path]) -> Iterator[Path]:
        files = set()
        for directory in directories:
            start = (self.root / directory).resolve()
            if not self.includes(start) or not start.is_dir():
                raise ValueError(f"invalid project directory: {directory}")

            for current, dirs, names in os.walk(start, onerror=raise_walk_error):
                dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
                for name in names:
                    path = Path(current, name)
                    if path.suffix == ".py" and not path.is_symlink() and path.is_file():
                        files.add(path)

        yield from sorted(files)

    def includes(self, path: Path) -> bool:
        return (
            path.is_relative_to(self.root)
            and not EXCLUDED_DIRS.intersection(path.relative_to(self.root).parts)
        )

    def module_parts(self, path: Path) -> tuple[str, ...]:
        root = self.src if path.is_relative_to(self.src) else self.root
        parts = path.relative_to(root).with_suffix("").parts
        return parts[:-1] if path.name == "__init__.py" else parts

    def resolve_module(self, module: str, *, within: Path | None = None) -> Path | None:
        if not module:
            return within
        parts = module.split(".")
        if not all(part.isidentifier() for part in parts):
            return None

        search_paths = [within] if within is not None else [self.root, self.src]
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            namespaces = []
            for directory in search_paths:
                package = (directory / part).resolve()
                source = (directory / f"{part}.py").resolve()
                if self.includes(package) and (package / "__init__.py").is_file():
                    if last:
                        return package
                    search_paths = [package]
                    break
                if self.includes(source) and source.is_file():
                    return source if last else None
                if self.includes(package) and package.is_dir():
                    namespaces.append(package)
            else:
                if not namespaces:
                    return None
                if last:
                    return namespaces[0]
                search_paths = namespaces

        return None
