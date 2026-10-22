import unittest
from unittest.mock import Mock, patch, PropertyMock
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    StaleElementReferenceException,
)
from modules.EmailAPIs import InboxesAPI


class InboxesTests(unittest.TestCase):
    def element(self, text, visible=True, enabled=True):
        return Mock(text=text, is_displayed=Mock(return_value=visible),
                    is_enabled=Mock(return_value=enabled))

    def test_placeholder_is_not_an_address(self):
        driver = Mock()
        driver.find_elements.return_value = [self.element('Creating...'),
                                             self.element('wrong@example.com suffix')]
        self.assertFalse(InboxesAPI(driver)._ready_address(driver))

    def test_page_refresh_retries_instead_of_aborting(self):
        driver, stale = Mock(), self.element('outdated@example.com')
        type(stale).text = PropertyMock(side_effect=StaleElementReferenceException())
        driver.find_elements.side_effect = [[stale], [self.element('user@example.com')]]
        api = InboxesAPI(driver)
        self.assertFalse(api._ready_address(driver))
        self.assertEqual(api._ready_address(driver), 'user@example.com')

    def test_valid_address_allows_domain_digits_and_hyphens(self):
        driver = Mock()
        driver.find_elements.return_value = [self.element(' user+tag@mx-2.example.com ')]
        self.assertEqual(InboxesAPI(driver)._ready_address(driver), 'user+tag@mx-2.example.com')

    @patch('modules.EmailAPIs.WebDriverWait')
    def test_waits_for_address_only_after_chooser_is_clicked_once(self, wait):
        driver = Mock()
        chooser = self.element('Choose for me')
        driver.find_elements.side_effect = [[self.element('Creating...')],
                                             [self.element('user@example.com')]]

        def resolve(condition):
            for _ in range(4):
                value = condition(driver)
                if value:
                    return value
            raise TimeoutException()

        wait.return_value.until.side_effect = resolve
        api = InboxesAPI(driver)
        with patch.object(api, '_open_inbox_chooser', return_value=chooser), \
             patch.object(api, '_ready_address', wraps=api._ready_address) as ready:
            chooser.click.side_effect = lambda: self.assertEqual(ready.call_count, 0)
            api.init()
        chooser.click.assert_called_once()
        self.assertEqual(api.email, 'user@example.com')
        self.assertEqual(ready.call_count, 2)
        driver.get.assert_called_once_with('https://inboxes.com')

    @patch('modules.BrowserDiagnostics.page_diagnostic', return_value='Visible page: unavailable')
    @patch('modules.EmailAPIs.WebDriverWait')
    def test_address_timeout_is_explicit(self, wait, diagnostic):
        driver = Mock()
        chooser = self.element('Choose for me')
        wait.return_value.until.side_effect = [chooser, TimeoutException()]
        with self.assertRaisesRegex(RuntimeError, 'no valid mailbox address'):
            InboxesAPI(driver).init()
        chooser.click.assert_called_once()

    @patch('modules.EmailAPIs.WebDriverWait')
    def test_delayed_chooser_is_polled_before_mailbox_address(self, wait):
        driver = Mock()
        chooser = self.element('Choose for me')
        api = InboxesAPI(driver)
        events = []

        def resolve(condition):
            for _ in range(4):
                value = condition(driver)
                if value:
                    return value
            raise TimeoutException()

        def read_address(_):
            self.assertEqual(events, ['chosen'])
            return 'real@example.com'

        wait.return_value.until.side_effect = resolve
        chooser.click.side_effect = lambda: events.append('chosen')
        with patch.object(api, '_open_inbox_chooser', side_effect=[False, False, chooser]) as open_chooser, \
             patch.object(api, '_ready_address', side_effect=read_address):
            api.init()
        self.assertEqual(open_chooser.call_count, 3)
        chooser.click.assert_called_once()
        self.assertEqual(api.email, 'real@example.com')

    @patch('modules.BrowserDiagnostics.page_diagnostic', return_value='Visible page: chooser unavailable')
    @patch('modules.EmailAPIs.WebDriverWait')
    def test_missing_chooser_fails_without_reading_sample_address(self, wait, diagnostic):
        driver = Mock()
        driver.find_elements.return_value = [self.element('sample@example.com')]
        wait.return_value.until.side_effect = TimeoutException()
        api = InboxesAPI(driver)
        with patch.object(api, '_ready_address') as read_address:
            with self.assertRaisesRegex(RuntimeError, '(?i)(choose|chooser|create-inbox)') as error:
                api.init()
        read_address.assert_not_called()
        self.assertIsNone(api.email)
        self.assertIn('Visible page: chooser unavailable', str(error.exception))

    def test_sample_sender_spans_are_excluded_from_address_search(self):
        driver = Mock()
        heading = self.element('Creating...')
        sample_sender = self.element('sender@sample.example')

        def elements(by, selector):
            self.assertEqual(by, 'css selector')
            return [heading] if selector == 'h1 span' else [sample_sender, heading]

        driver.find_elements.side_effect = elements
        self.assertFalse(InboxesAPI(driver)._ready_address(driver))
        driver.find_elements.assert_called_once_with('css selector', 'h1 span')

    def test_hidden_heading_address_is_ignored(self):
        driver = Mock()
        driver.find_elements.return_value = [
            self.element('hidden@example.com', visible=False),
            self.element('visible@example.com'),
        ]
        self.assertEqual(InboxesAPI(driver)._ready_address(driver), 'visible@example.com')

    def test_heading_that_becomes_stale_before_visibility_check_is_retried(self):
        driver = Mock()
        stale = self.element('old@example.com')
        stale.is_displayed.side_effect = StaleElementReferenceException()
        driver.find_elements.side_effect = [[stale], [self.element('current@example.com')]]
        api = InboxesAPI(driver)
        self.assertFalse(api._ready_address(driver))
        self.assertEqual(api._ready_address(driver), 'current@example.com')

    def test_landing_click_is_retried_until_chooser_really_opens(self):
        driver = Mock()
        opener = self.element('Get my first inbox!')
        chooser = self.element('Choose for me')

        def elements(by, selector):
            self.assertEqual(by, 'xpath')
            if selector == '//button[normalize-space(.)="Choose for me"]':
                return [chooser] if opener.click.call_count >= 2 else []
            self.assertEqual(selector, '//button[contains(normalize-space(.), "Get my first inbox")]')
            return [opener]

        driver.find_elements.side_effect = elements
        api = InboxesAPI(driver)
        self.assertFalse(api._open_inbox_chooser(driver))
        self.assertFalse(api._open_inbox_chooser(driver))
        self.assertIs(api._open_inbox_chooser(driver), chooser)
        self.assertEqual(opener.click.call_count, 2)
        chooser.click.assert_not_called()

    def test_hidden_and_disabled_chooser_buttons_are_not_selected(self):
        driver = Mock()
        hidden = self.element('Choose for me', visible=False)
        disabled = self.element('Choose for me', enabled=False)
        visible = self.element('Choose for me')
        driver.find_elements.return_value = [hidden, disabled, visible]
        self.assertIs(InboxesAPI(driver)._open_inbox_chooser(driver), visible)
        driver.find_elements.assert_called_once()
        for chooser in (hidden, disabled, visible):
            chooser.click.assert_not_called()

    def test_hidden_and_disabled_landing_buttons_are_not_clicked(self):
        driver = Mock()
        hidden = self.element('Get my first inbox!', visible=False)
        disabled = self.element('Get my first inbox!', enabled=False)
        visible = self.element('Get my first inbox!')
        driver.find_elements.side_effect = [[], [hidden, disabled, visible]]
        self.assertFalse(InboxesAPI(driver)._open_inbox_chooser(driver))
        hidden.click.assert_not_called()
        disabled.click.assert_not_called()
        visible.click.assert_called_once()

    def test_stale_chooser_poll_retries_without_creating_an_address(self):
        driver = Mock()
        stale = self.element('Choose for me')
        stale.is_displayed.side_effect = StaleElementReferenceException()
        current = self.element('Choose for me')
        driver.find_elements.side_effect = [[stale], [current]]
        api = InboxesAPI(driver)
        self.assertFalse(api._open_inbox_chooser(driver))
        self.assertIs(api._open_inbox_chooser(driver), current)
        self.assertIsNone(api.email)
        current.click.assert_not_called()

    def test_intercepted_landing_click_is_retried_on_next_poll(self):
        driver = Mock()
        opener = self.element('Get my first inbox!')
        opener.click.side_effect = [ElementClickInterceptedException(), None]
        driver.find_elements.side_effect = [[], [opener], [], [opener]]
        api = InboxesAPI(driver)
        self.assertFalse(api._open_inbox_chooser(driver))
        self.assertFalse(api._open_inbox_chooser(driver))
        self.assertEqual(opener.click.call_count, 2)
        self.assertIsNone(api.email)


if __name__ == '__main__':
    unittest.main()
