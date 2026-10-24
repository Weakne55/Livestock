"""Offline structural checks for real ENA config generation and Slurm limits."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, fname):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRealProduction(unittest.TestCase):
    def test_slurm_time_parser(self):
        mod=load_module('check_limits', 'check_slurm_limits.py')
        self.assertEqual(mod.slurm_minutes('1-00:00:00'), 1440)
        self.assertEqual(mod.slurm_minutes('06:00:00'), 360)
        self.assertEqual(mod.slurm_minutes('12:30:01'), 751)
        self.assertEqual(mod.slurm_minutes('60'), 60)
        self.assertGreater(mod.slurm_minutes('INFINITE'), 1000000)

    def test_exclude_sex_chromosomes(self):
        mod=load_module('real_run', 'prepare_ena_real_run.py')
        self.assertEqual(len(mod.CHROMS['Ovis_aries']), 26)
        self.assertEqual(len(mod.CHROMS['Bos_taurus']), 29)
        self.assertNotIn('NC_056080.1', mod.CHROMS['Ovis_aries'])
        self.assertNotIn('NC_037357.1', mod.CHROMS['Bos_taurus'])

    def test_dynamic_resource_definitions(self):
        for f in ('alignment.smk','bam_processing.smk','bam_qc.smk','preprocessing.smk'):
            self.assertIn('limit(', (ROOT/'workflow/rules'/f).read_text(), f)
        main=(ROOT/'workflow/Snakefile').read_text()
        self.assertIn('resource_limits', main)

    def test_real_launch_preflight(self):
        self.assertIn('check_slurm_limits.py', (ROOT/'scripts/run_vavilov.sh').read_text())
        self.assertIn('software-deployment-method', (ROOT/'profiles/vavilov/config.yaml').read_text())


if __name__ == '__main__':
    unittest.main()
