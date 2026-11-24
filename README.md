# import-layers-py

Checks dependency direction between layers of a Python project. Requires Python 3.10 or newer and uses the standard library's `ast` parser.

## Configuration

Create `import_layers.json` in the project root.

```json
{
  "layers": ["domain", "application"],
  "debug": false
}
```

As in the PHP tool, a layer can import from itself and from earlier entries in the list. For example, `application` can import from `domain`, and importing from `application` inside `domain` is a violation. Layer names match complete dotted module segments. Use a qualified name such as `app.domain` to scope the rule to a specific package. The first matching layer wins.

## Running with uv

From the project you want to check:

```sh
uv run import-layers-py
uv run import-layers-py -c config/layers.json src/app/domain src/app/application
```

By default the tool scans the current directory recursively. Positional directories narrow the scan. If set, `rootDir` in the config takes precedence over those arguments. Relative paths, including the `-c` path, are resolved against the current working directory.

The tool checks static `import` and `from ... import ...` statements in `.py` files. It resolves absolute imports against the project root and its `src` directory, and relative imports against the containing package. It skips common virtual environment, cache, and build directories. Dynamic imports, third-party packages, and modules outside the project are outside the scope of the check.

On success, the command prints `OK`. Violations include the source file, line number, and target module and are printed to stderr. Set `"debug": true` to print the relative path of each checked file. Exit codes are `0` for success, `1` for a layer violation, and `2` for an argument, configuration, or source parsing error.

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
