"""Regression checks for the optional performance profile and safe config cloning."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class TestPerformanceProfile(unittest.TestCase):
    def test_profile(self):
        config = yaml.safe_load((ROOT/'profiles/vavilov-fast/config.yaml').read_text())
        self.assertEqual(config['jobs'], 8)
        self.assertEqual(config['resources']['mem_mb'], 96000)
        self.assertEqual(config['set-resource-scopes']['mem_mb'], 'global')
        self.assertEqual(config['default-resources']['slurm_account'], 'users')
        self.assertNotIn('/mnt/databases', config['apptainer-args'])
        self.assertEqual(config['software-deployment-method'], ['apptainer'])
        self.assertEqual(config['default-resources']['slurm_extra'], '--nodelist=vavilov1')

    def test_new_run_does_not_change_existing_config(self):
        spec = importlib.util.spec_from_file_location('perf', ROOT/'scripts/prepare_perf_run.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        original = dict(samples='config/samples.tsv', references={'Ovis_aries':{'fasta':'/raw/ref.fna'}},
                        reference_cache_dir='/refs', container_image='/image.sif',
                        workdir='/old/work', results_dir='/old/results',
                        resource_limits={'align_highcov_runtime': 1440, 'fastp_mem_mb': 32000},
                        keep_trimmed_fastq=True, keep_lane_bam=True)
        new = mod.performance_config(original, 'bench_123', 'tester', Path('/home/tester'))
        self.assertEqual(original['resource_limits']['fastp_mem_mb'], 32000)
        self.assertEqual(new['resource_limits']['fastp_mem_mb'], 6000)
        self.assertEqual(new['resource_limits']['align_highcov_runtime'], 1440)
        self.assertEqual(new['workdir'], '/mnt/hot/tester/bench_123/work')
        self.assertEqual(new['results_dir'], '/home/tester/livestock_results/bench_123')
        self.assertFalse(new['keep_trimmed_fastq'])
        self.assertFalse(new['keep_lane_bam'])
        self.assertTrue(original['keep_lane_bam'])
        self.assertEqual(new['references'], original['references'])
        self.assertEqual(new['samples'], original['samples'])
        self.assertEqual(new['reference_cache_dir'], original['reference_cache_dir'])
        with self.assertRaises(ValueError):
            mod.performance_config(original, '../bad', 'tester', Path('/home/tester'))

    def test_runner_can_select_profile_without_changing_default(self):
        runner = (ROOT/'scripts/run_vavilov.sh').read_text()
        self.assertIn('${LIVESTOCK_PROFILE:-profiles/vavilov}', runner)
        self.assertIn('check_slurm_limits.py', runner)

    def test_benchmark_report_sample(self):
        spec = importlib.util.spec_from_file_location('report', ROOT/'scripts/benchmark_report.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'alignment'/'x.tsv'
            p.parent.mkdir(parents=True)
            p.write_text('s\tmax_rss\n600\t1024\n')
            row = mod.read_benchmarks(Path(d))
        self.assertEqual(row, [('alignment','alignment/x.tsv',600.0,1024.0)])


if __name__ == '__main__':
    unittest.main()
