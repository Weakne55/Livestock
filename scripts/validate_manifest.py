#!/usr/bin/env python3
"""Preflight checks, no calls to cluster tools; run before the Snakemake dry-run."""
import argparse
import csv
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workflow' / 'lib'))
from manifest import load_manifest, verify_references


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config/config.yaml')
    ap.add_argument('--allow-missing-inputs', action='store_true', help='Only for demonstration')
    ap.add_argument('--lightweight', action='store_true', help='Check presence without scanning multi-GB reference FASTAs on login node')
    a = ap.parse_args()
    cfg = yaml.safe_load(Path(a.config).read_text(encoding='utf8'))
    if not isinstance(cfg, dict):
        raise ValueError('Config must contain a YAML mapping')
    if not cfg.get('workdir'):
        raise ValueError('workdir must be defined in config')
    refs = cfg['references']
    verify_references(refs, require_files=not (a.allow_missing_inputs or a.lightweight))
    if a.lightweight and not a.allow_missing_inputs:
        for species, entry in refs.items():
            source = Path(entry['fasta'])
            if not source.is_file() or source.stat().st_size == 0:
                raise ValueError(f'Reference not found or empty: {source}')
    units, samples, groups = load_manifest(cfg['samples'], refs, require_files=not a.allow_missing_inputs)
    meta = Path(cfg.get('metadata', ''))
    if not meta.is_file():
        raise ValueError(f'Metadata file not found: {meta}')
    if meta.is_file():
        with meta.open(newline='', encoding='utf8') as h:
            rows = list(csv.DictReader(h, delimiter='\t'))
        ids = [r['sample'] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('metadata.tsv has duplicate sample rows')
        for row in rows:
            if row['sample'] in samples and (row['species'], row['breed']) != (samples[row['sample']].species, samples[row['sample']].breed):
                raise ValueError(f"Metadata disagree with manifest: {row['sample']}")
        if set(samples) - set(ids):
            raise ValueError(f"Missing metadata for: {sorted(set(samples) - set(ids))}")
    print(f'OK: {len(samples)} samples, {len(units)} sequencing units')
    for (species, mode), ids in sorted(groups.items()):
        print(f'  {species} / {mode}: {len(ids)} samples; reference {refs[species]["fasta"]}')
    print('Prealigned BAM/CRAM headers are checked at execution time by check_alignment.py')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        sys.exit(f'PREFLIGHT ERROR: {exc}')
