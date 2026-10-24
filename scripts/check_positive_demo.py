#!/usr/bin/env python3
"""Validate highcov *known SNPs* and lowpass PL on the positive fixture.

Examples:
  python scripts/check_positive_demo.py --bcftools .snakemake/conda/<hash>/bin/bcftools
"""
from __future__ import annotations
import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tests' / 'positive_data'
OUT = ROOT / 'tests' / 'positive_results' / 'vcf'


def run(bcftools: str, *args: str) -> str:
    p = subprocess.run([bcftools, *map(str, args)], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError(f"bcftools {' '.join(args)} failed: {p.stderr}")
    return p.stdout


def rows(bcftools: str, vcf: Path):
    fmt = r'%CHROM\t%POS\t%REF\t%ALT[\t%GT\t%PL]\n'
    result = {}
    for line in run(bcftools, 'query', '-f', fmt, str(vcf)).splitlines():
        fields = line.split('\t')
        if len(fields) >= 6:
            chrom, pos, ref, alt, gt, pl = fields[:6]
            result[(chrom, int(pos))] = (ref, alt, gt, pl)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bcftools', default=shutil.which('bcftools'))
    args = p.parse_args()
    if not args.bcftools:
        p.error('Run from SIF with bcftools in PATH or pass --bcftools')
    with (DATA / 'truth.tsv').open() as handle:
        truth = list(csv.DictReader(handle, delimiter='\t'))
    count = 0
    for species, sample in [('Ovis_aries', 'SH_HC'), ('Ovis_aries', 'SH_HC2'), ('Bos_taurus', 'CA_HC')]:
        vcf = OUT / species / 'highcov' / f'{sample}.vcf.gz'
        samples = run(args.bcftools, 'query', '-l', str(vcf)).splitlines()
        assert samples == [sample], f'{vcf}: expected [{sample}], got {samples}'
        observed = rows(args.bcftools, vcf)
        for rec in (r for r in truth if r['species'] == species):
            key = rec['chrom'], int(rec['pos'])
            assert key in observed, f'{vcf}: known SNP {key} missing'
            ref, alts, gt, pl = observed[key]
            assert ref == rec['ref'], f'{key}: reference mismatch {ref} != {rec["ref"]}'
            assert rec['alt'] in alts.split(','), f'{key}: expected ALT {rec["alt"]}, got {alts}'
            # Multiallelic splitting can change allele indexes; our synthetic reads
            # have only one true ALT per position, so GT must be unambiguous.
            assert gt.replace('|', '/') == rec['highcov_gt'], f'{key}: expected {rec["highcov_gt"]}, got {gt}'
            count += 1
            print(f'OK: {sample} {key[0]}:{key[1]} {ref}>{rec["alt"]} GT={gt}')
    vcf = OUT / 'Ovis_aries' / 'lowpass' / 'SH_LP.vcf.gz'
    assert run(args.bcftools, 'query', '-l', str(vcf)).splitlines() == ['SH_LP']
    obs = rows(args.bcftools, vcf)
    actual_pl = [(key, vals[3]) for key, vals in obs.items()
                 if vals[3] not in ('', '.', './.') and any(x.isdigit() for x in vals[3])]
    assert actual_pl, f'No low-pass VCF records with real FORMAT/PL in {vcf}'
    print(f'OK: {len(actual_pl)} lowpass variant records with actual PL values')
    print(f'PASS: {count} known highcov SNP genotypes + lowpass PL')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, RuntimeError, FileNotFoundError) as err:
        sys.exit(f'FAIL: {err}')
