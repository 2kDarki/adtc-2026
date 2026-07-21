#!/usr/bin/env python3
"""render_report.py — builds markdown report from llama-bench JSON + system metadata.

Usage:
    python render_report.py <run_number> <commit_sha> <json_dir> <output_path>

    json_dir should contain:
      - qwen2.5-3b-configA.json, qwen2.5-3b-configB.json
      - qwen2.5-coder-7b-configA.json, qwen2.5-coder-7b-configB.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Phone data points from PocketPal AI (ARM, not architecture-comparable for speed)
PHONE_DATA = [
    {
        "model": "Qwen2.5-3B-Instruct-Q4_K_M",
        "params": "3.09B",
        "file_size_gb": 1.92,
        "config": "phone",
        "threads": "N/A",
        "context": "N/A",
        "kv_cache": "N/A",
        "flash_attn": "N/A",
        "ngl": "N/A",
        "pp_ts": 19.34,
        "tg_ts": 4.51,
        "peak_rss_mb": 2630,
        "source": "PocketPal AI, ARM",
    },
    {
        "model": "Qwen2.5-Coder-7B-Instruct-Q4_K_M",
        "params": "7.62B",
        "file_size_gb": 4.68,
        "config": "phone",
        "threads": "N/A",
        "context": "N/A",
        "kv_cache": "N/A",
        "flash_attn": "N/A",
        "ngl": "N/A",
        "pp_ts": 2.77,
        "tg_ts": 0.78,
        "peak_rss_mb": 5130,
        "source": "PocketPal AI, ARM",
    },
]

MODEL_MAP = {
    "qwen2.5-3b": {
        "display": "Qwen2.5-3B-Instruct-Q4_K_M",
        "params": "3.09B",
        "repo": "bartowski/Qwen2.5-3B-Instruct-GGUF",
        "file": "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
    },
    "qwen2.5-coder-7b": {
        "display": "Qwen2.5-Coder-7B-Instruct-Q4_K_M",
        "params": "7.62B",
        "repo": "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
    },
}

RAM_LIMIT_MB = 7168  # 7 GB ceiling for Seff scoring


def parse_bench_json(data: dict) -> dict:
    """Extract pp/tg rates from llama-bench JSON output array."""
    rows = data.get("bench_output", [])
    pp_rate = 0.0
    tg_rate = 0.0
    for row in rows:
        n_gen = row.get("n_gen", 0)
        n_prompt = row.get("n_prompt", 0)
        avg_ts = row.get("avg_ts", 0.0)
        if n_gen == 0 and n_prompt > 0:
            pp_rate = float(avg_ts)
        elif n_gen > 0:
            tg_rate = float(avg_ts)
    return {"pp_ts": round(pp_rate, 2), "tg_ts": round(tg_rate, 2)}


def peak_rss_mb_from_bench(data: dict) -> float | None:
    """Try to extract peak RSS from bench output if available."""
    # llama-bench JSON rows may contain peak_mem or similar fields
    # For now return None — profiler audit captures this separately
    return None


def main() -> None:
    if len(sys.argv) != 5:
        print(f"usage: {sys.argv[0]} <run_number> <commit_sha> <json_dir> <output_path>")
        sys.exit(1)

    run_number = sys.argv[1]
    commit_sha = sys.argv[2][:7]
    json_dir = Path(sys.argv[3])
    output_path = Path(sys.argv[4])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Read system metadata from first available JSON
    system_info = {}
    for f in sorted(json_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            system_info = data.get("system", {})
            break
        except (json.JSONDecodeError, KeyError):
            continue

    # Build table rows
    rows = []

    # Runner results
    for model_key, model_info in MODEL_MAP.items():
        for config in ("A", "B"):
            fname = f"{model_key}-config{config}.json"
            fpath = json_dir / fname
            if not fpath.exists():
                continue
            data = json.loads(fpath.read_text())
            rates = parse_bench_json(data)
            rss = peak_rss_mb_from_bench(data)
            cache_label = f"{data.get('cache_type_k', '?')}/{data.get('cache_type_v', '?')}"
            fa_label = data.get("flash_attn", "?")
            rss_pct = f"{rss / RAM_LIMIT_MB * 100:.1f}%" if rss else "N/A"
            rows.append({
                "model": model_info["display"],
                "params": model_info["params"],
                "file_size_gb": f"{data.get('file_size_gb', 0):.2f}" if "file_size_gb" in data else "N/A",
                "config": config,
                "threads": data.get("threads", "?"),
                "context": data.get("n_prompt", 512),
                "kv_cache": cache_label,
                "flash_attn": fa_label,
                "ngl": data.get("n_gpu_layers", 0),
                "pp_ts": rates["pp_ts"],
                "tg_ts": rates["tg_ts"],
                "peak_rss_mb": rss if rss else "N/A",
                "peak_rss_pct": rss_pct,
                "source": "runner",
            })

    # Phone reference rows
    for phone in PHONE_DATA:
        rss_pct = f"{phone['peak_rss_mb'] / RAM_LIMIT_MB * 100:.1f}%"
        rows.append({
            "model": phone["model"],
            "params": phone["params"],
            "file_size_gb": f"{phone['file_size_gb']:.2f}",
            "config": phone["config"],
            "threads": phone["threads"],
            "context": phone["context"],
            "kv_cache": phone["kv_cache"],
            "flash_attn": phone["flash_attn"],
            "ngl": phone["ngl"],
            "pp_ts": phone["pp_ts"],
            "tg_ts": phone["tg_ts"],
            "peak_rss_mb": phone["peak_rss_mb"],
            "peak_rss_pct": f"{rss_pct}",
            "source": phone["source"],
        })

    # Render markdown
    cpu = system_info.get("cpu_model", "unknown")
    vcpus = system_info.get("vcpus", "unknown")
    ram = system_info.get("total_ram_mb", "unknown")
    kernel = system_info.get("kernel", "unknown")

    lines = [
        f"# ADTC Benchmark Report — Run {run_number}",
        "",
        f"- **Run**: #{run_number}",
        f"- **Commit**: `{commit_sha}`",
        f"- **Timestamp**: {now}",
        f"- **Runner CPU**: {cpu}",
        f"- **vCPUs**: {vcpus}",
        f"- **Total RAM**: {ram} MB ({ram} / {RAM_LIMIT_MB} MB ceiling)",
        f"- **Kernel**: {kernel}",
        "",
        "## Results",
        "",
        "| Model | Params | File GB | Config | Threads | Context | KV Cache | Flash Attn | GPU Layers | PP t/s | TG t/s | Peak RSS (MB) | Peak RSS (% of 7168 MB) | Source |",
        "|-------|--------|---------|--------|---------|---------|----------|------------|------------|--------|--------|---------------|--------------------------|--------|",
    ]

    for r in rows:
        lines.append(
            f"| {r['model']} | {r['params']} | {r['file_size_gb']} | {r['config']} "
            f"| {r['threads']} | {r['context']} | {r['kv_cache']} | {r['flash_attn']} "
            f"| {r['ngl']} | {r['pp_ts']} | {r['tg_ts']} | {r['peak_rss_mb']} "
            f"| {r['peak_rss_pct']} | {r['source']} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- The runner environment is x86_64 Linux but **not identical** CPU generation to the audit target",
        "  (Intel i5 10th-12th gen). Runner CPUs may differ in microarchitecture, cache sizes, and AVX support.",
        "- **Sperf** in the actual competition is scored relative to other teams' submissions, not against",
        "  these numbers directly. This report is a memory/sanity check and a rough speed baseline,",
        "  not a score prediction.",
        "- **Seff** is absolute against the 7168 MB ceiling — flagged in the Peak RSS column.",
        "- Phone data points (source: PocketPal AI, ARM) are **not architecture-comparable for speed**",
        "  but included for memory reference continuity.",
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
