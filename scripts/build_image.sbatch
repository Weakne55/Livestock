#!/usr/bin/env bash
#SBATCH --job-name=livestock-image
#SBATCH --partition=main
#SBATCH --nodelist=vavilov1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=logs/build-image-%j.out
#SBATCH --error=logs/build-image-%j.err
set -Eeuo pipefail
cd "$SLURM_SUBMIT_DIR"
RUNTIME=$(command -v apptainer || command -v singularity || true)
if [[ -z "$RUNTIME" ]]; then echo 'ERROR: apptainer/singularity not found on vavilov1' >&2; exit 2; fi
OUT="$(pwd)/containers/livestock-0.3.sif"
if [[ -e "$OUT" ]]; then echo "ERROR: $OUT exists; do not overwrite an image used by workflows" >&2; exit 3; fi
mkdir -p containers logs
TMPBASE="/mnt/hot/$USER/livestock_build"
mkdir -p "$TMPBASE"
export APPTAINER_TMPDIR="$TMPBASE"
export SINGULARITY_TMPDIR="$TMPBASE"
export APPTAINER_CACHEDIR="$TMPBASE/cache"
export SINGULARITY_CACHEDIR="$TMPBASE/cache"
mkdir -p "$APPTAINER_CACHEDIR"
"$RUNTIME" build --fakeroot "$OUT" containers/livestock.def
"$RUNTIME" exec --cleanenv "$OUT" bash -c 'for x in bwa bwa-mem2 samtools bcftools fastp mosdepth multiqc; do command -v "$x" || exit 1; done'
sha256sum "$OUT" > "$OUT.sha256"
echo "IMAGE_READY $OUT"
