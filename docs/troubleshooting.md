# Workflow troubleshooting

## Recovery after syncing upstream (October 22, 2026)

The October 22 sync replaced the fork's repaired branch with upstream code.
It removed the tests, dependency constraints, session validation, and mailbox
wait fixes. The upstream workflow also cloned `shadowcopyrz/etkg` and could
report success after the script failed. The repair restores the coherent
application and workflow from `cda2a0a`, as a new commit on top of the synced
history. Upstream's newer refactor is not used by this repaired version.

The repaired baseline completed successfully on October 22 before the sync:
[pre-sync run](https://github.com/kan3/etkg/actions/runs/39713337837).
The later green runs on the synced code contain failures; a green check alone
does not prove that any output was produced.

The first restored live run reached registration but remained on a visible
**Loading** state at the old 30-second deadline. Registration now waits up to
two minutes for that single submission; it does not resubmit the form. A
timeout remains a failure and includes the redacted visible page state.

To retain the fork's repairs during future updates, merge reviewed upstream
changes through a branch and pull request. Resolve conflicts while retaining
the local workflow runner, tests, dependency constraints, and session helpers.
Avoid **Discard commits** or force-sync options, which can replace these
changes. GitHub documents the merge approach in
[Syncing a fork](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/syncing-a-fork).
Run the regression workflow after merging, then use the manual mail-only
check to verify mailbox initialization independently of registration.

The workflow regression tests catch upstream cloning, automatic generation,
timestamp-writing tests, and deprecated checkout versions. They cannot
protect against a forced overwrite that also removes the tests themselves.

## External trial availability

The diagnostic run on September 23, 2026 reached a confirmed, authenticated
session, but ESET displayed **No free 30-day trials available** and stated that
the available trials had already been used:
[diagnostic run](https://github.com/kan3/etkg/actions/runs/35887787610).
Such a refusal prevents successful key generation; code cannot grant eligibility.
The workflow now reports the refusal immediately and stops the batch after a
failed attempt rather than registering more accounts. Earlier successful
results are preserved and counted, but a partial batch remains a failure.
This was an observed refusal in that run, rather than a permanent current
blocker. Later runs, including the pre-sync run above, completed successfully.
If the message reappears, resolve eligibility through ESET instead of retrying
with more accounts.

## Verified configuration

Use **ubuntu-latest** with **inboxes**, now the workflow defaults.
An end-to-end run on September 23, 2026 successfully initialized a mailbox,
registered and confirmed one account, and produced the requested trial-key
output: [verified run](https://github.com/kan3/etkg/actions/runs/35853460769).

The Windows comparison run initialized the mailbox and loaded the registration
form, but its local ChromeDriver connection was reset before submission.
That Windows-specific failure remains unresolved; use the verified Ubuntu
configuration. Mocked regression tests pass on all three operating systems,
but that does not prove that each live browser integration works.

## Mail and workflow diagnostics

Account confirmation now requires visible ESET HOME controls on the actual
`home.eset.com` origin. The login page's title also contains "ESET HOME", so
title matching alone was not evidence of an authenticated session. When the
confirmation link redirects to the welcome or login page, the script follows
the normal login flow once, using that attempt's existing account credentials.
Additional verification is reported as a failure rather than bypassed. An
already-skipped welcome screen no longer causes a mandatory-skip timeout.
Confirmation tokens are no longer printed. CI installs use the tested versions
in `constraints-ci.txt`.

The four-attempt run on September 23, 2026 completed one request, timed out
waiting for a confirmation link once, and twice timed out waiting for the
home-product trial option. A failed batch can therefore contain successful
results in its console output. The workflow summary reports completed versus
requested counts and shows each generated license key with its expiry date,
including keys from a partially successful batch. Account email addresses,
passwords, and confirmation tokens are excluded from the summary.

Browser-condition timeouts now report the page title and available onboarding
control labels. A missing trial option alone does not establish an IP block;
the old `TRY VPN` diagnosis was unsupported. The confirmation-email timeout
also does not distinguish nondelivery from an unrecognized email template.

The **Account and Key Generator** workflow now runs the selected branch of
this repository. It no longer clones and executes the upstream repository.
Use GitHub's **Use workflow from** selector to choose a branch.

To check a mail provider independently, enable **Check mail initialization
only** when starting the workflow. This creates no ESET account and requests
no license. A successful check verifies mailbox initialization only; it does
not prove message delivery or acceptance by ESET.

The Windows runner check on September 23, 2026 found that `emailfake.com`
returned a page titled **Access temporarily limited**, instead of an inbox.
This is a provider access restriction, not a Node.js or checkout error.
The same runner successfully initialized a mailbox with `inboxes`, which is
now the workflow default. The standalone CLI retains its upstream default;
pass `--email-api inboxes` explicitly when checking this provider locally.
Do not treat a provider's challenge page as a successful mailbox. Wait for
access to be restored or select another supported provider. Interactive
verification must be completed through the provider's supported process.

Mail initialization errors now retain their cause. Script errors, failed
repeated attempts, and missing output files produce a failed workflow rather
than a misleading green check. Successful account/key output remains in the
script's console output. New run summaries also display license keys and expiry
dates. Already completed run summaries are unchanged; find their original
output by opening the **Run script** step in the job logs.

The **Test the project** workflow runs mocked regression tests on Linux,
Windows, and macOS on pushes, pull requests, or manual dispatch. It does not
create accounts, request keys, or rewrite the README's test timestamp.

Run regression tests locally after installing `requirements.txt`:

```sh
python -m unittest discover -s tests -v
```

The inbox DOM fixture test also uses Node.js when installed.
