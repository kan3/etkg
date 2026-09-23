import unittest
from unittest.mock import Mock, patch

from modules.HomeSession import (
    HOME_CONTROLS, LOGIN_BUTTON, WELCOME, ensure_home_session, session_state,
    TrialUnavailableError, trial_option_state,
)
from modules.EsetTools import EsetRegister
from modules.EmailAPIs import CustomEmailAPI


def element():
    return Mock(is_displayed=Mock(return_value=True), is_enabled=Mock(return_value=True))


class SessionTests(unittest.TestCase):
    def test_service_refusal_fails_immediately(self):
        driver = Mock()
        driver.execute_script.return_value = "No free 30-day trials available\nIt looks like you've already used your available trials."
        with self.assertRaisesRegex(TrialUnavailableError, 'without ESET eligibility'):
            trial_option_state(driver, '148')
        driver.find_elements.assert_not_called()

    def test_available_trial_option_is_detected(self):
        driver = Mock()
        driver.execute_script.return_value = 'Choose your trial'
        driver.find_elements.return_value = [element()]
        self.assertTrue(trial_option_state(driver, '148'))

    def make_login(self, submit_succeeds=True):
        driver = Mock(current_url='https://login.eset.com/login')
        email, password, submit, home = [element() for _ in range(4)]
        fields = {'#email': email, '#password': password, LOGIN_BUTTON: submit}
        def find(by, selector):
            if driver.current_url == 'https://home.eset.com/':
                return [home] if selector == HOME_CONTROLS else []
            return [fields[selector]] if selector in fields else []
        driver.find_elements.side_effect = find
        if submit_succeeds:
            def submitted():
                driver.current_url = 'https://home.eset.com/'
            submit.click.side_effect = submitted
        return driver, email, password, submit

    def test_login_title_does_not_mean_authenticated(self):
        driver, _, _, _ = self.make_login()
        driver.title = 'Log in to ESET HOME - Access & manage your account'
        self.assertEqual(session_state(driver), 'login')

    def test_existing_session_does_not_submit_credentials(self):
        driver, email, password, submit = self.make_login()
        driver.current_url = 'https://home.eset.com/'
        self.assertTrue(ensure_home_session(driver, 'private@example.com', 'secret'))
        email.send_keys.assert_not_called()
        password.send_keys.assert_not_called()
        submit.click.assert_not_called()

    def test_login_redirect_uses_existing_credentials_once(self):
        driver, email, password, submit = self.make_login()
        self.assertTrue(ensure_home_session(driver, 'private@example.com', 'secret'))
        email.send_keys.assert_called_once_with('private@example.com')
        password.send_keys.assert_called_once_with('secret')
        submit.click.assert_called_once()

    def test_welcome_follows_normal_login_link(self):
        driver, email, _, submit = self.make_login()
        original_find = driver.find_elements.side_effect
        link = element()
        link.get_attribute.return_value = 'https://login.eset.com/login'
        driver.current_url = 'https://login.eset.com/welcome'
        def find(by, selector):
            if driver.current_url.endswith('/welcome'):
                return [link] if selector == WELCOME else []
            return original_find(by, selector)
        driver.find_elements.side_effect = find
        driver.get.side_effect = lambda url: setattr(driver, 'current_url', url)
        self.assertTrue(ensure_home_session(driver, 'private@example.com', 'secret'))
        driver.get.assert_called_once_with('https://login.eset.com/login')
        submit.click.assert_called_once()

    def test_untrusted_login_destination_is_rejected(self):
        driver, email, password, _ = self.make_login()
        driver.current_url = 'https://login.eset.com/welcome'
        link = element()
        link.get_attribute.return_value = 'https://example.com/login'
        driver.find_elements.side_effect = lambda by, selector: [link] if selector == WELCOME else []
        with self.assertRaisesRegex(RuntimeError, 'unexpected login destination'):
            ensure_home_session(driver, 'private@example.com', 'secret')
        driver.get.assert_not_called()
        email.send_keys.assert_not_called()
        password.send_keys.assert_not_called()

    def test_verification_banner_prevents_false_success(self):
        driver = Mock(current_url='https://home.eset.com/')
        driver.find_elements.return_value = [element()]
        self.assertFalse(session_state(driver))

    def test_additional_login_step_is_not_reported_as_success(self):
        driver, _, _, submit = self.make_login(submit_succeeds=False)
        with self.assertRaisesRegex(RuntimeError, 'did not establish an authenticated'):
            ensure_home_session(driver, 'private@example.com', 'secret', timeout=0)
        submit.click.assert_called_once()

    def test_confirmation_does_not_swallow_authentication_failure(self):
        mailbox = CustomEmailAPI()
        mailbox.email = 'private@example.com'
        register = EsetRegister(mailbox, 'secret', Mock())
        with patch('modules.EsetTools.parseToken', return_value='fixture-token'), \
             patch('modules.EsetTools.ensure_home_session', side_effect=RuntimeError('login required')), \
             patch('modules.EsetTools.console_log') as log:
            with self.assertRaisesRegex(RuntimeError, 'login required'):
                register.confirmAccount()
        self.assertNotIn('confirmed and authenticated', str(log.call_args_list))
        self.assertNotIn('fixture-token', str(log.call_args_list))


if __name__ == '__main__':
    unittest.main()
