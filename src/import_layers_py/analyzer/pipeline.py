import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from import_layers_py.dto.analysis_result import AnalysisResult


def parse_project(root: Path, files: list[str]) -> dict:
    return run_pipeline("--parse-project", {
        "language": "py", "interpreter": sys.executable, "root": str(root), "files": files,
    })


def check_graph(layers: tuple[str, ...], trees: dict, result: AnalysisResult) -> dict:
    return run_pipeline("--project", {
        "language": "py", "layers": layers, "trees": trees, "references": result.references,
    })


def run_pipeline(mode: str, payload: dict) -> dict:
    checkout = next(
        (parent for parent in Path(__file__).resolve().parents if (parent / "degra/go.mod").is_file()),
        None,
    )
    directory = os.environ.get("IMPORT_LAYERS_TOOLS")
    binary = str(Path(directory) / "degra") if directory else shutil.which("degra")
    if binary:
        command = [binary]
    elif checkout:
        command = ["go", "-C", str(checkout / "degra"), "run", "."]
    else:
        raise RuntimeError("degra not found on PATH")
    process = subprocess.run(
        [*command, mode, str(checkout) if checkout else ""],
        input=json.dumps(payload), capture_output=True, text=True,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or f"degra exited with status {process.returncode}")
    return json.loads(process.stdout)
