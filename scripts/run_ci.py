"""Cross-platform workflow entry point with strict failure propagation."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ('1secmail', 'guerrillamail', 'developermail', 'mailticking',
             'fakemail', 'inboxes', 'incognitomail', 'emailfake')


def run(environ=None):
    env = os.environ if environ is None else environ
    provider = env.get('EMAIL_PROVIDER', 'inboxes')
    mode = env.get('KEY_MODE', '--key')
    if provider not in PROVIDERS or mode not in ('--key', '--small-business-key'):
        raise ValueError('Invalid email provider or key mode')
    if env.get('MAIL_ONLY', 'false').lower() == 'true':
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'check_mail.py'), provider],
            cwd=ROOT,
        ).returncode
    counts = [int(env.get(name, default) or default) for name, default in
              [('ACCOUNT_COUNT', '0'), ('KEY_COUNT', '1')]]
    if any(count < 0 for count in counts):
        raise ValueError('Account and key counts must be nonnegative')
    if not any(counts):
        raise ValueError('Select a positive count or enable the mail-only check')
    for count, operation, filename in zip(
            counts, ['--account', mode], ['accounts.txt', 'keys.txt']):
        if count == 0:
            continue
        output = ROOT / filename
        if output.exists():
            raise RuntimeError(f'{filename} already exists; use a clean working directory')
        result = subprocess.run([
            sys.executable, str(ROOT / 'main.py'), '--auto-detect-browser',
            operation, '--email-api', provider, '--skip-update-check',
            '--skip-webdriver-menu', '--no-logo', '--disable-progress-bar',
            '--disable-logging', '--repeat', str(count), '--output-file', str(output),
        ], cwd=ROOT)
        if result.returncode:
            return result.returncode
        if not output.is_file() or not output.stat().st_size:
            raise RuntimeError(f'Script reported success but produced no {filename}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(run())
    except (ValueError, RuntimeError) as error:
        print(f'Workflow failed: {error}', file=sys.stderr)
        sys.exit(1)
