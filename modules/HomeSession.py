"""Verify ESET HOME session state and perform a normal login when redirected."""
from urllib.parse import urlsplit

from selenium.common.exceptions import (
    ElementClickInterceptedException, StaleElementReferenceException, TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait

WELCOME = '[data-label="welcome-login-log-in-button"]'
LOGIN_BUTTON = '[data-label="log-in-button"]'
HOME_CONTROLS = '[data-label^="onboarding-"], [data-label="license-list-open-detail-page-btn"]'


def visible(driver, selector):
    return [element for element in driver.find_elements('css selector', selector)
            if element.is_displayed()]


def session_state(driver):
    location = urlsplit(driver.current_url)
    if location.scheme != 'https':
        return False
    if location.hostname == 'login.eset.com':
        if visible(driver, WELCOME):
            return 'welcome'
        if visible(driver, '#email') and visible(driver, '#password') and visible(driver, LOGIN_BUTTON):
            return 'login'
    elif location.hostname == 'home.eset.com':
        if not visible(driver, '.verification-email_p') and visible(driver, HOME_CONTROLS):
            return 'authenticated'
    return False


def click_when_ready(driver, selector):
    for element in visible(driver, selector):
        if element.is_enabled():
            try:
                element.click()
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                return False
    return False


def ensure_home_session(driver, email, password, timeout=45):
    wait = WebDriverWait(driver, timeout, ignored_exceptions=(StaleElementReferenceException,))
    try:
        state = wait.until(session_state)
        if state == 'welcome':
            href = visible(driver, WELCOME)[0].get_attribute('href')
            target = urlsplit(href or '')
            if target.scheme != 'https' or target.hostname != 'login.eset.com':
                raise RuntimeError('ESET welcome page returned an unexpected login destination')
            driver.get(href)
            def login_or_home(browser):
                current = session_state(browser)
                return current if current in ('login', 'authenticated') else False
            state = wait.until(login_or_home)
        if state == 'login':
            location = urlsplit(driver.current_url)
            if location.scheme != 'https' or location.hostname != 'login.eset.com':
                raise RuntimeError('Refusing to enter credentials outside the ESET login origin')
            if visible(driver, '#cc-decline'):
                wait.until(lambda d: click_when_ready(d, '#cc-decline'))
            for selector, value in (('#email', email), ('#password', password)):
                field = visible(driver, selector)[0]
                field.clear()
                field.send_keys(value)
            wait.until(lambda d: click_when_ready(d, LOGIN_BUTTON))
            wait.until(lambda d: session_state(d) == 'authenticated')
        return True
    except TimeoutException as error:
        location = urlsplit(driver.current_url)
        raise RuntimeError(
            'Account confirmation did not establish an authenticated ESET HOME session. '
            f'Last page: {location.hostname}{location.path}. '
            'Login may require additional verification or the confirmation may be incomplete.'
        ) from error
