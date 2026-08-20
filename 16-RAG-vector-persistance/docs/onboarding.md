# Engineering Onboarding Guide

## First day

Every new engineer receives a company laptop on their first day. The laptop is
pre-installed with the standard image, but you must run the `bootstrap.sh` script
from the internal tooling repository before you can build any service locally.
The script installs the .NET SDK, Docker, the internal CLI, and the certificates
needed to reach the private NuGet feed.

Your manager will create your accounts in advance. If you cannot log in to the
identity provider on day one, contact the IT helpdesk at extension 4400. Do not
share credentials with a teammate while you wait, even temporarily.

## First week

During your first week you are expected to complete three things:

1. Finish the security awareness training in the learning portal.
2. Ship one small change to production, however trivial. The goal is to walk the
   whole path once: branch, pull request, review, CI, deploy.
3. Pair with at least two people on your team for a half day each.

Your onboarding buddy is a peer, not your manager. The buddy answers questions
about how things really work, and is explicitly allowed to spend up to four hours
per week supporting you during your first month.

## Development environment

We support Linux and macOS as development machines. Windows is supported through
WSL2 only. The main monorepo is large, so a shallow clone is recommended:
use `git clone --depth 50` unless you need full history for archaeology.

Local services run through Docker Compose. The `make dev` target starts Postgres,
Redis, and the local message broker. Do not point your local environment at the
staging database. If you need realistic data, run `make seed`, which generates
synthetic records that look real but contain no customer information.

## Getting help

Ask questions in the team channel rather than in direct messages. Answers in a
channel become searchable knowledge for the next person; answers in DMs are lost.
If a question stays unanswered for more than two hours, it is acceptable and
expected to escalate it to your team lead.
