import os
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workflow/lib'))
from manifest import load_manifest, verify_references

HEAD = 'sample\tspecies\tbreed\tcoverage_type\tinput_type\tlibrary\tlane\tr1\tr2\tbam\tcram\n'
REF = {'Ovis_aries': {'assembly': 'GCF_TEST1', 'fasta': '/fake/ref.fa', 'contigs': ['chr1']},
       'Bos_taurus': {'assembly': 'GCF_TEST2', 'fasta': '/fake/other.fa', 'contigs': ['chr1']}}

def row(s='S1', sp='Ovis_aries', cov='highcov', kind='fastq', lib='L1', lane='001'):
    p = ('r1.fq.gz', 'r2.fq.gz', '', '') if kind == 'fastq' else ('', '', 'x.bam' if kind == 'bam' else '', 'x.cram' if kind == 'cram' else '')
    return '\t'.join([s,sp,'Breed',cov,kind,lib,lane,*p]) + '\n'

class TestManifest(unittest.TestCase):
    def read(self, body):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'sample.tsv'
            p.write_text(HEAD + body)
            return load_manifest(str(p), REF)

    def test_multiple_lanes_one_sample(self):
        units, samples, groups = self.read(row() + row(lane='002'))
        self.assertEqual(len(units), 2)
        self.assertEqual(len(samples), 1)
        self.assertEqual(groups[('Ovis_aries','highcov')], ['S1'])

    def test_multi_species(self):
        _, samples, groups = self.read(row() + row(s='B1',sp='Bos_taurus',cov='lowpass'))
        self.assertEqual(len(samples), 2)
        self.assertEqual(len(groups), 2)

    def test_reject_mixing_modes(self):
        with self.assertRaisesRegex(ValueError, 'contradictory'):
            self.read(row() + row(cov='lowpass',lane='002'))

    def test_reject_duplicate_units(self):
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            self.read(row() + row())

    def test_reject_multi_bam(self):
        with self.assertRaisesRegex(ValueError, 'one file per sample'):
            self.read(row(kind='bam') + row(kind='bam',lane='002'))

    def test_reject_incomplete_fastq(self):
        with self.assertRaises(ValueError):
            self.read(row().replace('r2.fq.gz',''))

    def test_reject_multi_library(self):
        with self.assertRaisesRegex(ValueError, 'multiple independent libraries'):
            self.read(row() + row(lib='L2', lane='002'))

    def test_reference(self):
        verify_references(REF)

if __name__ == '__main__':
    unittest.main()
