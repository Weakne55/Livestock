#!/usr/bin/env python3
"""Check required Snakemake per-job walltimes against real Slurm partition MaxTime.

This cannot guarantee that a job finishes before its time limit, but prevents
an invalid --time request that Slurm would reject. No cluster jobs are started.
"""
from __future__ import annotations

import argparse
from math import inf
from pathlib import Path
import re
import subprocess
import yaml


def slurm_minutes(raw):
    value = raw.strip().upper()
    if value in ('INFINITE', 'UNLIMITED'):
        return inf
    if value in ('NOT_SET', 'N/A', 'NONE'):
        raise ValueError(f'Unknown MaxTime={raw}; check partition manually')
    days = 0
    if '-' in value:
        d, value = value.split('-', 1)
        days = int(d)
    fields = value.split(':')
    if len(fields) == 3:
        hours, minutes, seconds = map(int, fields)
    elif len(fields) == 2:
        minutes, seconds = map(int, fields)
        hours = 0
    elif len(fields) == 1:
        minutes = int(fields[0])
        seconds = hours = 0
    else:
        raise ValueError(raw)
    return 1440 * days + 60 * hours + minutes + (seconds > 0)


def required_walltimes(config):
    """Largest configured times for rules that can appear in a real run."""
    limits = config.get('resource_limits', {})
    def get(k, default):
        return int(limits.get(k, default))
    baseline = {
        'prepare_reference': get('prepare_ref_runtime', 180),
        'index_reference': get('mem2_index_runtime', 720) if config.get('aligner','bwa') == 'bwa-mem2' else get('bwa_index_runtime', 480),
        'highcov_call': get('call_highcov_runtime', 900),
        'lowpass_call': get('call_lowpass_runtime', 480),
        'final_vcf': get('final_vcf_runtime', 360),
    }
    modes = set()
    import csv
    with Path(config['samples']).open(newline='', encoding='utf8') as h:
        for row in csv.DictReader(h, delimiter='\t'):
            modes.add(row['coverage_type'])
    if 'highcov' in modes:
        baseline.update(align_highcov=get('align_highcov_runtime', 1440),
                        canonical_highcov=get('canonical_highcov_runtime', 1440),
                        qc_highcov=get('bam_qc_highcov_runtime', 720),
                        fastp_highcov=get('fastp_highcov_runtime', 240))
    if 'lowpass' in modes:
        baseline.update(align_lowpass=get('align_lowpass_runtime', 360),
                        canonical_lowpass=get('canonical_lowpass_runtime', 360),
                        qc_lowpass=get('bam_qc_lowpass_runtime', 360),
                        fastp_lowpass=get('fastp_lowpass_runtime', 120))
    return baseline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--partition', default='main')
    args = ap.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding='utf8'))
    result = subprocess.run(['scontrol','show','partition',args.partition], text=True,
                            capture_output=True, check=True)
    matched = re.search(r'\bMaxTime=(\S+)', result.stdout)
    if not matched:
        raise SystemExit('Could not read MaxTime; inspect `scontrol show partition main`')
    mx = slurm_minutes(matched.group(1))
    requested = required_walltimes(config)
    longest = max(requested.values())
    print('Slurm partition:', args.partition)
    print('MaxTime:', matched.group(1))
    print('Largest pipeline request:', longest, 'minutes')
    overs = [(rule,n) for rule,n in requested.items() if n > mx]
    if overs:
        text = '\n'.join(f'  {rule}: {minutes} min' for rule, minutes in overs)
        raise SystemExit('ERROR: requested time exceeds partition MaxTime:\n'+text+'\n'
                         'Use a partition with sufficient MaxTime or a genuinely faster/chunked workflow. '
                         'Lowering --time without reducing work will reproduce TIMEOUT.')
    print('PASS: requested walltimes do not exceed partition MaxTime')


if __name__ == '__main__':
    main()
