#!/usr/bin/env bash
# FastQ branch: stream collate -> fixmate -> coordinate-sort -> markdup.
# BAM/CRAM branch: check supplied alignment; do not silently re-mark duplicates.
set -Eeuo pipefail
mode=$1; reference=$2; sample=$3; threads=$4; output=$5; shift 5
if [ "$#" -eq 0 ]; then echo 'No alignment files provided' >&2; exit 1; fi
if [ "$threads" -lt 4 ]; then echo 'canonical_bam requires >=4 allocated CPUs' >&2; exit 1; fi
mkdir -p "$(dirname "$output")"
tmp=$(mktemp -d "$(dirname "$output")/.${sample}.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT

if [[ "$mode" == fastq ]]; then
  # -@ controls auxiliary threads; these programs run concurrently in the pipe.
  # Keep the total comfortably below threads=8 (one main thread per process too).
  finish() {
    samtools fixmate -m -u -@ 1 - - \
      | samtools sort -u -@ 2 -m 768M -T "$tmp/sort" - \
      | samtools markdup -@ 1 - "$output"
  }
  if [[ "$#" -eq 1 ]]; then
    samtools collate -u -O -@ 1 "$1" "$tmp/collate" | finish
  else
    # Merge preserves distinct RG records from lanes/libraries. Collate removes
    # the need for a global name sort, regardless of input record order.
    samtools merge -u -@ 1 - "$@" \
      | samtools collate -u -O -@ 1 - "$tmp/collate" \
      | finish
  fi
elif [[ "$mode" == bam || "$mode" == cram ]]; then
  if [[ "$#" -ne 1 ]]; then echo 'Aligned input requires exactly one file per sample' >&2; exit 1; fi
  python scripts/check_alignment.py "$1" "$sample" "$reference"
  samtools view -@ 2 -T "$reference" -b -o "$output" "$1"
else
  echo "Unknown input mode: $mode" >&2; exit 1
fi
samtools quickcheck -v "$output"
samtools index -@ 2 "$output"
