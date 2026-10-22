"""Catch the workflow regressions introduced by overwriting this fork."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ForkWorkflowTests(unittest.TestCase):
    def test_generation_requires_manual_dispatch(self):
        workflow = (ROOT / '.github/workflows/eset.yml').read_text()
        self.assertRegex(workflow, r'(?m)^  workflow_dispatch:')
        self.assertNotRegex(workflow, r'(?m)^  (?:schedule|push|pull_request):')

    def test_generation_runs_the_selected_fork_checkout(self):
        workflow = (ROOT / '.github/workflows/eset.yml').read_text()
        self.assertIn('actions/checkout@', workflow)
        self.assertIn('python scripts/run_ci.py', workflow)
        self.assertNotRegex(workflow, r'(?im)\bgit\s+clone\b')
        self.assertNotRegex(workflow, r'(?m)^\s+(?:repository|ref):')
        run_block = workflow.split('      - name: Run script\n', 1)[-1]
        # Dispatch values belong in the environment, not interpolated shell code.
        self.assertRegex(run_block, r'(?m)^        env:')
        self.assertRegex(run_block, r'(?m)^        run: python scripts/run_ci\.py$')

    def test_routine_tests_do_not_create_accounts_or_commit_timestamps(self):
        workflow = (ROOT / '.github/workflows/test.yml').read_text()
        self.assertIn('python -m unittest discover', workflow)
        self.assertNotRegex(workflow, r'(?m)^  schedule:')
        self.assertNotRegex(workflow, r'(?i)\b(?:main\.py|scripts/run_ci\.py)\b')
        self.assertNotRegex(workflow, r'(?i)\bgit\s+(?:clone|commit|push)\b')

    def test_workflows_do_not_reintroduce_deprecated_checkout_runtime(self):
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            with self.subTest(workflow=path.name):
                self.assertNotRegex(path.read_text(), r'actions/checkout@v[1-4]\b')


if __name__ == '__main__':
    unittest.main()
