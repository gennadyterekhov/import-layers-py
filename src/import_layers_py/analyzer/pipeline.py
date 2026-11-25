import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from import_layers_py.dto.analysis_result import AnalysisResult


def check_graph(root: Path, layers: tuple[str, ...], result: AnalysisResult) -> dict:
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
    payload = {
        "language": "py",
        "interpreter": sys.executable,
        "root": str(root),
        "layers": layers,
        "files": result.files,
        "references": result.references,
    }
    process = subprocess.run(
        [*command, "--project", str(checkout) if checkout else ""],
        input=json.dumps(payload), capture_output=True, text=True,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or f"degra exited with status {process.returncode}")
    return json.loads(process.stdout)
