import unittest
from unittest.mock import Mock, patch
from modules.EsetTools import EsetRegister


class RegistrationTests(unittest.TestCase):
    def run_registration(self, visible_text):
        driver = Mock()
        driver.page_source = 'hidden: This email address is already registered'
        def script(source):
            if source == 'return document.title':
                return 'Register'
            if source == 'return document.URL':
                return 'https://login.eset.com/Register'
            if 'document.body.innerText' in source:
                return visible_text
            return Mock(text='Ukraine')
        driver.execute_script.side_effect = script
        api = Mock(email='fixture@example.com')
        with patch('modules.EsetTools.untilConditionExecute', return_value=True), \
             patch('modules.EsetTools.time.sleep'), \
             patch('modules.EsetTools.DEFAULT_MAX_ITER', 1), \
             patch('modules.EsetTools.page_diagnostic', return_value='Visible page: register'):
            EsetRegister(api, 'fixture-password', driver).createAccount()

    def test_hidden_duplicate_message_does_not_mean_duplicate(self):
        with self.assertRaisesRegex(RuntimeError, 'registration did not complete'):
            self.run_registration('Create account')

    def test_visible_duplicate_message_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, 'already registered'):
            self.run_registration('This email address is already registered')
