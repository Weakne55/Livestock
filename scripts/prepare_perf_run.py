#!/usr/bin/env python3
"""Build a NEW performance-only YAML run from an already completed run.

Reuse raw inputs and reference cache, keep scientific parameters unchanged,
write to distinct work/results directories, do not modify the source config.
Test-derived memory limits are only validated for the three-sample pilot.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import os
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
PILOT_LIMITS = {
    'align_mem_mb_mem2': 32000, # measured WGS peak: 19.8 GB
    'canonical_mem_mb': 12000, # measured peak: 5.0 GB
    'fastp_mem_mb': 6000, # measured peak: 1.5 GB
    'bam_qc_mem_mb': 8000, # measured peak: 2.4 GB
    'call_highcov_mem_mb': 4000, # 1 highcov sample per species in pilot
    'call_lowpass_mem_mb': 4000,
}


def performance_config(source: dict, run_id: str, user: str, home: Path) -> dict:
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*', run_id):
        raise ValueError('run-id accepts letters, numbers, _ and - only')
    if not user or '/' in user:
        raise ValueError('invalid user')
    config = deepcopy(source)
    needed = ('samples', 'references', 'reference_cache_dir', 'container_image')
    missing = [k for k in needed if k not in config]
    if missing:
        raise ValueError('source run configuration missing: ' + ', '.join(missing))
    config['workdir'] = str(Path('/mnt/hot') / user / run_id / 'work')
    config['results_dir'] = str(home / 'livestock_results' / run_id)
    # Temp intermediate files are removed by Snakemake after downstream success.
    # The input FASTQs, cached references, and final BAM/VCF/QC are not temp.
    config['keep_trimmed_fastq'] = False
    config['keep_lane_bam'] = False
    limits = dict(config.get('resource_limits', {}))
    limits.update(PILOT_LIMITS)
    config['resource_limits'] = limits
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Existing run YAML configuration')
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        parser.error(f'not found: {source}')
    old = yaml.safe_load(source.read_text(encoding='utf8'))
    if not isinstance(old, dict):
        parser.error(f'config is not a YAML mapping: {source}')
    new = performance_config(old, args.run_id, os.environ.get('USER') or Path.home().name, Path.home())
    target = ROOT / 'config' / f'{args.run_id}.yaml'
    # Avoid overwriting, including other runs' outputs.
    for kind, p in [('new config', target), ('work directory', Path(new['workdir'])),
                    ('results directory', Path(new['results_dir']))]:
        if p.exists():
            parser.error(f'{kind} already exists: {p}; choose a new --run-id')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Atomic no-clobber creation: no replacement even if a name appears meanwhile.
    with target.open('x', encoding='utf8') as f:
        yaml.safe_dump(new, f, allow_unicode=True, sort_keys=False)
    print('CREATED:', target)
    print('SOURCE (unchanged):', source)
    print('WORK:', new['workdir'])
    print('RESULTS:', new['results_dir'])
    print('PROFILE: profiles/vavilov-fast')
    print('NO downloads; same source reads and references.')
    print('WARNING: memory tuning is calibrated only for 3 pilot samples; not for large cohorts.')


if __name__ == '__main__':
    main()
