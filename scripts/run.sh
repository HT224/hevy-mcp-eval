#!/usr/bin/env bash
# Run the full 5-system × 13-prompt × 3-epoch eval matrix.
# Each system is launched as a separate Inspect run so logs are
# per-system in logs/<timestamp>_hevy-eval_<runid>.eval.

set -euo pipefail

MODEL="${MODEL:-anthropic/claude-sonnet-4-6}"
EPOCHS="${EPOCHS:-3}"

SYSTEMS=(chrisdoc meimakes thin baseline_csv baseline_nodata)

# Filter via SYSTEMS env var if provided: SYSTEMS="thin baseline_csv" ./scripts/run.sh
if [ -n "${SYSTEMS_OVERRIDE:-}" ]; then
    read -ra SYSTEMS <<< "$SYSTEMS_OVERRIDE"
fi

echo "Running ${#SYSTEMS[@]} systems × 13 prompts × $EPOCHS epochs on $MODEL"
echo

for sys in "${SYSTEMS[@]}"; do
    echo "============================================="
    echo "  system: $sys"
    echo "============================================="
    uv run inspect eval evals/run.py \
        -T system="$sys" \
        --model "$MODEL" \
        --epochs "$EPOCHS" \
        --log-dir logs/
done
