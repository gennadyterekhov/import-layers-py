import ast
from collections.abc import Iterator


def literal_import_calls(tree: ast.Module, nodes: list[ast.AST]) -> Iterator[tuple[ast.Call, str]]:
    recognized_aliases = set()
    modules = set()
    functions = {"__import__"}
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.name == "importlib":
                    recognized_aliases.add(alias)
                    modules.add(alias.asname or alias.name)
        elif isinstance(statement, ast.ImportFrom) and statement.module == "importlib" and not statement.level:
            for alias in statement.names:
                if alias.name == "import_module":
                    recognized_aliases.add(alias)
                    functions.add(alias.asname or alias.name)

    # Drop names with ambiguous bindings anywhere in the file instead of guessing their scope.
    shadowed = modules & functions
    for node in nodes:
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            shadowed.add(node.id)
        elif isinstance(node, ast.arg):
            shadowed.add(node.arg)
        elif (
            isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                ast.ExceptHandler, ast.MatchAs, ast.MatchStar,
            ))
            and node.name is not None
        ):
            shadowed.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            shadowed.add(node.rest)
        elif isinstance(node, ast.alias) and node not in recognized_aliases:
            shadowed.add(node.asname or node.name.split(".", 1)[0])
        elif (
            isinstance(node, ast.Attribute) and node.attr == "import_module"
            and isinstance(node.ctx, (ast.Store, ast.Del)) and isinstance(node.value, ast.Name)
        ):
            shadowed.add(node.value.id)

    modules -= shadowed
    functions -= shadowed
    if "*" in shadowed:
        return

    for node in nodes:
        if not isinstance(node, ast.Call) or len(node.args) != 1 or node.keywords:
            continue
        arg = node.args[0]
        if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
            continue
        if not all(part.isidentifier() for part in arg.value.split(".")):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id in functions:
            yield node, arg.value
        elif (
            isinstance(function, ast.Attribute) and function.attr == "import_module"
            and isinstance(function.value, ast.Name) and function.value.id in modules
        ):
            yield node, arg.value
