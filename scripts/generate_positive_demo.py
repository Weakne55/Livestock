#!/usr/bin/env python3
"""Generate a deterministic *positive* WGS/lpWGS integration fixture.

Requires only PyYAML (already installed in the Snakemake manager environment).
Outputs are separate from the original tests/data and tests/results.
The low-pass fixture is deliberately spiked near the two known SNP positions:
this tests the VCF/PL route, NOT the accuracy of low-pass genotyping.
"""
from __future__ import annotations

import csv
import gzip
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "positive_data"
CONFIG = ROOT / "config" / "demo_positive.yaml"
DATA.mkdir(parents=True, exist_ok=True)

SEQ_LEN = 10_000
READ_LEN = 150
INSERT_LEN = 360
TARGETS = (3200, 6100)  # 1-based VCF positions
COMPLEMENT = str.maketrans("ACGT", "TGCA")


def revcomp(s: str) -> str:
    return s.translate(COMPLEMENT)[::-1]


def alternative(ref: str) -> str:
    return "ACGT"[("ACGT".index(ref) + 1) % 4]


def fastq_pairs(sample: str, ref: str, seed: int, lowpass: bool) -> None:
    rng = random.Random(seed)
    # A normal whole-reference random sample, plus artificially enriched sites
    # in the lowpass fixture to test variant emission and FORMAT/PL propagation.
    fragments: list[tuple[int, int]] = []
    n = 50 if lowpass else 1600
    for i in range(n):
        fragments.append((rng.randrange(0, SEQ_LEN - INSERT_LEN), i % 2))
    if lowpass:
        for k, position in enumerate(TARGETS):
            for i in range(14):
                start = (position - 1) - 65 - i
                # The second locus is homozygous ALT; at the first, alternate
                # haplotypes provide both REF and ALT observations.
                fragments.append((start, i % 2))
    p1 = DATA / f"{sample}_R1.fastq.gz"
    p2 = DATA / f"{sample}_R2.fastq.gz"
    with gzip.open(p1, "wt", compresslevel=6) as out1, gzip.open(p2, "wt", compresslevel=6) as out2:
        for i, (start, hap) in enumerate(fragments):
            chunk = list(ref[start:start + INSERT_LEN])
            for site, het in ((TARGETS[0], True), (TARGETS[1], False)):
                offset = (site - 1) - start
                if 0 <= offset < INSERT_LEN and (not het or hap == 1):
                    chunk[offset] = alternative(ref[site - 1])
            fragment = "".join(chunk)
            r1 = fragment[:READ_LEN]
            r2 = revcomp(fragment[-READ_LEN:])
            key = f"{sample}_{i:05d}"
            out1.write(f"@{key}/1\n{r1}\n+\n{'I' * READ_LEN}\n")
            out2.write(f"@{key}/2\n{r2}\n+\n{'I' * READ_LEN}\n")
    print(f"  {sample}: {len(fragments)} read pairs -> {p1.name}, {p2.name}")


rows = [
    ("SH_HC", "Ovis_aries", "Askanian", "highcov", 5041),
    ("SH_HC2", "Ovis_aries", "Askanian", "highcov", 5045),
    ("SH_LP", "Ovis_aries", "Tsigai", "lowpass", 5042),
    ("CA_HC", "Bos_taurus", "Kalmyk", "highcov", 9041),
]
refs = {}
truth = []

for index, (species, chrom) in enumerate((
    ("Ovis_aries", "TEST_OVIS_1"),
    ("Bos_taurus", "TEST_BOS_1"),
)):
    rng = random.Random(10101 + index)
    sequence = "".join(rng.choices("ACGT", k=SEQ_LEN))
    fasta = DATA / f"{species}.fa"
    with fasta.open("w") as handle:
        handle.write(f">{chrom}\n")
        for start in range(0, len(sequence), 80):
            handle.write(sequence[start:start + 80] + "\n")
    refs[species] = {
        "assembly": "SYNTHETIC_POSITIVE_TEST_ONLY",
        "fasta": str(fasta.resolve()),
        "contigs": [chrom],
    }
    for pos in TARGETS:
        truth.append((species, chrom, pos, sequence[pos - 1], alternative(sequence[pos - 1]),
                      "0/1" if pos == TARGETS[0] else "1/1"))
    for sample, sp, breed, cov, seed in rows:
        if sp == species:
            fastq_pairs(sample, sequence, seed, cov == "lowpass")

with (DATA / "samples.tsv").open("w", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t")
    writer.writerow(["sample", "species", "breed", "coverage_type", "input_type",
                     "library", "lane", "r1", "r2", "bam", "cram"])
    for sample, species, breed, cov, _ in rows:
        writer.writerow([sample, species, breed, cov, "fastq", "LIB1", "L001",
                         str((DATA / f"{sample}_R1.fastq.gz").resolve()),
                         str((DATA / f"{sample}_R2.fastq.gz").resolve()), "", ""])

with (DATA / "metadata.tsv").open("w", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t")
    writer.writerow(["sample", "species", "breed"])
    for sample, species, breed, _, _ in rows:
        writer.writerow([sample, species, breed])

with (DATA / "truth.tsv").open("w", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t")
    writer.writerow(["species", "chrom", "pos", "ref", "alt", "highcov_gt"])
    writer.writerows(truth)

config = {
    "samples": str((DATA / "samples.tsv").resolve()),
    "metadata": str((DATA / "metadata.tsv").resolve()),
    "workdir": str((ROOT / "tests" / "positive_results").resolve()),
    "results_dir": str((ROOT / "tests" / "positive_results").resolve()),
    "reference_cache_dir": str((ROOT / "tests" / "positive_results" / "ref_cache").resolve()),
    "container_image": str(ROOT / "containers/livestock-0.3.sif"),
    "references": refs,
    "variant_calling": {
        "min_mapq": 20,
        "min_baseq": 20,
        "max_depth_per_bam": 10000,
        "highcov_min_qual": 10,
    },
}
CONFIG.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
print(f"Created: {CONFIG}")
print(f"Truth:   {DATA / 'truth.tsv'}")
