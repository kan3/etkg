import importlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import run_ci
from modules.EmailAPIs import EmailFakeAPI, PARSE_EMAILFAKE_INBOX
from selenium.common.exceptions import TimeoutException


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = patch.object(run_ci, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    @patch.object(run_ci.subprocess, 'run')
    def test_failed_script_is_not_reported_as_success(self, execute):
        execute.return_value.returncode = 7
        self.assertEqual(run_ci.run({}), 7)

    @patch.object(run_ci.subprocess, 'run')
    def test_missing_output_fails_even_if_script_exits_zero(self, execute):
        execute.return_value.returncode = 0
        with self.assertRaisesRegex(RuntimeError, 'produced no'):
            run_ci.run({})

    @patch.object(run_ci.subprocess, 'run')
    def test_success_requires_nonempty_output(self, execute):
        def write_output(*args, **kwargs):
            (self.root / 'keys.txt').write_text('fixture result')
            return Mock(returncode=0)
        execute.side_effect = write_output
        self.assertEqual(run_ci.run({}), 0)

    @patch.object(run_ci.subprocess, 'run')
    def test_rejects_invalid_counts_before_execution(self, execute):
        for count in ['-1', 'abc', '1; echo injected']:
            with self.subTest(count=count), self.assertRaises(ValueError):
                run_ci.run({'KEY_COUNT': count})
        execute.assert_not_called()

    @patch.object(run_ci.subprocess, 'run')
    def test_mail_only_never_runs_main(self, execute):
        execute.return_value.returncode = 1
        self.assertEqual(run_ci.run({'MAIL_ONLY': 'true'}), 1)
        self.assertTrue(execute.call_args.args[0][1].endswith('check_mail.py'))
        execute.assert_called_once()


class MailTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for the DOM fixture')
    def test_current_clickable_rows_and_empty_inboxes(self):
        fixture = r'''
const parse = new Function('document', PARSER);
const doc = rows => ({getElementById: () => ({children: rows})});
const row = {tagName: 'DIV', hasAttribute: name => name === 'onclick',
    children: [{innerText: 'sender@example.com'}, {innerText: 'Test message'}]};
if (parse(doc([])).length !== 0) throw Error('Empty inbox must be valid');
if (parse({getElementById: () => null}).length !== 0) throw Error('Missing table');
const result = parse(doc([row]));
if (result[0][0] !== row || result[0][1] !== 'sender@example.com' ||
    result[0][2] !== 'Test message') throw Error('Clickable row lost');
'''.replace('PARSER', json.dumps(PARSE_EMAILFAKE_INBOX))
        subprocess.run(['node', '-e', fixture], check=True, capture_output=True, text=True)

    def test_clickable_message_uses_its_click_handler(self):
        driver, row = Mock(), Mock()
        api = EmailFakeAPI(driver)
        api.open_mail(row)
        row.click.assert_called_once()
        driver.get.assert_not_called()
        self.assertTrue(api.opened_mail)

    def test_empty_address_or_placeholder_is_not_success(self):
        driver = Mock()
        driver.find_element.return_value.text = 'Creating...'
        driver.current_url = 'https://emailfake.com/'
        driver.title = 'Verification required'
        api = EmailFakeAPI(driver)
        with patch('modules.EmailAPIs.WebDriverWait') as wait:
            def timeout(condition):
                self.assertFalse(condition(driver))
                raise TimeoutException()
            wait.return_value.until.side_effect = timeout
            with self.assertRaisesRegex(RuntimeError, 'Verification required'):
                api.init()
        self.assertIsNone(api.email)

    def test_valid_address_is_read_without_reloading(self):
        driver = Mock()
        driver.find_element.return_value.text = ' test@example.com '
        api = EmailFakeAPI(driver)
        api.init()
        self.assertEqual(api.email, 'test@example.com')
        driver.get.assert_called_once()

    def test_inbox_does_not_reload_on_every_poll(self):
        driver = Mock()
        driver.execute_script.return_value = []
        api = EmailFakeAPI(driver)
        self.assertEqual(api.parse_inbox(), [])
        self.assertEqual(api.parse_inbox(), [])
        driver.get.assert_called_once()
        api.opened_mail = True
        api.parse_inbox()
        self.assertEqual(driver.get.call_count, 2)


class MainFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch('sys.argv', ['main.py', '--disable-logging']):
            cls.app = importlib.import_module('main')

    def test_mail_exception_preserves_cause_and_fails(self):
        app = self.app
        args = dict(app.ARGS_DEFAULT, skip_update_check=True,
                    skip_webdriver_menu=True, email_api='emailfake')
        driver = Mock()
        mail = Mock(email=None)
        mail.init.side_effect = RuntimeError('provider unavailable')
        with patch.object(app, 'args', args), \
             patch.object(app, 'MBCI_MODE', False), \
             patch.object(app, 'PROXIES', []), \
             patch.object(app.logging, 'critical'), \
             patch.object(app, 'WebDriverInstaller') as installer, \
             patch.object(app, 'initSeleniumWebDriver', return_value=driver), \
             patch.dict(app.EMAIL_API_CLASSES, {'emailfake': Mock(return_value=mail)}), \
             patch.object(app, 'console_log') as output:
            installer.return_value.detect_installed_browser.return_value = None
            self.assertEqual(app.main(disable_exit=True), 1)
            self.assertIn('provider unavailable', str(output.call_args_list))
        driver.quit.assert_called_once()
        self.assertIsNone(app.DRIVER)

    def test_browser_start_failure_exits_nonzero(self):
        app = self.app
        args = dict(app.ARGS_DEFAULT, skip_update_check=True,
                    skip_webdriver_menu=True)
        with patch.object(app, 'args', args), \
             patch.object(app, 'MBCI_MODE', False), \
             patch.object(app, 'PROXIES', []), \
             patch.object(app.logging, 'critical'), \
             patch.object(app, 'WebDriverInstaller') as installer, \
             patch.object(app, 'initSeleniumWebDriver', side_effect=RuntimeError('browser failed')), \
             patch.object(app, 'console_log'):
            installer.return_value.detect_installed_browser.return_value = None
            with self.assertRaises(SystemExit) as error:
                app.main()
            self.assertEqual(error.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
