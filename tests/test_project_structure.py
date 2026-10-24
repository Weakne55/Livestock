"""Structure tests for the modular container-based v0.3 workflow.

The old Conda-only structure tests are intentionally superseded.
"""
import unittest
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


class TestProjectStructure(unittest.TestCase):
    def test_main_snakefile_declares_container(self):
        snake = (ROOT / "workflow/Snakefile").read_text(encoding="utf8")
        self.assertIn("container: IMAGE", snake)
        self.assertNotIn("conda:", snake)

    def test_rules_use_container_not_conda(self):
        for file in (ROOT / "workflow/rules").glob("*.smk"):
            self.assertNotIn("conda:", file.read_text(encoding="utf8"), file.name)

    def test_slurm_profile_uses_apptainer(self):
        profile = yaml.safe_load((ROOT / "profiles/vavilov/config.yaml").read_text(encoding="utf8"))
        self.assertEqual(profile["executor"], "slurm")
        self.assertEqual(profile["software-deployment-method"], ["apptainer"])
        self.assertTrue(profile["slurm-no-account"])
        self.assertEqual(profile["slurm-status-command"], "sacct")

    def test_container_htslib_compatible_mosdepth_pin(self):
        definition = (ROOT / "containers/livestock.def").read_text(encoding="utf8")
        self.assertIn("mosdepth=0.3.14", definition)
        self.assertIn("samtools=1.24", definition)
        self.assertIn("bcftools=1.24", definition)
        self.assertNotIn("mosdepth=0.3.11", definition)

    def test_alignment_limits_distinguish_highcov_and_lowpass(self):
        text = (ROOT / "workflow/rules/alignment.smk").read_text(encoding="utf8")
        self.assertIn("limit('align_highcov_runtime', 1440)", text)
        self.assertIn("limit('align_lowpass_runtime', 360)", text)
        self.assertIn("limit('align_mem_mb_mem2', 56000)", text)
        self.assertIn('threads: 12', text)


if __name__ == "__main__":
    unittest.main()
