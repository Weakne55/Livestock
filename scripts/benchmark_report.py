#!/usr/bin/env python3
"""Offline benchmark summary from an existing Snakemake run, no computations launched."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import median


def read_benchmarks(root: Path) -> list[tuple[str, str, float, float | None]]:
    out = []
    for p in root.rglob('*.tsv'):
        try:
            with p.open(newline='', encoding='utf8') as f:
                row = next(csv.DictReader(f, delimiter='\t'), None)
            if not row or not row.get('s'):
                continue
            seconds = float(row['s'])
            ram = float(row['max_rss']) if row.get('max_rss') else None
            relative = p.relative_to(root)
            out.append((relative.parts[0], str(relative), seconds, ram))
        except (OSError, ValueError, IndexError, StopIteration):
            continue
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-id', default='real_sif_20261022')
    ap.add_argument('--results-dir', type=Path)
    ap.add_argument('--top', type=int, default=15)
    args = ap.parse_args()
    root = (args.results_dir or Path.home() / 'livestock_results' / args.run_id) / 'benchmarks'
    if not root.is_dir():
        ap.error(f'benchmark directory not found: {root}')
    rows = read_benchmarks(root)
    if not rows:
        ap.error('no benchmark rows found')
    groups = defaultdict(list)
    for group, filename, seconds, ram in rows:
        groups[group].append((seconds, ram))
    print(f'Benchmark directory: {root}')
    print(f'Valid completed benchmarks: {len(rows)}')
    print('\nBy stage (minutes):')
    print(f'{"Stage":<18} {"N":>4} {"Median":>10} {"Max":>10} {"Sum":>12}')
    for key in sorted(groups):
        values = [s/60 for s, _ in groups[key]]
        print(f'{key:<18} {len(values):>4} {median(values):>10.1f} {max(values):>10.1f} {sum(values):>12.1f}')
    print('\nLongest individual jobs:')
    print(f'{"Minutes":>9} {"RSS GB":>9}  Benchmark file')
    for group, filename, seconds, ram in sorted(rows, key=lambda x:x[2], reverse=True)[:max(0,args.top)]:
        rss = f'{ram/1024:.2f}' if ram is not None else '-'
        print(f'{seconds/60:>9.1f} {rss:>9}  {filename}')
    print('\nNOTE: Sum = aggregate individual task walltimes, NOT end-to-end walltime.')
    print('NOTE: max_rss is Snakemake benchmark RSS; Slurm step accounting may differ.')


if __name__ == '__main__':
    main()
