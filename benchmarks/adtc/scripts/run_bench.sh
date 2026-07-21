#!/usr/bin/env bash
# run_bench.sh — wraps llama-bench invocation, emits JSON
#
# Usage:
#   ./run_bench.sh <model_path> <config> <output_path>
#
#   config: "A" (phone-parity) or "B" (submission-intended)
#
# Outputs a JSON file with benchmark results + system metadata.

set -euo pipefail

MODEL_PATH="${1:?usage: run_bench.sh <model_path> <config> <output_path>}"
CONFIG="${2:?usage: run_bench.sh <model_path> <config> <output_path>}"
OUTPUT_PATH="${3:?usage: run_bench.sh <model_path> <config> <output_path>}"

THREADS="$(nproc)"

# Config A: phone-parity (f16 cache, flash-attn off)
# Config B: submission-intended (q8_0 cache, flash-attn on)
case "$CONFIG" in
  A)
    CACHE_TYPE_K="f16"
    CACHE_TYPE_V="f16"
    FLASH_ATTN="off"
    ;;
  B)
    CACHE_TYPE_K="q8_0"
    CACHE_TYPE_V="q8_0"
    FLASH_ATTN="on"
    ;;
  *)
    echo "error: config must be A or B, got: $CONFIG" >&2
    exit 1
    ;;
esac

LLAMA_BENCH="${LLAMA_BENCH:-llama-bench}"

if ! command -v "$LLAMA_BENCH" &>/dev/null; then
  echo "error: llama-bench not found on PATH (set LLAMA_BENCH env var)" >&2
  exit 1
fi

echo "running llama-bench: config=$CONFIG threads=$THREADS cache=$CACHE_TYPE_K/$CACHE_TYPE_V flash_attn=$FLASH_ATTN"

# Run llama-bench with JSON output
BENCH_JSON=$("$LLAMA_BENCH" \
  -m "$MODEL_PATH" \
  -p 512 \
  -n 128 \
  -t "$THREADS" \
  -ngl 0 \
  -ctk "$CACHE_TYPE_K" \
  -ctv "$CACHE_TYPE_V" \
  -fa "$FLASH_ATTN" \
  -r 3 \
  -o json)

# Capture exit code
BENCH_RC=$?

if [ $BENCH_RC -ne 0 ]; then
  echo "error: llama-bench exited with code $BENCH_RC" >&2
  exit $BENCH_RC
fi

# Collect system metadata
CPU_MODEL=$(lscpu | awk -F: '/Model name/ {gsub(/^[ \t]+/, "", $2); print $2}')
VCPUS=$(nproc)
TOTAL_RAM_KB=$(awk '/^MemTotal/ {print $2}' /proc/meminfo)
TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))
KERNEL=$(uname -r)
ARCH=$(uname -m)

# Build output JSON
cat > "$OUTPUT_PATH" <<ENDJSON
{
  "config": "$CONFIG",
  "model_path": "$MODEL_PATH",
  "cache_type_k": "$CACHE_TYPE_K",
  "cache_type_v": "$CACHE_TYPE_V",
  "flash_attn": "$FLASH_ATTN",
  "threads": $THREADS,
  "n_gpu_layers": 0,
  "n_prompt": 512,
  "n_gen": 128,
  "repetitions": 3,
  "system": {
    "cpu_model": "$CPU_MODEL",
    "vcpus": $VCPUS,
    "total_ram_mb": $TOTAL_RAM_MB,
    "kernel": "$KERNEL",
    "arch": "$ARCH"
  },
  "bench_output": $BENCH_JSON
}
ENDJSON

echo "wrote $OUTPUT_PATH"
