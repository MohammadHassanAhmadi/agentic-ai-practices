# Security Policy

## Secrets

Secrets are never committed to a repository, not even in a private one, and not
even temporarily. All secrets live in the central vault and are injected as
environment variables at container start. If a secret is committed by accident,
treat it as compromised: rotate it first, then clean the history. Rotating is
urgent, cleaning history is not.

Personal access tokens expire after ninety days. Service accounts use short-lived
credentials that are refreshed automatically and cannot be extended manually.

## Access control

Access follows the principle of least privilege. Production database access is
read-only by default, and write access is granted for a fixed time window through
the access request tool. Every granted window is logged and reviewed monthly.

Nobody has standing administrator access to production, including the platform
team. Administrative actions are performed through break-glass accounts, which
trigger an alert to the security channel the moment they are used.

## Dependencies

All third-party dependencies are pulled through the internal proxy, never
directly from a public registry. The proxy keeps an immutable copy of every
version we have ever used, so a package that is deleted upstream cannot break a
build. Dependency scans run on every pull request and block the merge on any
known critical vulnerability.

## Reporting an incident

If you believe you have found a security issue, report it in the security channel
immediately. Do not investigate a suspected breach alone and do not attempt to
fix it quietly. There is no penalty for reporting something that turns out to be
harmless. The only penalty is for staying silent.

Customer data must never be copied to a personal machine, a personal cloud drive,
or a local database, even for debugging. Use the anonymised data export instead.
