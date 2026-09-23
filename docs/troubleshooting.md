# Workflow troubleshooting

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
