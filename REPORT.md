# Technical Report — Offline Coding Assistant on a Budget Laptop

**Team ID:** your-team-id
**Domain:** coding_assistants
**Model:** Qwen3.5-4B-Q5_K_M

---

## Problem

Many students in African universities and coding bootcamps share a common barrier:
a budget laptop (4 vCPU, 8 GB RAM) with unreliable or expensive internet. Cloud
code assistants (GitHub Copilot, ChatGPT) are unusable in this setting — they
require a persistent connection, and data costs are prohibitive. Students who
want to practice Python, debug homework, or learn algorithms need an assistant
that runs **entirely offline** on the machine they already own.

This submission delivers a local, offline coding tutor: a GGUF-quantized LLM
running through llama.cpp on CPU only, with zero external network calls during
inference. A student types a question — "why does my list comprehension fail?",
"write a function that…" — and gets a step-by-step explanation generated on
their own hardware.

---

## Design Decisions

- **Base model:** Qwen3.5-4B (4B params, instruct-tuned, reasoning mode).
  Chosen after evaluating the template default (SmolLM2-135M), whose output
  quality on multi-step coding questions is too weak for tutoring use.
- **Quantization:** GGUF Q5_K_M via unsloth. This is the sweet spot for the
  8 GB laptop profile:
  - The model file is **2.93 GB**, leaving ample headroom in RAM.
  - Measured server peak RSS is **4866 MB** = 67.9% of the 7168 MB ceiling
    used by the ADTC profiler — safe margin against OOM.
  - Q5_K_M quality is measurably better than Q4_K_M on reasoning-heavy
    prompts, at negligible speed cost (measured: 8.79 t/s vs ~8.8 t/s).
- **Alternatives considered and rejected:**
  - **Q8_0 / 8B Q4_K_M:** file size ~5 GB; projected peak RSS ~6.5–7 GB,
    dangerously close to the 7168 MB ceiling with no swap. Rejected for OOM
    risk.
  - **Q4_K_M of the same model:** slightly smaller, but the quality delta on
    long reasoning chains did not justify the marginal memory saving.
- **Runtime:** llama.cpp (`llama-server`, OpenBLAS build, b10217) — the only
  accepted runtime, fully offline.
- **Inference flags:** 4 threads (matches the 4 vCPU laptop profile), 2048
  token context, 1536 max output tokens (Qwen3.5's reasoning mode is verbose;
  a shorter cap truncated final answers mid-thinking, see Benchmarks).

---

## Constraints

- Target profile: 4 vCPU, **8 GB RAM**, integrated GPU only (no CUDA/Metal
  acceleration — CPU inference only).
- 100% offline during evaluation: the model is served locally by llama.cpp;
  inference makes zero network calls.
- No swap available under the profiler (OOM kills instead of swapping), so
  memory headroom is a hard requirement.
- Benchmark harness runs in a container capped at exactly 4 vCPUs / 8 GB RAM
  with no swap to reproduce the target laptop profile.
- Runner CPU is an AMD EPYC 7763; target laptops (Intel i5 10th–12th gen) may
  differ by ±10–15% in generation speed. Thread count is fixed at 4.

---

## Benchmarks

Measured in the ADTC bench harness (llama.cpp b10217, 4 vCPU / 8 GB RAM
container, no swap, Ubuntu 22.04):

| Metric | Value |
|---|---|
| Machine | 4 vCPU / 8 GB RAM container, AMD EPYC 7763 |
| Model file size | 2.93 GB (Q5_K_M) |
| RAM at peak (VmHWM) | 4949 MB (69.0% of 7168 MB ceiling) |
| Prompt processing (llama-bench) | 11.77 t/s |
| Generation speed (llama-bench) | 8.25–8.42 t/s |
| Time to first token (avg, live) | 3.68 s |
| Generation speed (live, incl. thinking) | 8.05 t/s |
| Reasoning questions answered | 7/7 correct |
| Total generated tokens | 7,343 in ~940 s |

**Why these numbers are acceptable for a tutor:** TTFT ≈ 3.7 s and ~8.5 t/s
feel like a slow chatbot, but for a step-by-step coding tutor this is the
right trade — the model's value is in *correct* explanations, not speed.
Speed is 2–3× the 135M baseline while producing genuinely useful answers.

**Note on token cap:** run 1 used a 768-token output cap; Qwen3.5's reasoning
mode consumed the entire budget mid-thinking and cut off 5 of 7 final
answers. Raised to 1536 tokens — run 5 reports complete answers. This is a
harness parameter, not a model change.

Full methodology, raw outputs, and the reasoning prompt results are in
`benchmarks/adtc/` (`LATEST.md` and `results-*.md`).
