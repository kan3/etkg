import unittest
from unittest.mock import Mock, patch

from modules import SharedTools


TOKEN = '12345678-1234-1234-1234-123456789abc'


class ConfirmationTokenTests(unittest.TestCase):
    def message(self, body, sender='noreply@product.eset.com', subject='Confirm account'):
        return {'from': sender, 'subject': subject, 'body': body}

    def api(self, messages, provider='inboxes'):
        return Mock(class_name=provider, get_messages=Mock(return_value=messages))

    def parse(self, api, **kwargs):
        with patch('modules.SharedTools.time.sleep'):
            return SharedTools.parseToken(api, delay=0, max_iter=1, **kwargs)

    def test_confirmation_is_found_in_either_message_order(self):
        confirmation = self.message(f'<a href="https://login.eset.com/confirm?token={TOKEN}">Confirm</a>')
        notification = self.message('A later notification without an activation link.')
        for provider in ('inboxes', 'developermail'):
            for messages in ([confirmation, notification], [notification, confirmation]):
                with self.subTest(provider=provider, messages=messages):
                    self.assertEqual(self.parse(self.api(messages, provider=provider)), TOKEN)

    def test_1secmail_fetches_confirmation_body_before_later_notification(self):
        api = Mock(class_name='1secmail')
        api.read_email.return_value = [
            {'id': 101, 'from': 'noreply@product.eset.com', 'subject': 'Confirm account'},
            {'id': 102, 'from': 'noreply@product.eset.com', 'subject': 'Notification'},
        ]
        api.get_message.side_effect = lambda message_id: {
            'body': f'token={TOKEN}' if message_id == 101 else 'No confirmation link',
        }
        self.assertEqual(self.parse(api), TOKEN)
        api.read_email.assert_called_once_with()
        api.get_message.assert_called_once_with(101)
        api.get_messages.assert_not_called()

    def test_product_sender_is_case_insensitive(self):
        api = self.api([self.message(f'token={TOKEN}', sender='NoReply@PRODUCT.ESET.COM')])
        self.assertEqual(self.parse(api), TOKEN)

    def test_invalid_earlier_link_does_not_hide_valid_later_link(self):
        body = f'<a href="?token=too-short">Old</a><a href="?token={TOKEN}">Current</a>'
        self.assertEqual(self.parse(self.api([self.message(body)])), TOKEN)

    def test_html_encoded_link_is_decoded_before_extraction(self):
        body = f'<a href="https://login.eset.com/confirm?lang=en&amp;token&#61;{TOKEN}">Confirm</a>'
        self.assertEqual(self.parse(self.api([self.message(body)])), TOKEN)

    def test_business_subject_allows_activation_link(self):
        body = f'<a href="https://protecthub.eset.com/activation/{TOKEN}">Activate</a>'
        api = self.api([self.message(body, sender='hub@eset.com', subject='Welcome to ESET PROTECT Hub')])
        self.assertEqual(self.parse(api, eset_business=True), TOKEN)

    def test_polling_waits_for_confirmation_without_overwriting_it(self):
        api = self.api([])
        notification = self.message('Unrelated notification')
        confirmation = self.message(f'token={TOKEN}')
        api.get_messages.side_effect = [[], [notification], [confirmation, notification]]
        with patch('modules.SharedTools.time.sleep') as sleep:
            result = SharedTools.parseToken(api, delay=0, max_iter=3)
        self.assertEqual(result, TOKEN)
        self.assertEqual(api.get_messages.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_custom_link_uses_same_multiple_match_and_html_decoding_rules(self):
        api = Mock(class_name='custom')
        link = f'https://login.eset.com/confirm?token=short&amp;token&#61;{TOKEN}'
        with patch('builtins.input', return_value=link):
            self.assertEqual(SharedTools.parseToken(api), TOKEN)

    def test_browser_mail_link_uses_shared_extraction(self):
        api = Mock(class_name='emailfake')
        api.parse_inbox.return_value = [
            ('confirmation-id', 'noreply@product.eset.com', 'Confirm account'),
            ('notification-id', 'noreply@product.eset.com', 'Notification'),
        ]
        driver = Mock()
        driver.find_element.return_value.get_attribute.return_value = (
            f'https://login.eset.com/confirm?token=short&amp;token&#61;{TOKEN}')
        self.assertEqual(self.parse(api, driver=driver), TOKEN)
        api.open_mail.assert_called_once_with('confirmation-id')
        driver.switch_to.default_content.assert_called_once_with()

    def test_timeout_diagnostics_distinguish_reason_without_exposing_message_data(self):
        cases = [
            ('empty', [], r'(?i)(empty|no messages)'),
            ('unmatched', [self.message(f'PRIVATE-BODY token={TOKEN}',
                                       sender='private@example.com', subject='PRIVATE-SUBJECT')],
             r'(?i)(no (?:matching|eligible|eset)|none matched|unmatched)'),
            ('missing link', [self.message('PRIVATE-BODY token=SECRET-SHORT',
                                          subject='PRIVATE-SUBJECT')],
             r'(?i)(usable confirmation link|missing|without)'),
        ]
        reasons = []
        for name, messages, reason in cases:
            with self.subTest(reason=name):
                api = self.api(messages)
                with patch('modules.SharedTools.time.sleep'), self.assertRaises(RuntimeError) as error:
                    SharedTools.parseToken(api, delay=0, max_iter=2)
                diagnostic = str(error.exception)
                reasons.append(diagnostic)
                self.assertIn('inboxes', diagnostic)
                self.assertRegex(diagnostic, reason)
                self.assertRegex(diagnostic, r'(?i)polls?[^\d]*2')
                self.assertIn(f'max_messages={len(messages)}', diagnostic)
                self.assertIn(f'max_eset_matches={int(name == "missing link")}', diagnostic)
                for private in ('PRIVATE-BODY', 'PRIVATE-SUBJECT', 'private@example.com',
                                'noreply@product.eset.com', 'SECRET-SHORT', TOKEN):
                    self.assertNotIn(private, diagnostic)
                self.assertEqual(api.get_messages.call_count, 2)
        self.assertEqual(len(set(reasons)), 3)

    def test_helper_rejects_empty_and_invalid_tokens(self):
        for value in (None, '', 'No confirmation link', 'token=', 'token=too-short',
                      'token=' + 'a' * 37):
            with self.subTest(value=value):
                self.assertIsNone(SharedTools._extract_confirmation_token(value))


if __name__ == '__main__':
    unittest.main()
