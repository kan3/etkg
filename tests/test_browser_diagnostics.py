import unittest
from unittest.mock import Mock

from modules.BrowserDiagnostics import page_diagnostic


class RedactionTests(unittest.TestCase):
    def test_failure_page_preserves_message_but_redacts_sensitive_patterns(self):
        driver = Mock()
        driver.execute_script.return_value = {
            'text': 'Trial is unavailable. person@example.com ABCD-EFGH-IJKL-MNOP-QRST '
                    '12345678-1234-1234-1234-123456789012 token=private password=private',
            'labels': ['onboarding-trial-help-link'],
        }
        result = page_diagnostic(driver)
        self.assertIn('Trial is unavailable', result)
        for secret in ['person@example.com', 'ABCD-EFGH', '12345678-1234', 'private']:
            self.assertNotIn(secret, result)

    def test_closed_browser_does_not_replace_original_failure(self):
        driver = Mock()
        driver.execute_script.side_effect = RuntimeError('private details')
        self.assertEqual(page_diagnostic(driver), 'Page diagnostics unavailable (RuntimeError)')
