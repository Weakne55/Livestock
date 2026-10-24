#!/usr/bin/env python3
"""Fail fast on shared-storage and container configuration."""
import argparse
import os
from pathlib import Path
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--require-image', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    conf = yaml.safe_load(Path(args.config).read_text(encoding='utf8'))
    image = Path(conf.get('container_image', root / 'containers/livestock-0.3.sif')).expanduser()
    if not image.is_absolute():
        image = root / image
    image = image.resolve()
    if args.require_image and (not image.is_file() or image.stat().st_size < 1024):
        raise SystemExit(f'Container missing/too small: {image}')
    for key in ('workdir', 'results_dir', 'reference_cache_dir'):
        if not conf.get(key):
            raise SystemExit(f'Missing {key}')
        value = str(Path(conf[key]).expanduser().resolve())
        if '/USERNAME/' in value or 'GCF_REPLACE_ME' in str(conf['references']):
            raise SystemExit('Replace placeholders in production config')
    paths = [Path(conf[key]).expanduser().resolve() for key in ('workdir', 'results_dir', 'reference_cache_dir')]
    if paths[0] == paths[1]:
        print('WARNING: workdir == results_dir; final outputs are not isolated from scratch')
    if str(paths[2]).startswith('/mnt/hot/'):
        raise SystemExit('Reference cache must NOT reside on /mnt/hot (auto-cleaned)')
    if str(paths[1]).startswith('/mnt/hot/'):
        raise SystemExit('Persistent results_dir must NOT reside on /mnt/hot')
    print(f'IMAGE: {image}')
    print(f'WORK: {paths[0]}')
    print(f'RESULTS: {paths[1]}')
    print(f'CACHE: {paths[2]}')

if __name__ == '__main__':
    main()
