"""Check mail without invoking ESET account or license operations."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selenium import webdriver
from modules.EmailAPIs import (
    OneSecEmailAPI, DeveloperMailAPI, GuerRillaMailAPI, MailTickingAPI,
    FakeMailAPI, InboxesAPI, IncognitoMailAPI, EmailFakeAPI,
)

PROVIDERS = {
    '1secmail': OneSecEmailAPI, 'developermail': DeveloperMailAPI,
    'guerrillamail': GuerRillaMailAPI, 'mailticking': MailTickingAPI,
    'fakemail': FakeMailAPI, 'inboxes': InboxesAPI,
    'incognitomail': IncognitoMailAPI, 'emailfake': EmailFakeAPI,
}


def check(provider):
    driver = None
    try:
        cls = PROVIDERS[provider]
        if provider in ('1secmail', 'developermail'):
            api = cls()
        else:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new')
            options.page_load_strategy = 'eager'
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(45)
            api = cls(driver)
        api.init()
        if not api.email:
            raise RuntimeError('Provider returned no email address')
        print(f'{provider}: mail initialization succeeded (address omitted).')
        return 0
    except Exception as error:
        print(f'{provider}: {type(error).__name__}: {error}', file=sys.stderr)
        return 1
    finally:
        if driver is not None:
            driver.quit()


if __name__ == '__main__':
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else 'emailfake'))
