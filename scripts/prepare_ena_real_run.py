#!/usr/bin/env python3
"""Create a NEW Singularity run using the verified 2026-10-20 ENA data.

No downloads, no FASTQ/FASTA rewriting, and no changes to existing results.
The reference-group key Bos_taurus is NOT a claim that SRR5507199 is Bos taurus:
ENA metadata identifies this run as Bos indicus.
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROWS = (
    ('SHEEP_LP_SRR2976536', 'Ovis_aries', 'Unverified', 'lowpass', 'SRR2976536', 'Ovis aries'),
    ('SHEEP_HC_SRR10822538', 'Ovis_aries', 'Unverified', 'highcov', 'SRR10822538', 'Ovis aries'),
    ('CATTLE_HC_SRR5507199', 'Bos_taurus', 'Wannan', 'highcov', 'SRR5507199', 'Bos indicus'),
)
ASSEMBLIES = {'Ovis_aries': 'GCF_016772045.1', 'Bos_taurus': 'GCF_002263795.1'}
# RefSeq ARS-UI_Ramb_v2.0: 26 autosomes; ARS-UCD1.2: 29 autosomes.
# Exclude X to avoid assigning diploid ploidy to males without sex metadata.
CHROMS = {
    'Ovis_aries': [f'NC_{n:06d}.1' for n in range(56054, 56080)],
    'Bos_taurus': [f'NC_{n:06d}.1' for n in range(37328, 37357)],
}


def write_tsv(path, columns, rows):
    with path.open('w', newline='', encoding='utf8') as handle:
        writer = csv.DictWriter(handle, delimiter='\t', fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-id', default='real_sif_20261022',
                    help='Unique ID: creates a separate workdir/results_dir')
    ap.add_argument('--aligner', choices=['bwa', 'bwa-mem2'], default='bwa-mem2')
    ap.add_argument('--scratch-root', default=f'/mnt/hot/{os.environ.get("USER", Path.home().name)}/livestock_real_20261020',
                    help='Existing 2026-10-20 raw/ and references/ directory')
    ap.add_argument('--reference-cache', default=str(Path.home() / 'livestock_references'))
    ap.add_argument('--force-config', action='store_true',
                    help='Overwrite only generated YAML/TSV files, NOT results or source reads')
    args = ap.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', args.run_id):
        ap.error('--run-id may contain letters, digits, underscores, dashes only')

    source = Path(args.scratch_root).expanduser().resolve()
    reference_paths = {
        species: source / 'references' / species / f'{assembly}_genomic.fna'
        for species, assembly in ASSEMBLIES.items()
    }
    expected_files = list(reference_paths.values())
    for _, _, _, _, run, _ in ROWS:
        for mate in (1, 2):
            expected_files.append(source / 'raw' / f'{run}_{mate}.fastq.gz')
    missing = [str(p) for p in expected_files if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise SystemExit('Missing/empty already-downloaded input files (no downloads attempted):\n' + '\n'.join(missing))

    confdir = ROOT / 'config'
    confdir.mkdir(exist_ok=True)
    cfgpath = confdir / f'{args.run_id}.yaml'
    samples = confdir / f'{args.run_id}_samples.tsv'
    metadata = confdir / f'{args.run_id}_metadata.tsv'
    for path in (cfgpath, samples, metadata):
        if path.exists() and not args.force_config:
            raise SystemExit(f'Refusing to overwrite: {path}; use a new --run-id')

    sample_rows, meta_rows = [], []
    for sample, species, breed, mode, run, reported in ROWS:
        sample_rows.append(dict(sample=sample, species=species, breed=breed, coverage_type=mode,
                                input_type='fastq', library=run, lane='L001',
                                r1=str(source / 'raw' / f'{run}_1.fastq.gz'),
                                r2=str(source / 'raw' / f'{run}_2.fastq.gz'), bam='', cram=''))
        meta_rows.append(dict(sample=sample, species=species, breed=breed, ENA_run=run,
                              reported_scientific_name=reported, reference_group=species))

    # All large inputs are *reused*, never rewritten or linked to the old workdir.
    results = (Path.home() / 'livestock_results' / args.run_id).resolve()
    work = (Path('/mnt/hot') / os.environ.get('USER', Path.home().name) / args.run_id / 'work').resolve()
    cache = Path(args.reference_cache).expanduser().resolve()
    if results.exists() or work.exists():
        raise SystemExit(f'Run output already exists, pick another --run-id:\nwork={work}\nresults={results}')
    image = (ROOT / 'containers' / 'livestock-0.3.sif').resolve()
    if not image.is_file():
        raise SystemExit(f'No built Singularity image: {image}')
    cfg = {
        'samples': str(samples.resolve()), 'metadata': str(metadata.resolve()),
        'container_image': str(image), 'workdir': str(work),
        'results_dir': str(results), 'reference_cache_dir': str(cache),
        'aligner': args.aligner,
        # Keep trimmed FASTQ and per-lane BAM during first production validation.
        # After successful completion, explicit manual cleanup is possible.
        'keep_trimmed_fastq': True, 'keep_lane_bam': True,
        'references': {
            sp: {'assembly': asm, 'fasta': str(reference_paths[sp]), 'contigs': CHROMS[sp]}
            for sp, asm in ASSEMBLIES.items()
        },
        'variant_calling': {'min_mapq': 20, 'min_baseq': 20,
                            'max_depth_per_bam': 10000, 'highcov_min_qual': 30},
        # Slurm runtime is a walltime ceiling, not expected processing duration.
        'resource_limits': {
            'align_mem_mb_mem2': 56000, 'align_mem_mb_bwa': 24000,
            'align_highcov_runtime': 1440, 'align_lowpass_runtime': 360,
            'mem2_index_mem_mb': 60000, 'mem2_index_runtime': 720,
            'canonical_mem_mb': 24000, 'canonical_highcov_runtime': 1440,
            'canonical_lowpass_runtime': 360,
            'bam_qc_mem_mb': 12000, 'bam_qc_highcov_runtime': 720,
            'bam_qc_lowpass_runtime': 360,
            'fastp_mem_mb': 32000, 'fastp_highcov_runtime': 240,
            'fastp_lowpass_runtime': 120,
            'call_highcov_mem_mb': 16000, 'call_highcov_runtime': 900,
            'call_lowpass_mem_mb': 8000, 'call_lowpass_runtime': 480,
        },
    }
    write_tsv(samples, ['sample','species','breed','coverage_type','input_type','library','lane','r1','r2','bam','cram'], sample_rows)
    write_tsv(metadata, ['sample','species','breed','ENA_run','reported_scientific_name','reference_group'], meta_rows)
    cfgpath.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding='utf8')
    print('READY:', cfgpath)
    print('Input FASTQ and references are reused from:', source)
    print('NEW workdir:', work)
    print('NEW results_dir:', results)
    print('Reference cache:', cache)
    print('Autosomes only: sheep=26, cattle=29; sex chromosomes excluded')
    print('NOTICE: SRR5507199 reported as Bos indicus; aligned to Bos taurus reference as a pilot cross-subspecies test')


if __name__ == '__main__':
    main()
