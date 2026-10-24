#!/usr/bin/env bash
#SBATCH --job-name=livestock_downloads
#SBATCH --partition=main
#SBATCH --nodelist=vavilov1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/downloads-%j.out
set -Eeuo pipefail
cd "$SLURM_SUBMIT_DIR"
python scripts/download_manifest.py "${1:-config/downloads.example.tsv}"
