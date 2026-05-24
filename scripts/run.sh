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

FAILED=()
for sys in "${SYSTEMS[@]}"; do
    echo "============================================="
    echo "  system: $sys"
    echo "  started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================="
    if uv run inspect eval evals/run.py \
        -T system="$sys" \
        --model "$MODEL" \
        --epochs "$EPOCHS" \
        --log-dir logs/; then
        echo "  ✓ $sys complete"
    else
        rc=$?
        echo "  ✗ $sys failed with exit $rc — continuing"
        FAILED+=("$sys")
    fi
done

echo
echo "============================================="
echo "  matrix done"
echo "============================================="
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "FAILED systems: ${FAILED[*]}"
    exit 1
else
    echo "all systems completed"
fi
