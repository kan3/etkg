import unittest
from unittest.mock import Mock, patch
from selenium.common.exceptions import TimeoutException
from modules.EmailAPIs import InboxesAPI


class InboxesTests(unittest.TestCase):
    def test_placeholder_is_not_an_address(self):
        driver = Mock()
        driver.find_elements.return_value = [Mock(text='Creating...'), Mock(text='wrong@example.com suffix')]
        self.assertFalse(InboxesAPI(driver)._ready_address(driver))

    def test_valid_address_allows_domain_digits_and_hyphens(self):
        driver = Mock()
        driver.find_elements.return_value = [Mock(text=' user+tag@mx-2.example.com ')]
        self.assertEqual(InboxesAPI(driver)._ready_address(driver), 'user+tag@mx-2.example.com')

    @patch('modules.EmailAPIs.time.sleep')
    @patch('modules.EmailAPIs.WebDriverWait')
    def test_waits_for_address_after_creation(self, wait, sleep):
        driver = Mock()
        driver.execute_script.return_value = [Mock(text='Choose for me')]
        driver.find_elements.side_effect = [[Mock(text='Creating...')], [Mock(text='user@example.com')]]
        def resolve(condition):
            self.assertFalse(condition(driver))
            return condition(driver)
        wait.return_value.until.side_effect = resolve
        api = InboxesAPI(driver)
        api.init()
        self.assertEqual(api.email, 'user@example.com')

    @patch('modules.BrowserDiagnostics.page_diagnostic', return_value='Visible page: unavailable')
    @patch('modules.EmailAPIs.time.sleep')
    @patch('modules.EmailAPIs.WebDriverWait')
    def test_timeout_is_explicit(self, wait, sleep, diagnostic):
        driver = Mock()
        driver.execute_script.return_value = [Mock(text='Choose for me')]
        wait.return_value.until.side_effect = TimeoutException()
        with self.assertRaisesRegex(RuntimeError, 'no valid email address'):
            InboxesAPI(driver).init()


if __name__ == '__main__':
    unittest.main()
