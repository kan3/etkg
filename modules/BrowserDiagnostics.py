"""Small, redacted diagnostics for a failed browser wait."""
import re


def redact(text):
    text = re.sub(r'[^\s<>]+@[^\s<>]+', '[email omitted]', str(text))
    text = re.sub(r'\b[A-Z0-9]{4}(?:-[A-Z0-9]{4}){4}\b', '[key omitted]', text, flags=re.I)
    text = re.sub(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b', '[token omitted]', text, flags=re.I)
    text = re.sub(r'(?i)(token|password|secret|code)=([^\s&]+)', r'\1=[omitted]', text)
    return text


def page_diagnostic(driver):
    try:
        # Do not collect HTML, cookies, storage, input values, or URL query strings.
        content = driver.execute_script("""
            const main = document.querySelector('main') || document.body;
            const labels = Array.from(document.querySelectorAll('[data-label]'))
                .map(e => e.getAttribute('data-label'))
                .filter(value => /^[a-z0-9-]+$/.test(value)).slice(0, 80);
            return {text: main ? main.innerText.slice(0, 6000) : '', labels};
        """)
        return 'Visible page: ' + redact(content['text'])[:3000] + '; control labels: ' + redact(content['labels'])
    except Exception as error:
        return f'Page diagnostics unavailable ({type(error).__name__})'
