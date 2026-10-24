#!/usr/bin/env python3
"""Validate chromosome names against the indexed reference on the compute node."""
import sys
from pathlib import Path

def main():
    fai=Path(sys.argv[1]); expected=sys.argv[2:]
    names=[]
    with fai.open() as fh:
        for line in fh:
            names.append(line.split('\t',1)[0])
    missing=set(expected)-set(names)
    if missing: raise SystemExit(f'Missing contigs in {fai}: {sorted(missing)}')
    if [name for name in names if name in set(expected)] != expected:
        raise SystemExit('Configured contig order differs from FASTA order')
    print(f'OK: {len(expected)} configured contigs in reference')

if __name__=='__main__': main()
