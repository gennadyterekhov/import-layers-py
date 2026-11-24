# import-layers-py

Checks dependency direction between layers of a Python project. Requires Python 3.10 or newer and uses the standard library's `ast` parser.

## Configuration

Create `import_layers.json`, `import_layers.yaml`, or `import_layers.yml` in the project root. The CLI searches upward from the current directory and uses the first directory with a config, preferring JSON in that directory.

```json
{
  "layers": ["domain", "application"],
  "debug": false,
  "ignoreTests": false
}
```

A layer can import from itself and from earlier entries in the list. For example, `application` can import from `domain`, and importing from `application` inside `domain` is a violation. Layer names match complete dotted module segments. Use a qualified name such as `app.domain` to scope the rule to a package. Directory prefixes such as `src/app/domain` match from the project root and take precedence over dotted names. The first matching entry within each kind wins.

`ignoreTests: true` skips files in `test`, `tests`, and `__tests__` directories and files named `test_*.py` or `*_test.py`. The legacy `ignore_tests` spelling is accepted.

## Running with uv

From the project you want to check, use `uv run import-layers-py` if the package is installed. To run a local checkout directly:

```sh
uvx --from /path/to/import-layers-py import-layers-py
uvx --from /path/to/import-layers-py import-layers-py --config config/layers.yml src/app/domain.py src/app/application
```

By default the tool scans the project root recursively. Positional files and directories narrow the scan and resolve from the current directory. `rootDir` takes precedence over those arguments and resolves from the project root. `-c` and `--config` accept a JSON or YAML path relative to the current directory. If no default config is found above that directory, the current directory is the project root.

The tool checks `import` and `from ... import ...` statements in `.py` files. It also checks `importlib.import_module("pkg.module")` and `__import__("pkg.module")` with a single string literal as the argument. It recognizes aliases imported at module level and skips helper names with conflicting bindings. Computed arguments and relative dynamic imports are outside this check.

Absolute imports resolve against the project root and its `src` directory. Relative imports resolve against the containing package. The tool skips common virtual environment, cache, and build directories. Missing explicitly named relative modules and missing submodules of local regular packages produce diagnostics. Imported attributes, namespace packages shared with installed distributions, and external packages limit what can be resolved statically.

On success, the command prints `OK`. Violations include the source file, line number, and target module and are printed to stderr. Set `"debug": true` to print the relative path of each checked file. Exit codes are `0` for success, `1` for a layer violation, and `2` for an argument, configuration, or analysis error.

`--graph` writes a JSON object with `nodes` and `edges` arrays. Edges are `{ "from": "...", "to": "..." }` objects with project-relative file paths. It includes checked files and their directly imported local files, including package `__init__.py` files. Namespace packages without an `__init__.py` have no file to include. Diagnostics and debug output go to stderr in this mode.

## Development

```sh
uv run import-layers-py
uv run python -m unittest discover -s tests
uv build
```

## See also

- [import-layers-go](https://github.com/gennadyterekhov/import-layers-go)
- [import-layers-php](https://github.com/gennadyterekhov/import-layers-php)
- [import-layers-js](https://github.com/gennadyterekhov/import-layers-js)
