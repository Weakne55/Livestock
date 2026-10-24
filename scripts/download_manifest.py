#!/usr/bin/env python3
"""Fetch ENA FASTQs and NCBI .fna.gz reproducibly on a SLURM compute node.

Input TSV: accession, url, path, md5 (md5 may be empty for NCBI reference;
then NCBI's md5checksums.txt is retrieved and verified).
"""
from __future__ import annotations
import csv
import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import urllib.request


def digest(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ncbi_md5(url: str) -> str:
    # FTP archive reference checksum is a directory-level file.
    folder, name = url.rsplit('/', 1)
    with urllib.request.urlopen(folder + '/md5checksums.txt', timeout=120) as handle:
        for line in handle:
            words = line.decode('utf8').strip().split()
            if len(words) >= 2 and words[-1].lstrip('./') == name:
                return words[0].lower()
    raise ValueError(f'NCBI md5checksums.txt has no checksum for {name}')


def fetch(url: str, target: Path, expected: str):
    if not url.startswith('https://'):
        raise ValueError(f'Only HTTPS downloads are supported: {url}')
    if not expected:
        if 'ftp.ncbi.nlm.nih.gov/genomes/all/' not in url:
            raise ValueError(f'Missing MD5 for non-NCBI file: {url}')
        expected = ncbi_md5(url)
    expected = expected.lower()
    if not (len(expected) == 32 and all(c in '0123456789abcdef' for c in expected)):
        raise ValueError('Expected checksum must be MD5 hex')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and digest(target) == expected:
        print(f'REUSE {target}', flush=True)
    else:
        if target.exists():
            raise ValueError(f'Corrupted final file: {target}; inspect before retry')
        part = Path(str(target) + '.part')
        print(f'DOWNLOAD {url} -> {target}', flush=True)
        subprocess.run(['curl','--fail','--location','--retry','20',
                        '--retry-delay','30','--connect-timeout','60',
                        '--continue-at','-','--output',str(part),url], check=True)
        actual = digest(part)
        if actual != expected:
            raise ValueError(f'MD5 mismatch {part}: {actual}, expected {expected}')
        part.replace(target)
        print(f'VERIFIED {target}', flush=True)
    if target.name.endswith('.fna.gz'):
        fasta = target.with_suffix('')
        # Do not decompress twice; persistent reference cache will subsequently
        # copy and index this FASTA exactly once per assembly.
        if not fasta.is_file():
            tmp = Path(str(fasta)+'.part')
            print(f'UNPACK {target} -> {fasta}', flush=True)
            with gzip.open(target,'rb') as src, tmp.open('wb') as dest:
                while True:
                    block=src.read(8*1024*1024)
                    if not block: break
                    dest.write(block)
            tmp.replace(fasta)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: download_manifest.py config/downloads.tsv')
    path = Path(sys.argv[1])
    with path.open(newline='', encoding='utf8') as fh:
        rows = list(csv.DictReader(fh, delimiter='\t'))
    if not rows:
        raise ValueError('Empty downloads manifest')
    for item in rows:
        dest = Path(os.path.expandvars(os.path.expanduser(item['path'])))
        if not dest.is_absolute():
            raise ValueError(f'Download path must be absolute: {dest}')
        fetch(item['url'], dest, item.get('md5','').strip())
    print(f'DONE: {len(rows)} verified downloads', flush=True)

if __name__ == '__main__': main()
