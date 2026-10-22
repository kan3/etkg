import unittest
from unittest.mock import Mock, patch
from modules.EsetTools import EsetRegister


class RegistrationTests(unittest.TestCase):
    def run_registration(self, visible_text, urls=None, max_iter=1):
        driver = Mock()
        driver.page_source = 'hidden: This email address is already registered'
        def script(source):
            if source == 'return document.title':
                return 'Register'
            if source == 'return document.URL':
                if urls is not None:
                    return next(urls)
                return 'https://login.eset.com/Register'
            if 'document.body.innerText' in source:
                return visible_text
            return Mock(text='Ukraine')
        driver.execute_script.side_effect = script
        api = Mock(email='fixture@example.com')
        with patch('modules.EsetTools.untilConditionExecute', return_value=True) as wait, \
             patch('modules.EsetTools.time.sleep'), \
             patch('modules.EsetTools.REGISTRATION_MAX_ITER', max_iter), \
             patch('modules.EsetTools.page_diagnostic', return_value='Visible page: register'):
            result = EsetRegister(api, 'fixture-password', driver).createAccount()
        submissions = [call for call in wait.call_args_list
                       if 'register-create-account-button' in call.args[1]]
        self.assertEqual(len(submissions), 1)
        return result

    def test_hidden_duplicate_message_does_not_mean_duplicate(self):
        with self.assertRaisesRegex(RuntimeError, 'registration did not complete'):
            self.run_registration('Create account')

    def test_visible_duplicate_message_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, 'already registered'):
            self.run_registration('This email address is already registered')

    def test_slow_registration_waits_for_the_same_submission(self):
        urls = iter(['https://login.eset.com/Register'] * 35 + ['https://home.eset.com/'])
        self.assertTrue(self.run_registration('Loading', urls=urls, max_iter=120))
