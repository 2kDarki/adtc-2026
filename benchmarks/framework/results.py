"""Historical results storage.

Stores benchmark run results in a directory structure that preserves
history and allows comparison between runs. Never overwrites previous runs.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import BenchmarkRun


class ResultsStore:
    """Manages historical benchmark results.

    Directory structure:
        results/<suite_id>/<version>/<run_id>.json
    """

    def __init__(self, results_dir: Path | str | None = None) -> None:
        if results_dir is None:
            results_dir = Path(__file__).parent.parent / "results"
        self.results_dir = Path(results_dir)

    def save(self, run: BenchmarkRun) -> Path:
        """Save a benchmark run. Returns the path to the saved file."""
        suite_dir = self.results_dir / run.suite_id / run.suite_version
        suite_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{run.run_id}.json"
        filepath = suite_dir / filename

        # Never overwrite — append timestamp if file exists
        if filepath.exists():
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            filename = f"{run.run_id}-{ts}.json"
            filepath = suite_dir / filename

        filepath.write_text(json.dumps(run.to_dict(), indent=2))
        return filepath

    def load(self, suite_id: str, version: str, run_id: str) -> BenchmarkRun | None:
        """Load a specific run."""
        filepath = self.results_dir / suite_id / version / f"{run_id}.json"
        if not filepath.exists():
            return None
        data = json.loads(filepath.read_text())
        return BenchmarkRun.from_dict(data)

    def list_runs(self, suite_id: str, version: str) -> list[dict[str, Any]]:
        """List all runs for a suite version, sorted by timestamp (newest first)."""
        suite_dir = self.results_dir / suite_id / version
        if not suite_dir.exists():
            return []

        runs = []
        for f in sorted(suite_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                runs.append({
                    "run_id": data.get("run_id", f.stem),
                    "model_name": data.get("model_name", "unknown"),
                    "timestamp": data.get("timestamp", "unknown"),
                    "overall_score": data.get("scores", {}).get("overall_score", 0.0),
                    "path": str(f),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by timestamp descending
        runs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return runs

    def list_suites(self) -> dict[str, list[str]]:
        """List all suites and their versions that have results."""
        result: dict[str, list[str]] = {}
        if not self.results_dir.exists():
            return result

        for suite_dir in sorted(self.results_dir.iterdir()):
            if not suite_dir.is_dir():
                continue
            versions = []
            for v_dir in sorted(suite_dir.iterdir()):
                if v_dir.is_dir() and any(v_dir.glob("*.json")):
                    versions.append(v_dir.name)
            if versions:
                result[suite_dir.name] = versions

        return result

    def compare(self, run1: BenchmarkRun, run2: BenchmarkRun) -> dict[str, Any]:
        """Compare two runs of the same suite."""
        s1 = run1.scores.get("overall_score", 0.0)
        s2 = run2.scores.get("overall_score", 0.0)

        return {
            "run1": {"id": run1.run_id, "timestamp": run1.timestamp, "score": s1},
            "run2": {"id": run2.run_id, "timestamp": run2.timestamp, "score": s2},
            "delta": s2 - s1,
            "improved": s2 > s1,
        }
