"""Suite discovery and registry.

Dynamically discovers benchmark suites by scanning the suites/ directory
for valid suite.json files. No hardcoded suite registration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import SuiteMetadata


class SuiteRegistry:
    """Discovers and manages benchmark suites."""

    def __init__(self, suites_dir: Path | str | None = None) -> None:
        if suites_dir is None:
            suites_dir = Path(__file__).parent.parent / "suites"
        self.suites_dir = Path(suites_dir)
        self._cache: dict[str, tuple[Path, SuiteMetadata]] | None = None

    def discover(self) -> dict[str, tuple[Path, SuiteMetadata]]:
        """Scan suites/ directory for valid suite.json files.

        Directory structure expected:
            suites/<suite_id>/<version>/suite.json
        """
        if self._cache is not None:
            return self._cache

        suites: dict[str, tuple[Path, SuiteMetadata]] = {}

        if not self.suites_dir.exists():
            self._cache = suites
            return suites

        for suite_dir in sorted(self.suites_dir.iterdir()):
            if not suite_dir.is_dir():
                continue
            # Each version is a subdirectory
            for version_dir in sorted(suite_dir.iterdir()):
                if not version_dir.is_dir():
                    continue
                suite_json = version_dir / "suite.json"
                if not suite_json.exists():
                    continue
                try:
                    import json
                    data = json.loads(suite_json.read_text())
                    meta = SuiteMetadata.from_dict(data)
                    # Use suite_id:version as key for multi-version support
                    key = f"{meta.id}:{meta.version}"
                    suites[key] = (version_dir, meta)
                except (KeyError, ValueError, Exception):
                    continue

        self._cache = suites
        return suites

    def list_suites(self) -> list[SuiteMetadata]:
        """Return metadata for all discovered suites (latest version per suite)."""
        all_suites = self.discover()
        # Group by suite id, keep latest version
        latest: dict[str, tuple[Path, SuiteMetadata]] = {}
        for key, (path, meta) in all_suites.items():
            suite_id = meta.id
            if suite_id not in latest or meta.version > latest[suite_id][1].version:
                latest[suite_id] = (path, meta)
        return [meta for _, meta in latest.values()]

    def list_versions(self, suite_id: str) -> list[SuiteMetadata]:
        """Return all versions of a specific suite."""
        all_suites = self.discover()
        versions = []
        for key, (path, meta) in all_suites.items():
            if meta.id == suite_id:
                versions.append(meta)
        return sorted(versions, key=lambda m: m.version)

    def get_suite(self, suite_id: str, version: str | None = None) -> tuple[Path, SuiteMetadata] | None:
        """Get a specific suite. If version is None, returns latest."""
        all_suites = self.discover()

        if version is not None:
            key = f"{suite_id}:{version}"
            return all_suites.get(key)

        # Find latest version
        candidates = [(p, m) for k, (p, m) in all_suites.items() if m.id == suite_id]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1].version)

    def describe(self, suite_id: str) -> str:
        """Human-readable description of a suite."""
        result = self.get_suite(suite_id)
        if result is None:
            return f"Suite '{suite_id}' not found."

        path, meta = result
        versions = self.list_versions(suite_id)

        lines = [
            f"Suite: {meta.name} ({meta.id})",
            f"  Version:     {meta.version}",
            f"  Description: {meta.description}",
            f"  Languages:   {', '.join(meta.languages)}",
            f"  Categories:  {', '.join(meta.categories)}",
            f"  Tags:        {', '.join(meta.tags) if meta.tags else '(none)'}",
            f"  Path:        {path}",
        ]
        if len(versions) > 1:
            lines.append(f"  All versions: {', '.join(v.version for v in versions)}")
        if meta.maintainers:
            lines.append("  Maintainers:")
            for m in meta.maintainers:
                lines.append(f"    - {m.get('name', '?')} <{m.get('email', '?')}>")
        if meta.dependencies:
            lines.append(f"  Dependencies: {', '.join(meta.dependencies)}")

        return "\n".join(lines)
