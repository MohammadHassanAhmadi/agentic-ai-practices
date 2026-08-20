# Deployment and Release Process

## Environments

We run four environments: local, dev, staging, and production. Dev and staging
are shared, so breaking them affects other teams. Production is the only
environment with real customer data.

Every environment is deployed from the same container image. The image is built
once, tagged with the git commit SHA, and promoted forward. We never rebuild an
image for production, because a rebuild can silently pick up a different
dependency version than the one that was tested.

## Release windows

Deployments to production are allowed Monday through Thursday, between 09:00 and
16:00 local time. Friday deployments are blocked by default because too few
people are available to respond if something breaks over the weekend.

A release outside the window requires approval from the on-call engineer and the
service owner. Emergency fixes for an active incident are always allowed and do
not need prior approval, but they must be documented in the incident channel
within one hour.

## Rollback

Every deployment must be reversible within five minutes. In practice this means
two rules. First, a database migration must be backward compatible with the
previous version of the application: add columns, never rename or drop them in
the same release that starts using them. Second, feature flags are preferred
over long-lived branches, so a bad feature can be disabled without a redeploy.

To roll back, run `deploy rollback <service>` from the CLI. This re-points the
service to the previously running image tag. Rollback does not undo database
migrations, which is exactly why migrations must be backward compatible.

## Health checks and canaries

New versions go out as a canary to five percent of traffic for ten minutes. The
canary is promoted automatically if the error rate stays below the service's
error budget and the p99 latency does not regress by more than twenty percent.
If either check fails, the canary is withdrawn automatically and the deployment
is marked failed. Nobody has to be watching a dashboard for this to work.
