#!/usr/bin/env bash
# Usage: bash scripts/launch_vavilov.sh config/production.yaml
set -Eeuo pipefail
[[ "$#" -eq 1 ]] || { echo 'Usage: scripts/launch_vavilov.sh config/run.yaml' >&2; exit 2; }
[[ -z "${SLURM_JOB_ID:-}" ]] || { echo 'Launch from vavilov0, NOT from inside Slurm' >&2; exit 2; }
cd "$(dirname "$0")/.."
config=$(realpath "$1")
mkdir -p logs
stamp=$(date -u +%Y%m%dT%H%M%SZ)
log="logs/controller-${stamp}.log"
nohup bash scripts/run_vavilov.sh "$config" > "$log" 2>&1 < /dev/null &
pid=$!
printf 'Controller PID: %s\nLog: %s\n' "$pid" "$log"
