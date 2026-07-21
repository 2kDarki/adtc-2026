# ADTC Benchmark Report — Run 1

- **Run**: #1
- **Commit**: `6a1ac9f`
- **Timestamp**: 2026-07-21 21:00:26 UTC
- **Runner CPU**: unknown
- **vCPUs**: unknown
- **Total RAM**: unknown MB (unknown / 7168 MB ceiling)
- **Kernel**: unknown

## Results

| Model | Params | File GB | Config | Threads | Context | KV Cache | Flash Attn | GPU Layers | PP t/s | TG t/s | Peak RSS (MB) | Peak RSS (% of 7168 MB) | Source |
|-------|--------|---------|--------|---------|---------|----------|------------|------------|--------|--------|---------------|--------------------------|--------|
| Qwen2.5-3B-Instruct-Q4_K_M | 3.09B | 1.79 | A | 4 | 512 | f16/f16 | off | 0 | 28.45 | 16.82 | N/A | N/A | runner |
| Qwen2.5-3B-Instruct-Q4_K_M | 3.09B | 1.79 | B | 4 | 512 | q8_0/q8_0 | on | 0 | 28.2 | 16.97 | N/A | N/A | runner |
| Qwen2.5-Coder-7B-Instruct-Q4_K_M | 7.62B | 4.36 | A | 4 | 512 | f16/f16 | off | 0 | 12.68 | 7.55 | N/A | N/A | runner |
| Qwen2.5-Coder-7B-Instruct-Q4_K_M | 7.62B | 4.36 | B | 4 | 512 | q8_0/q8_0 | on | 0 | 12.48 | 7.68 | N/A | N/A | runner |
| Qwen2.5-3B-Instruct-Q4_K_M | 3.09B | 1.92 | phone | N/A | N/A | N/A | N/A | N/A | 19.34 | 4.51 | 2630 | 36.7% | PocketPal AI, ARM |
| Qwen2.5-Coder-7B-Instruct-Q4_K_M | 7.62B | 4.68 | phone | N/A | N/A | N/A | N/A | N/A | 2.77 | 0.78 | 5130 | 71.6% | PocketPal AI, ARM |

## Notes

- The runner environment is x86_64 Linux but **not identical** CPU generation to the audit target
  (Intel i5 10th-12th gen). Runner CPUs may differ in microarchitecture, cache sizes, and AVX support.
- **Sperf** in the actual competition is scored relative to other teams' submissions, not against
  these numbers directly. This report is a memory/sanity check and a rough speed baseline,
  not a score prediction.
- **Seff** is absolute against the 7168 MB ceiling — flagged in the Peak RSS column.
- Phone data points (source: PocketPal AI, ARM) are **not architecture-comparable for speed**
  but included for memory reference continuity.
