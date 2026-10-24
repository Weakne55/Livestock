#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
image="${1:-containers/livestock-0.3.sif}"
command -v apptainer >/dev/null 2>&1 && runtime=apptainer || runtime=singularity
command -v "$runtime" >/dev/null 2>&1 || { echo 'No Singularity/Apptainer available' >&2; exit 1; }
[[ -s "$image" ]] || { echo "Image not found: $image" >&2; exit 1; }
"$runtime" exec --cleanenv "$image" bash -c '
 set -Eeuo pipefail
 for x in bwa bwa-mem2 samtools bcftools fastp mosdepth multiqc python; do command -v "$x"; done
 bcftools --version | head -1
 samtools --version | head -1
 bwa-mem2 version 2>&1 | head -5 || true
'
if [[ -f "$image.sha256" ]]; then (cd "$(dirname "$image")" && sha256sum -c "$(basename "$image").sha256"); fi
