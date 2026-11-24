import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class CliTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.write_config()

    def write(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    def write_config(self, name="import_layers.json", **options):
        self.write(name, json.dumps({"layers": ["high", "low"], **options}))

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "import_layers_py", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def test_success_only_prints_ok(self):
        self.write("high/item.py", "import json\nimport external.low\n")
        self.write("low/item.py", "from high import item\n")
        self.write(".venv/lib/ignored.py", "this should not parse!\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "OK\n")
        self.assertEqual(result.stderr, "")

    def test_absolute_and_relative_imports_in_src_layout(self):
        self.write("src/app/high/check.py", """\
import app.low.one as one, app.low.two
from .. import low
from ..low import one
def load():
    from app.low.two import value
""")
        self.write("src/app/low/one.py", "value = 1\n")
        self.write("src/app/low/two.py", "value = 2\n")

        result = self.run_cli()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        errors = result.stderr.splitlines()
        self.assertEqual(len(errors), 5, result.stderr)
        for line, target in [(1, "one"), (1, "two"), (2, ""), (3, "one"), (5, "two")]:
            module = f"app.low.{target}" if target else "app.low"
            self.assertIn(
                f"src/app/high/check.py:{line} -> {module}: "
                "cannot import package from lower layer (high -> low)",
                errors,
            )

    def test_custom_config_and_multiple_directories(self):
        self.write_config("config/layers.json", debug=True, layers=["app.high", "app.low"])
        self.write("app/high/item.py", "import app.low.item\n")
        self.write("app/low/item.py", "pass\n")
        self.write("other/skipped.py", "this should not parse!\n")

        result = self.run_cli("-c", "config/layers.json", "app/high", "app/low")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout,
            "processing file app/high/item.py\nprocessing file app/low/item.py\n",
        )
        self.assertIn("(app.high -> app.low)", result.stderr)

    def test_root_dir_takes_precedence_over_positional_directory(self):
        self.write_config(rootDir="low", debug=True)
        self.write("high/item.py", "import low.item\n")
        self.write("low/item.py", "pass\n")
        result = self.run_cli("high")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "processing file low/item.py\nOK\n")

    def test_reports_parse_errors_and_continues(self):
        self.write("high/broken.py", "from . import\n")
        self.write("high/item.py", "from low import item\n")
        self.write("low/item.py", "pass\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("high/broken.py:1", result.stderr)
        self.assertIn("cannot import package from lower layer", result.stderr)

    def test_rejects_non_boolean_debug(self):
        self.write_config(debug="true")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("debug must be a boolean", result.stderr)

    def test_matches_full_module_segments_only(self):
        self.write("high/check.py", "import shallow.lowest\n")
        self.write("shallow/lowest.py", "pass\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "OK\n")

    def test_relative_import_uses_the_package_containing_the_source(self):
        self.write("app.py", "pass\n")
        self.write("src/app/high/check.py", "from ..low import item\n")
        self.write("src/app/low/item.py", "raise RuntimeError('must never execute')\n")
        result = self.run_cli("src/app/high")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("src/app/high/check.py:1 -> app.low.item", result.stderr)


if __name__ == "__main__":
    unittest.main()
