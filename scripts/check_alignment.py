#!/usr/bin/env python3
"""Reject incompatible reference builds, unsorted inputs and misleading RG sample labels."""
import subprocess
import sys
from pathlib import Path

def check(path, sample, reference):
    p = subprocess.run(['samtools','view','-H','-T',reference,path], text=True, capture_output=True, check=True)
    names = set()
    head_sort = None
    lengths = {}
    ref_lengths = {}
    with open(reference + '.fai', encoding='utf8') as handle:
        for line in handle:
            parts = line.split('\t')
            ref_lengths[parts[0]] = int(parts[1])
    for line in p.stdout.splitlines():
        cols = line.split('\t')
        if line.startswith('@HD'):
            head_sort = next((x[3:] for x in cols if x.startswith('SO:')), None)
        if line.startswith('@RG'):
            names.update(x[3:] for x in cols if x.startswith('SM:'))
        if line.startswith('@SQ'):
            sn = next((x[3:] for x in cols if x.startswith('SN:')), None)
            ln = next((int(x[3:]) for x in cols if x.startswith('LN:')), None)
            if sn:
                lengths[sn] = ln
    if head_sort != 'coordinate':
        raise ValueError(f'{path}: header requires @HD SO:coordinate (got {head_sort})')
    if names != {sample}:
        raise ValueError(f'{path}: @RG SM must equal {sample!r}, got {sorted(names)}; repair RG before import')
    if not lengths or any(n not in ref_lengths or ref_lengths[n] != l for n, l in lengths.items()):
        raise ValueError(f'{path}: @SQ chromosome names/lengths differ from configured reference')

if __name__ == '__main__':
    try:
        check(*sys.argv[1:4])
    except Exception as exc:
        sys.exit(f'ERROR: {exc}')
