# Workflow troubleshooting

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

The four-attempt run on September 23, 2026 completed one request, timed out
waiting for a confirmation link once, and twice timed out waiting for the
home-product trial option. A failed batch can therefore contain successful
results in its console output. The workflow summary now reports completed
versus requested counts without including account credentials or keys.

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
script's console output; workflow summaries no longer duplicate credentials.

The **Test the project** workflow runs mocked regression tests on Linux,
Windows, and macOS on pushes, pull requests, or manual dispatch. It does not
create accounts, request keys, or rewrite the README's test timestamp.

Run regression tests locally after installing `requirements.txt`:

```sh
python -m unittest discover -s tests -v
```

The inbox DOM fixture test also uses Node.js when installed.
