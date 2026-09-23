import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from modules.SharedTools import untilConditionExecute
from modules.EsetTools import EsetKeygen
from scripts.run_ci import report_result


class DiagnosticTests(unittest.TestCase):
    def test_wait_reports_observed_controls_without_claiming_ip_block(self):
        driver = Mock(title='ESET HOME')
        driver.execute_script.side_effect = [None, None, False, ['onboarding-other-option']]
        with self.assertRaisesRegex(RuntimeError, 'trial option') as error:
            untilConditionExecute(driver, 'return false', max_iter=1, delay=0,
                                  description='trial option')
        self.assertIn('onboarding-other-option', str(error.exception))
        self.assertNotIn('TRY VPN', str(error.exception))

    def test_small_business_waits_for_its_own_card(self):
        keygen = EsetKeygen(Mock(), Mock(), 'SMALL BUSINESS')
        with patch('modules.EsetTools.untilConditionExecute', side_effect=[True, True, RuntimeError('stop')]) as wait, \
             patch.object(keygen, '_EsetKeygen__press_button_with_text'), \
             patch('modules.EsetTools.console_log'):
            with self.assertRaisesRegex(RuntimeError, 'stop'):
                keygen.sendRequestForKey()
        self.assertIn('card-172', wait.call_args.args[1])
        self.assertNotIn('card-148', wait.call_args.args[1])

    def test_partial_result_summary_does_not_expose_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'keys.txt'
            summary = Path(directory) / 'summary.md'
            output.write_text('Account Email: private@example.com\nLicense Key: SECRET-FIXTURE\n')
            report_result(output, 4, '--key', 1, {'GITHUB_STEP_SUMMARY': str(summary)})
            content = summary.read_text()
            self.assertIn('1 completed out of 4', content)
            self.assertNotIn('SECRET', content)
            self.assertNotIn('private@example.com', content)
