#!/usr/bin/env python3
"""benchmark_llm.py — TTFT, decode-speed and reasoning benchmark against llama-server.

Spawns llama-server (or attaches to an existing one via --server-url) and
streams chat completions over its OpenAI-compatible API. For every question it
records:

  - TTFT        : request start -> first generated token
  - Decode t/s  : (tokens - 1) / time after the first token
  - Token count and output text (thinking and final answer split apart)
  - Peak RSS    : VmHWM of the llama-server process

Writes a JSON record that render_report.py turns into the committed markdown.

Stdlib only (no pip dependencies). Exit 0 on success, 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

RAM_CEILING_MB = 7168

EXTRA_PROMPTS: list[dict[str, str]] = [
    {
        "category": "Multi-Step Logic",
        "prompt": (
            "A train leaves Station A heading East at 60 mph. 30 minutes later, "
            "another train leaves Station A heading East at 80 mph. How many hours "
            "after the second train leaves will it catch up to the first train?"
        ),
    },
    {
        "category": "Mathematical Reasoning",
        "prompt": (
            "If 5 workers can build 5 tables in 5 days, how many days does it take "
            "100 workers to build 100 tables? Explain step-by-step."
        ),
    },
]

SYSTEM_PROMPT = "You are a precise reasoning assistant."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Path to the GGUF model file")
    parser.add_argument("--server-bin", default="llama-server", help="llama-server binary (default: llama-server)")
    parser.add_argument("--server-url", default=None, help="Attach to a running server instead of spawning one")
    parser.add_argument("--output", default="bench-results/ttft-results.json", help="JSON output path")
    parser.add_argument("--model-name", default=None, help="Display name of the model")
    parser.add_argument("--model-repo", default="", help="Hugging Face repo of the model")
    parser.add_argument("--server-version", default="", help="llama.cpp release tag (e.g. b10217)")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ctx", type=int, default=2048)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--ngl", type=int, default=0, help="GPU layers (0 = pure CPU)")
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument(
        "--questions",
        default="benchmarks/suites/reasoning/v1/dataset.json",
        help="Reasoning suite dataset.json (items are used as questions)",
    )
    parser.add_argument("--health-timeout", type=int, default=300, help="Seconds to wait for server readiness")
    return parser.parse_args()


def load_questions(suite_path: str) -> list[dict[str, Any]]:
    """Load reasoning questions from the suite dataset, extra prompts and metadata.json."""
    questions: list[dict[str, Any]] = []
    if suite_path and Path(suite_path).is_file():
        data = json.loads(Path(suite_path).read_text())
        for item in data.get("items", []):
            questions.append(
                {
                    "id": item.get("id", f"q{len(questions) + 1:03d}"),
                    "category": item.get("category", "reasoning"),
                    "prompt": item.get("question", ""),
                    "reference": item.get("expected_answer", ""),
                }
            )
    for i, extra in enumerate(EXTRA_PROMPTS, start=1):
        questions.append(
            {
                "id": f"extra-{i:03d}",
                "category": extra["category"],
                "prompt": extra["prompt"],
                "reference": "",
            }
        )
    meta_path = Path("metadata.json")
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        for tp in meta.get("test_prompts", []):
            questions.append(
                {
                    "id": tp.get("prompt_id", f"tp{len(questions) + 1:03d}"),
                    "category": "test_prompt",
                    "prompt": tp.get("prompt", ""),
                    "reference": "",
                }
            )
    questions = [q for q in questions if q["prompt"].strip()]
    if not questions:
        print("error: no questions found", file=sys.stderr)
        sys.exit(1)
    return questions


def http_get_json(url: str, timeout: float = 30.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def stream_chat_completion(
    url: str, messages: list[dict[str, str]], max_tokens: int, temperature: float
) -> dict[str, Any]:
    """Stream one chat completion, returning timing data and all token chunks."""
    body = json.dumps(
        {"messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "Accept": "text/event-stream"}
    )
    t0 = time.perf_counter()
    first_t: float | None = None
    chunks: list[str] = []
    usage: dict[str, Any] | None = None
    error: str | None = None
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                delta = ((chunk.get("choices") or [{}])[0]).get("delta") or {}
                text = delta.get("content") or delta.get("reasoning_content") or ""
                if not text:
                    continue
                if first_t is None:
                    first_t = time.perf_counter()
                chunks.append(text)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    t_end = time.perf_counter()
    return {"start_t": t0, "first_t": first_t, "end_t": t_end, "chunks": chunks, "usage": usage, "error": error}


def split_think(text: str) -> tuple[str, str]:
    """Split a response into (thinking, answer).

    Qwen3.5 may emit a <think>...</think> block. If none is present the whole
    response is treated as the answer.
    """
    close = text.find("</think>")
    if close == -1:
        return "", text.strip()
    open_tag = text.find("<think>")
    if open_tag == -1:
        return text[:close].strip(), text[close + len("</think>"):].strip()
    thinking = text[open_tag + len("<think>"):close]
    answer = text[close + len("</think>"):]
    return thinking.strip(), answer.strip()


def run_question(base_url: str, q: dict[str, Any], max_tokens: int, temperature: float) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": q["prompt"]},
    ]
    out = stream_chat_completion(base_url + "/v1/chat/completions", messages, max_tokens, temperature)
    text = "".join(out["chunks"])
    tokens = len(out["chunks"])
    if out["usage"] and out["usage"].get("completion_tokens"):
        tokens = int(out["usage"]["completion_tokens"])
    ttft = (out["first_t"] - out["start_t"]) if out["first_t"] is not None else None
    decode = None
    if out["first_t"] is not None and tokens > 1:
        decode_t = out["end_t"] - out["first_t"]
        if decode_t > 0:
            decode = (tokens - 1) / decode_t
    thinking, answer = split_think(text)
    return {
        "id": q["id"],
        "category": q["category"],
        "prompt": q["prompt"],
        "reference": q.get("reference", ""),
        "ttft_sec": round(ttft, 3) if ttft is not None else None,
        "decode_tps": round(decode, 2) if decode is not None else None,
        "tokens": tokens,
        "total_sec": round(out["end_t"] - out["start_t"], 3),
        "truncated": bool(out["error"]) or (tokens >= max_tokens),
        "error": out["error"],
        "thinking": thinking,
        "answer": answer,
    }


def vms_peak_mb(pid: int) -> float | None:
    """Peak resident set size (VmHWM) of a process, in MB."""
    try:
        status = Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return None
    for line in status.splitlines():
        if line.startswith("VmHWM:"):
            return float(line.split()[1]) / 1024.0
    return None


def dump_log(path: str, n_lines: int = 40) -> None:
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return
    print(f"--- llama-server log (last {n_lines} lines) ---", file=sys.stderr)
    for line in lines[-n_lines:]:
        print(line, file=sys.stderr)


def start_server(args: argparse.Namespace) -> tuple[subprocess.Popen, float]:
    """Spawn llama-server and wait until /health reports ready."""
    model_path = Path(args.model)
    if not model_path.is_file():
        print(f"error: model not found at {model_path}", file=sys.stderr)
        sys.exit(1)

    log_path = str(Path(args.output).with_suffix(Path(args.output).suffix + ".server.log"))
    log_file = open(log_path, "w")
    cmd = [
        args.server_bin,
        "-m", str(model_path),
        "--host", "127.0.0.1",
        "--port", str(args.port),
        "--ctx-size", str(args.ctx),
        "--threads", str(args.threads),
        "-ngl", str(args.ngl),
    ]
    print(f"starting: {' '.join(cmd)}")
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)
    base_url = f"http://127.0.0.1:{args.port}"
    deadline = time.monotonic() + args.health_timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            print("error: llama-server exited before becoming ready", file=sys.stderr)
            dump_log(log_path)
            _kill(proc)
            sys.exit(1)
        if http_get_json(base_url + "/health", timeout=5) is not None:
            return proc, time.perf_counter() - t0
        time.sleep(1)
    print(f"error: llama-server not healthy after {args.health_timeout}s", file=sys.stderr)
    dump_log(log_path)
    _kill(proc)
    sys.exit(1)


def _kill(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def system_info() -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        cpu = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=10)
        for line in cpu.stdout.splitlines():
            if line.startswith("Model name:"):
                info["cpu_model"] = line.split(":", 1)[1].strip()
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal"):
                    info["total_ram_mb"] = int(line.split()[1]) // 1024
                    break
    except OSError:
        pass
    info["vcpus"] = os.cpu_count() or 0
    try:
        info["kernel"] = subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()
        info["arch"] = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    try:
        limit = Path("/sys/fs/cgroup/memory.max").read_text().strip()
        if limit != "max":
            info["container_mem_limit_mb"] = int(limit) // (1024 * 1024)
    except OSError:
        pass
    return info


def file_size_gb(path: str) -> float | None:
    try:
        return round(Path(path).stat().st_size / 1073741824, 2)
    except OSError:
        return None


def main() -> int:
    args = parse_args()
    questions = load_questions(args.questions)
    model_name = args.model_name or (Path(args.model).name if args.model else "unknown")

    base_url = args.server_url.rstrip("/") if args.server_url else None
    proc = None
    server_start_sec = None
    if base_url is None:
        proc, server_start_sec = start_server(args)
        base_url = f"http://127.0.0.1:{args.port}"

    try:
        props = http_get_json(base_url + "/props") or {}
        results = []
        for q in questions:
            print(f"[{q['category']}] {q['prompt'][:70].replace(chr(10), ' ')}")
            results.append(run_question(base_url, q, args.max_tokens, args.temperature))

        peak_rss = None
        if proc is not None:
            peak_rss = vms_peak_mb(proc.pid)
        else:
            try:
                out = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True, text=True)
                pids = out.stdout.split()
                if pids:
                    peak_rss = vms_peak_mb(int(pids[0]))
            except Exception:
                pass

        ttfts = [r["ttft_sec"] for r in results if r["ttft_sec"] is not None]
        tpses = [r["decode_tps"] for r in results if r["decode_tps"] is not None]
        summary = {
            "questions_total": len(results),
            "questions_ok": sum(1 for r in results if not r["error"]),
            "avg_ttft_sec": round(sum(ttfts) / len(ttfts), 3) if ttfts else None,
            "avg_decode_tps": round(sum(tpses) / len(tpses), 2) if tpses else None,
            "total_generated_tokens": sum(r["tokens"] for r in results),
            "total_elapsed_sec": round(sum(r["total_sec"] for r in results), 1),
        }

        record = {
            "model": {
                "name": model_name,
                "repo": args.model_repo,
                "file": Path(args.model).name if args.model else None,
                "file_size_gb": file_size_gb(args.model) if args.model else None,
                "server_version": args.server_version,
            },
            "runtime": {
                "backend": "llama.cpp llama-server",
                "ctx": args.ctx,
                "threads": args.threads,
                "ngl": args.ngl,
                "mmap": True,
            },
            "system": system_info(),
            "server": {
                "mode": "attached" if args.server_url else "spawned",
                "start_sec": round(server_start_sec, 2) if server_start_sec is not None else None,
            },
            "props": {
                k: props.get(k)
                for k in ("model_path", "model_name", "arch", "total_params", "n_ctx")
                if props.get(k) is not None
            },
            "memory": {
                "server_peak_rss_mb": round(peak_rss, 1) if peak_rss is not None else None,
                "seff_ceiling_mb": RAM_CEILING_MB,
            },
            "generation": {"max_tokens": args.max_tokens, "temperature": args.temperature},
            "questions": results,
            "summary": summary,
        }

        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2))
        print(f"wrote {out}")
        print(json.dumps(summary))
        return 0
    finally:
        if proc is not None:
            _kill(proc)


if __name__ == "__main__":
    sys.exit(main())
