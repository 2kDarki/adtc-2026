#!/usr/bin/env python3
"""render_report.py — builds the committed markdown report.

Merges llama-bench JSON (configA.json / configB.json from run_bench.sh), the
TTFT / reasoning JSON produced by benchmark_llm.py, and system metadata into
`benchmarks/adtc/results-<run>-<sha>.md`.

Usage:
    python render_report.py <run_number> <commit_sha> <json_dir> <output_path>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEFF_CEILING_MB = 7168


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, FileNotFoundError, KeyError):
        return None


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


def short(text: str, limit: int = 50) -> str:
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def fmt(v: Any, default: str = "N/A") -> str:
    return default if v is None else str(v)


def main() -> None:
    if len(sys.argv) != 5:
        print(f"usage: {sys.argv[0]} <run_number> <commit_sha> <json_dir> <output_path>")
        sys.exit(1)

    run_number = sys.argv[1]
    commit_sha = sys.argv[2][:7]
    json_dir = Path(sys.argv[3])
    output_path = Path(sys.argv[4])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    ttft_data = read_json(json_dir / "ttft-results.json")
    if ttft_data is None:
        print("error: ttft-results.json missing or invalid in %s" % json_dir, file=sys.stderr)
        sys.exit(1)

    system = ttft_data.get("system", {}) or {}
    model = ttft_data.get("model", {}) or {}
    memory = ttft_data.get("memory", {}) or {}
    summary = ttft_data.get("summary", {}) or {}
    questions = ttft_data.get("questions", []) or []

    config_rows = []
    for cfg in ("A", "B"):
        data = read_json(json_dir / f"config{cfg}.json")
        if data is None:
            continue
        rates = parse_bench_json(data)
        config_rows.append(
            {
                "config": cfg,
                "threads": data.get("threads", "?"),
                "context": data.get("n_prompt", "?"),
                "kv_cache": f"{data.get('cache_type_k', '?')}/{data.get('cache_type_v', '?')}",
                "flash_attn": data.get("flash_attn", "?"),
                "ngl": data.get("n_gpu_layers", "?"),
                "pp_ts": rates["pp_ts"],
                "tg_ts": rates["tg_ts"],
                "file_size_gb": data.get("file_size_gb", "N/A"),
            }
        )

    peak_rss = memory.get("server_peak_rss_mb")
    peak_pct = f"{peak_rss / SEFF_CEILING_MB * 100:.1f}%" if peak_rss else "N/A"
    if peak_rss is None:
        verdict = "UNKNOWN (peak RSS not sampled)"
    elif peak_rss > SEFF_CEILING_MB:
        verdict = f"FAIL — peak RSS {peak_rss:.0f} MB exceeds {SEFF_CEILING_MB} MB ceiling"
    else:
        verdict = f"PASS — peak RSS {peak_rss:.0f} MB fits within {SEFF_CEILING_MB} MB ceiling"
    enforced = system.get("container_mem_limit_mb")

    lines = [
        f"# ADTC Benchmark Report — Run {run_number}",
        "",
        f"- **Run**: #{run_number}",
        f"- **Commit**: `{commit_sha}`",
        f"- **Timestamp**: {now}",
        f"- **Model**: `{model.get('name', 'unknown')}`",
        f"- **Model repo**: {model.get('repo', 'N/A')}",
        f"- **Model file**: {fmt(model.get('file_size_gb'))} GB",
        f"- **llama.cpp**: {fmt(model.get('server_version'), 'N/A')}",
        f"- **Runner CPU**: {fmt(system.get('cpu_model'), 'unknown')}",
        f"- **vCPUs**: {fmt(system.get('vcpus'), 'unknown')}",
        f"- **Total RAM**: {fmt(system.get('total_ram_mb'), 'unknown')} MB",
        f"- **Container RAM ceiling**: {fmt(enforced, 'unlimited')} MB",
        "",
    ]

    if config_rows:
        lines += [
            "## llama-bench (synthetic harness)",
            "",
            "| Config | Threads | Context | KV Cache | Flash Attn | GPU Layers | PP t/s | TG t/s | File GB |",
            "|--------|---------|---------|----------|------------|------------|--------|--------|----------|",
        ]
        for r in config_rows:
            lines.append(
                f"| {r['config']} | {r['threads']} | {r['context']} | {r['kv_cache']} | {r['flash_attn']} "
                f"| {r['ngl']} | {r['pp_ts']} | {r['tg_ts']} | {r['file_size_gb']} |"
            )
        lines.append("")

    lines += [
        "## TTFT & Decode Speed (live generation)",
        "",
        "| Question | Category | TTFT (s) | Decode (t/s) | Tokens | Answer |",
        "|----------|----------|----------|--------------|--------|--------|",
    ]
    for q in questions:
        answer = short(q.get("answer") or q.get("thinking") or "(no output)", 48)
        if q.get("error"):
            answer = f"ERROR: {q['error'][:48]}"
        lines.append(
            f"| {q.get('id', '?')} | {q.get('category', '?')} | {fmt(q.get('ttft_sec'))} "
            f"| {fmt(q.get('decode_tps'))} | {q.get('tokens', 0)} | {answer} |"
        )
    lines.append(
        f"| **Average** | | {fmt(summary.get('avg_ttft_sec'))} | {fmt(summary.get('avg_decode_tps'))} "
        f"| {summary.get('total_generated_tokens', 0)} total | |"
    )
    lines += [
        "",
        f"Questions answered: {summary.get('questions_ok', 0)}/{summary.get('questions_total', 0)}. "
        f"Total generation time: {fmt(summary.get('total_elapsed_sec'))} s.",
        "",
        "## Memory — 8 GB laptop profile",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Model file size | {fmt(model.get('file_size_gb'))} GB |",
        f"| Server peak RSS (VmHWM) | {fmt(peak_rss, 'N/A')} MB |",
        f"| Seff ceiling | {SEFF_CEILING_MB} MB |",
        f"| Peak RSS % of Seff ceiling | {peak_pct} |",
        f"| Container enforced limit | {fmt(enforced, 'unlimited')} MB |",
        f"| **Verdict** | **{verdict}** |",
        "",
        "## Reasoning outputs",
        "",
    ]
    for i, q in enumerate(questions, start=1):
        lines += [
            f"### {i}. {q.get('id', '?')} — {q.get('category', '?')}",
            "",
            f"**Prompt:** {q['prompt']}",
            "",
        ]
        if q.get("reference"):
            lines += [f"**Reference:** {q['reference']}", ""]
        if q.get("error"):
            lines += [f"**ERROR:** {q['error']}", ""]
        if q.get("thinking"):
            lines += [
                "**Thinking:**",
                "",
                "```text",
                q["thinking"],
                "```",
                "",
            ]
        lines += [
            "**Answer:**",
            "",
            "```text",
            q.get("answer") or "(no output)",
            "```",
            "",
            f"_TTFT {fmt(q.get('ttft_sec'))} s · decode {fmt(q.get('decode_tps'))} t/s · "
            f"{q.get('tokens', 0)} tokens · total {fmt(q.get('total_sec'))} s"
            + (" · truncated" if q.get("truncated") else "")
            + "_\n",
        ]

    lines += [
        "## Notes & Caveats",
        "",
        "- The runner environment is x86_64 Linux but **not identical** to the audit target",
        "  (Intel i5 10th-12th gen). Runner CPUs may differ in microarchitecture, cache sizes,",
        "  and AVX support, so generation speeds (t/s) will vary by ±10-15% across runs.",
        "- The job runs inside a container capped at 4 vCPUs and 8 GB RAM with **no swap**",
        "  (an OOM kill instead of swapping), matching the budget-laptop profile.",
        "- **Seff** is absolute against the 7168 MB ceiling — see the memory section above.",
        "- TTFT is measured to the first generated token, including the start of a",
        "  `<think>` block when the model's thinking mode is active.",
        "- Peak RSS is sampled from `/proc/<pid>/status` (VmHWM). Memory mapped with mmap",
        "  may also sit in the page cache, which is not counted in VmHWM.",
        "- Decode speed includes any thinking tokens. Thread count is fixed at 4 to match",
        "  the 4 vCPU laptop profile.",
        "",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
