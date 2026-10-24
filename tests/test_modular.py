import re
import unittest
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
MODULES=['reference','preprocessing','alignment','bam_processing','bam_qc','calling_highcov','calling_lowpass','vcf_processing','reporting']
class TestModular(unittest.TestCase):
    def test_includes(self):
        snake=(ROOT/'workflow/Snakefile').read_text()
        self.assertIn('container: IMAGE',snake)
        self.assertIn('rule all:',snake)
        for name in MODULES:
            self.assertIn(f'include: "rules/{name}.smk"',snake)
            self.assertTrue((ROOT/f'workflow/rules/{name}.smk').is_file())
    def test_rules_unique(self):
        alltext='\n'.join(p.read_text() for p in (ROOT/'workflow/rules').glob('*.smk'))
        names=re.findall(r'^\s*rule ([a-z_]+):',alltext,re.M)
        self.assertEqual(len(names)-len(set(names)), 1)  # index_reference has two mutually exclusive aligner implementations
        self.assertEqual(names.count('index_reference'), 2)
        self.assertGreaterEqual(len(names),13)
        self.assertNotIn('conda:',alltext)
    def test_profile(self):
        profile=yaml.safe_load((ROOT/'profiles/vavilov/config.yaml').read_text())
        self.assertEqual(profile['executor'],'slurm')
        self.assertEqual(profile['software-deployment-method'],['apptainer'])
        self.assertTrue(profile['slurm-no-account'])
        self.assertEqual(profile['slurm-status-command'],'sacct')
    def test_image(self):
        defi=(ROOT/'containers/livestock.def').read_text()
        for tool in ['bwa-mem2','fastp','samtools','bcftools','mosdepth','multiqc']:
            self.assertIn(tool,defi)
    def test_run_controller(self):
        ctrl=(ROOT/'scripts/run_vavilov.sh').read_text()
        self.assertIn('SLURM_JOB_ID',ctrl)
        self.assertIn('--profile "${LIVESTOCK_PROFILE:-profiles/vavilov}"',ctrl)
if __name__=='__main__':unittest.main()
