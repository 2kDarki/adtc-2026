"""Suite loader — loads datasets from discovered suite directories."""

from __future__ import annotations

import json
from pathlib import Path

from .models import EvalDataset, EvalItem, SuiteMetadata


def load_dataset(suite_path: Path | str) -> EvalDataset:
    """Load the dataset.json from a suite directory."""
    suite_path = Path(suite_path)
    dataset_file = suite_path / "dataset.json"

    if not dataset_file.exists():
        raise FileNotFoundError(f"No dataset.json found in {suite_path}")

    data = json.loads(dataset_file.read_text())
    return EvalDataset.from_dict(data)


def load_suite_metadata(suite_path: Path | str) -> SuiteMetadata:
    """Load suite.json from a suite directory."""
    suite_path = Path(suite_path)
    meta_file = suite_path / "suite.json"

    if not meta_file.exists():
        raise FileNotFoundError(f"No suite.json found in {suite_path}")

    data = json.loads(meta_file.read_text())
    return SuiteMetadata.from_dict(data)


def list_suite_files(suite_path: Path | str) -> dict[str, Path]:
    """List all files in a suite directory."""
    suite_path = Path(suite_path)
    files: dict[str, Path] = {}
    for f in sorted(suite_path.iterdir()):
        if f.is_file():
            files[f.name] = f
    return files
