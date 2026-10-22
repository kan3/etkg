import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from scripts.run_ci import report_result


class ResultSummaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / 'results.txt'
        self.summary = Path(self.directory.name) / 'summary.md'
        self.environment = {'GITHUB_STEP_SUMMARY': str(self.summary)}

    def report(self, content, count=1, operation='--key', returncode=0):
        if content is not None:
            self.output.write_text(content, encoding='utf-8')
        with redirect_stdout(io.StringIO()):
            report_result(self.output, count, operation, returncode, self.environment)
        return self.summary.read_text(encoding='utf-8')

    def key_rows(self, content):
        return [line for line in content.splitlines()
                if line.startswith('|') and '<code>' in line]

    def test_multiple_keys_remain_matched_with_their_expiration_dates(self):
        content = self.report(
            'Account Email: first@example.com\n'
            'Account Password: private-first\n'
            'License Name: First fixture\n'
            'License Key: FIRST-KEY\n'
            'License Out Date: 23.11.2026\n\n'
            'Account Email: second@example.com\n'
            'Account Password: private-second\n'
            'License Name: Second fixture\n'
            'License Key: SECOND-KEY\n'
            'License Out Date: 24.11.2026\n', count=2)
        self.assertIn('2 completed out of 2', content)
        rows = self.key_rows(content)
        self.assertEqual(len(rows), 2)
        self.assertIn('<code>FIRST-KEY</code>', rows[0])
        self.assertIn('23.11.2026', rows[0])
        self.assertNotIn('24.11.2026', rows[0])
        self.assertIn('<code>SECOND-KEY</code>', rows[1])
        self.assertIn('24.11.2026', rows[1])
        for private in ('first@example.com', 'second@example.com',
                        'private-first', 'private-second', 'First fixture', 'Second fixture'):
            self.assertNotIn(private, content)

    def test_partial_failure_still_shows_successful_key_and_failure_status(self):
        content = self.report('License Key: SUCCESSFUL-KEY\n'
                              'License Out Date: 23.11.2026\n', count=4, returncode=1)
        self.assertIn('1 completed out of 4', content)
        self.assertIn('script exit code 1', content)
        self.assertIn('<code>SUCCESSFUL-KEY</code>', content)
        self.assertIn('23.11.2026', content)

    def test_small_business_key_is_shown(self):
        content = self.report('License Key: BUSINESS-KEY\n'
                              'License Out Date: 25.11.2026\n',
                              operation='--small-business-key')
        self.assertIn('--small-business-key: 1 completed', content)
        self.assertIn('<code>BUSINESS-KEY</code>', content)

    def test_missing_and_unusable_keys_do_not_create_key_rows(self):
        for fixture in (None, '', 'License Key: \n', 'License Key: None\n',
                        'License Key: null\n', 'Account Email: private@example.com\n'):
            with self.subTest(fixture=fixture):
                if self.summary.exists():
                    self.summary.unlink()
                if self.output.exists():
                    self.output.unlink()
                content = self.report(fixture, returncode=1)
                self.assertIn('0 completed out of 1', content)
                self.assertEqual(self.key_rows(content), [])
                self.assertNotIn('private@example.com', content)

    def test_invalid_record_expiration_is_not_assigned_to_next_valid_key(self):
        content = self.report('License Key: None\n'
                              'License Out Date: 01.01.2000\n\n'
                              'License Key: VALID-KEY\n'
                              'License Out Date: 26.11.2026\n')
        self.assertIn('1 completed out of 1', content)
        rows = self.key_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertIn('VALID-KEY', rows[0])
        self.assertIn('26.11.2026', rows[0])
        self.assertNotIn('01.01.2000', content)

    def test_missing_expiration_does_not_borrow_from_next_key(self):
        content = self.report('License Key: NO-DATE\n\n'
                              'License Key: WITH-DATE\n'
                              'License Out Date: 27.11.2026\n', count=2)
        rows = self.key_rows(content)
        self.assertEqual(len(rows), 2)
        self.assertIn('NO-DATE', rows[0])
        self.assertNotIn('27.11.2026', rows[0])
        self.assertIn('WITH-DATE', rows[1])
        self.assertIn('27.11.2026', rows[1])

    def test_account_mode_reports_count_without_license_or_account_secrets(self):
        content = self.report('Account Email: private@example.com\n'
                              'Account Password: PRIVATE-PASSWORD\n'
                              'License Key: UNRELATED-KEY\n'
                              'License Out Date: 28.11.2026\n', operation='--account')
        self.assertIn('--account: 1 completed out of 1', content)
        self.assertEqual(self.key_rows(content), [])
        for private in ('private@example.com', 'PRIVATE-PASSWORD',
                        'UNRELATED-KEY', '28.11.2026'):
            self.assertNotIn(private, content)

    def test_values_are_trimmed_and_utf8_expiration_is_preserved(self):
        content = self.report('License Key:   TRIMMED-KEY  \n'
                              'License Out Date:   ٢٨ نوفمبر ٢٠٢٦  \n')
        self.assertIn('<code>TRIMMED-KEY</code>', content)
        self.assertIn('<code>٢٨ نوفمبر ٢٠٢٦</code>', content)

    def test_markup_in_output_cannot_create_html_or_extra_table_cells(self):
        content = self.report('License Key: <script>alert(1)</script>&`|KEY\n'
                              'License Out Date: <img src=x onerror=alert(2)>|date\n')
        rows = self.key_rows(content)
        self.assertEqual(len(rows), 1)
        self.assertNotIn('<script>', content)
        self.assertNotIn('<img ', content)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;&amp;', rows[0])
        self.assertIn('&lt;img ', rows[0])
        self.assertIn('&#124;KEY', rows[0])
        self.assertIn('&#124;date', rows[0])
        self.assertEqual(rows[0].count('|'), 3)

    def test_existing_summary_is_preserved(self):
        self.summary.write_text('Existing job information\n', encoding='utf-8')
        content = self.report('License Key: APPENDED-KEY\n')
        self.assertTrue(content.startswith('Existing job information\n'))
        self.assertIn('APPENDED-KEY', content)

    def test_absent_summary_environment_does_not_prevent_reporting(self):
        self.output.write_text('License Key: OUTPUT-KEY\n', encoding='utf-8')
        with redirect_stdout(io.StringIO()) as console:
            report_result(self.output, 1, '--key', 0, {})
        self.assertIn('1 completed out of 1', console.getvalue())
        self.assertFalse(self.summary.exists())


if __name__ == '__main__':
    unittest.main()
