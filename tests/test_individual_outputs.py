"""Regression checks: every highcov sample has its own variant-calling DAG and VCF."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workflow' / 'lib'))
from manifest import load_manifest


class TestPerSampleCalling(unittest.TestCase):
    def test_two_highcov_samples_one_species_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'samples.tsv'
            with path.open('w', newline='') as handle:
                writer = csv.writer(handle, delimiter='\t')
                writer.writerow(('sample','species','breed','coverage_type','input_type',
                                 'library','lane','r1','r2','bam','cram'))
                for sample, mode in [('HC_A','highcov'),('HC_B','highcov'),('LP_C','lowpass')]:
                    writer.writerow((sample,'Ovis_aries','Example',mode,'bam',
                                     'LIB1','L001','','',f'/input/{sample}.bam',''))
            _, samples, groups = load_manifest(str(path), {'Ovis_aries': {}}, require_files=False)
            high = [(sp, sid) for (sp, mode), ids in groups.items()
                    if mode == 'highcov' for sid in ids]
            self.assertEqual(high, [('Ovis_aries', 'HC_A'), ('Ovis_aries', 'HC_B')])
            self.assertEqual(len(samples), 3)

        # Test the actual helper from Snakefile using an isolated execution
        # namespace, without requiring a local Snakemake installation.
        src = (ROOT / 'workflow' / 'Snakefile').read_text()
        start = src.index('def high_bam(wc):')
        end = src.index('def low_raw(wc):')
        helper_src = src[start:end]
        ns = {'SAMPLES': samples, 'WORK': '/runs/work',
              'CHROMS': {'Ovis_aries':['NC_1','NC_2']}}
        ns['sample'] = lambda wc: ns['SAMPLES'][wc.sample]
        exec(helper_src, ns)
        wc_a = SimpleNamespace(sample='HC_A', species='Ovis_aries')
        wc_b = SimpleNamespace(sample='HC_B', species='Ovis_aries')
        self.assertEqual(ns['high_bam'](wc_a), '/runs/work/bam/HC_A.bam')
        self.assertEqual(ns['high_raw'](wc_a), [
            '/runs/work/raw_calls/Ovis_aries/highcov/HC_A/NC_1.bcf',
            '/runs/work/raw_calls/Ovis_aries/highcov/HC_A/NC_2.bcf'])
        self.assertNotEqual(ns['high_raw'](wc_a), ns['high_raw'](wc_b))
        with self.assertRaisesRegex(ValueError, 'not highcov'):
            ns['high_bam'](SimpleNamespace(sample='LP_C', species='Ovis_aries'))
        with self.assertRaisesRegex(ValueError, 'not highcov'):
            ns['high_bam'](SimpleNamespace(sample='HC_A', species='Bos_taurus'))

    def test_rules_are_single_sample(self):
        snake = (ROOT / 'workflow' / 'Snakefile').read_text()
        caller = (ROOT / 'workflow' / 'rules' / 'calling_highcov.smk').read_text()
        finish = (ROOT / 'workflow' / 'rules' / 'vcf_processing.smk').read_text()
        report = (ROOT / 'workflow' / 'rules' / 'reporting.smk').read_text()
        check = (ROOT / 'scripts' / 'check_positive_demo.py').read_text()
        self.assertNotIn('high_bams', snake + caller)
        self.assertNotIn('cohort.vcf.gz', snake + caller + finish + report + check)
        self.assertIn('bam=high_bam', caller)
        self.assertIn('highcov/{{sample}}/{{contig}}.bcf', caller)
        self.assertIn('highcov/{{sample}}.vcf.gz', finish)
        self.assertIn('highcov/{{sample}}.stats.txt', finish)
        self.assertIn('highcov/{sid}.stats.txt', report)
        self.assertIn('highcov/{sid}.vcf.gz', snake)
        self.assertIn('f\'{sample}.vcf.gz\'', check)

    def test_lowpass_branch_still_individual(self):
        caller = (ROOT / 'workflow' / 'rules' / 'calling_lowpass.smk').read_text()
        finish = (ROOT / 'workflow' / 'rules' / 'vcf_processing.smk').read_text()
        self.assertIn('lowpass/{{sample}}/{{contig}}.bcf', caller)
        self.assertIn('lowpass/{{sample}}.vcf.gz', finish)


if __name__ == '__main__':
    unittest.main()
