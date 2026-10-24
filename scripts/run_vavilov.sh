#!/usr/bin/env bash
# Controller on login node only. Compute-heavy rules submitted to Slurm.
set -Eeuo pipefail
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  echo 'Do NOT run Snakemake controller inside sbatch or srun.' >&2; exit 2
fi
cd "$(dirname "$0")/.."
[[ "$#" -eq 1 ]] || { echo 'Usage: scripts/run_vavilov.sh config/run.yaml' >&2; exit 2; }
CONFIG=$(realpath "$1")
[[ -s "$CONFIG" ]] || { echo "Missing config: $CONFIG" >&2; exit 1; }
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate livestock-snakemake
mkdir -p logs
# Unique workspace lock via Snakemake plus one manager per repository
exec 9>logs/vavilov-controller.lock
flock -n 9 || { echo 'Another manager for this repository is running.' >&2; exit 3; }
python scripts/validate_manifest.py --config "$CONFIG" --lightweight
python scripts/check_config.py --config "$CONFIG" --require-image
python scripts/check_slurm_limits.py --config "$CONFIG" --partition main
exec snakemake \
  -s workflow/Snakefile \
  --configfile "$CONFIG" \
  --profile "${LIVESTOCK_PROFILE:-profiles/vavilov}"
