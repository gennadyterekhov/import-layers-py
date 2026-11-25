import os
from collections.abc import Iterator
from pathlib import Path


EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox",
    "build", "dist", "node_modules", "site-packages",
}
TEST_DIRS = {"test", "tests", "__tests__"}


def raise_walk_error(error: OSError) -> None:
    raise error


class Project:
    def __init__(self, root: Path, *, ignore_tests: bool = False):
        self.root = root.resolve()
        self.src = self.root / "src"
        self.ignore_tests = ignore_tests

    def source_files(self, paths: list[Path]) -> Iterator[Path]:
        files = set()
        for path in paths:
            start = (self.root / path).resolve()
            included = self.includes(start)
            is_directory = included and start.is_dir()
            is_python_file = included and start.suffix == ".py" and start.is_file()
            if not (is_directory or is_python_file):
                raise ValueError(f"invalid project path: {path}")
            if self.is_ignored_test(start):
                continue
            if is_directory:
                files.update(self._directory_sources(start))
            else:
                files.add(start)

        yield from sorted(files)

    def _directory_sources(self, directory: Path) -> Iterator[Path]:
        for current, dirs, names in os.walk(directory, onerror=raise_walk_error):
            dirs[:] = [
                name for name in dirs
                if name not in EXCLUDED_DIRS and not self.is_ignored_test(Path(current, name))
            ]
            for name in names:
                path = Path(current, name)
                if (
                    path.suffix == ".py" and not path.is_symlink()
                    and path.is_file() and not self.is_ignored_test(path)
                ):
                    yield path

    def relative_path(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def includes(self, path: Path) -> bool:
        return (
            path.is_relative_to(self.root)
            and not EXCLUDED_DIRS.intersection(path.relative_to(self.root).parts)
        )

    def is_ignored_test(self, path: Path) -> bool:
        return self.ignore_tests and (
            bool(TEST_DIRS.intersection(path.relative_to(self.root).parts))
            or (path.suffix == ".py" and (path.name.startswith("test_") or path.name.endswith("_test.py")))
        )

    def module_file(self, path: Path) -> Path | None:
        file = (path / "__init__.py").resolve() if path.is_dir() else path
        if self.includes(file) and file.is_file():
            return file
        return None

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
            search_paths = self._find_module_part(part, search_paths)
            if not search_paths:
                return None
            if index < len(parts) - 1 and not search_paths[0].is_dir():
                return None
        return search_paths[0]

    def _find_module_part(self, part: str, search_paths: list[Path]) -> list[Path]:
        namespaces = []
        for directory in search_paths:
            package = (directory / part).resolve()
            source = (directory / f"{part}.py").resolve()
            if self.includes(package) and package.is_dir():
                if (package / "__init__.py").is_file():
                    return [package]
                namespaces.append(package)
            if self.includes(source) and source.is_file():
                return [source]
        return namespaces
