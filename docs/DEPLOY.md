# Architecture, deployment and cost

```
GitHub Actions (cron + push to main + manual)
  1. restore data/picks + data/results from the Actions cache
  2. circa reconcile -> download new selection PDFs, fetch ESPN results, fail on mismatches
  3. circa export    -> web/public/data/**.json
  4. npm run build   -> web/dist
  5. keyless auth to Google Cloud, firebase deploy --only hosting
                                   |
                                   v
Firebase Hosting (CDN) --> visitors fetch static files only; no server, no database
```

Cache: key is the UTC date (one save/day). If evicted, the next run re-downloads all published PDFs (~1 min) and
refetches results, so nothing is lost; the PDFs and ESPN are the sources of truth.

Schedule: the cron in `.github/workflows/publish.yml` is a **placeholder** (4x/day). Pick the real cadence for
picks (Thu/Fri/Sat when PDFs appear) and results (game windows) and edit it there.

## What is configured (as of 2026-10-18)
Live site: https://circa-million-tracker-za.web.app

- GCP project `circa-million-tracker-za` (number `955147654445`), owner `zachaustin01@gmail.com`, **billing: disabled**.
  Verify any time (must print False):
  `gcloud billing projects describe circa-million-tracker-za --format="value(billingEnabled)"`
- Firebase added (Spark plan); Hosting site `circa-million-tracker-za`; live channel keeps 1 release.
- APIs enabled: firebase, firebasehosting, iamcredentials, sts, serviceusage, iam (none billable).
- Service account `gh-deployer@circa-million-tracker-za.iam.gserviceaccount.com` with only
  `roles/firebasehosting.admin` and `roles/serviceusage.serviceUsageConsumer`.
- Workload identity pool `github`, provider `github-oidc`, condition `assertion.repository=='zachaustin01/circa-million-tracker'`.
- Repo variables (identifiers, not secrets): `GCP_PROJECT_ID`, `GCP_DEPLOY_SA`, `GCP_WIF_PROVIDER`.
- `main` is protected like ballpark-projections: PR required, `build-and-deploy` must pass, no force-push or
  deletion, applies to admins. Default workflow token is read-only; PRs build and test only, never deploy.

Deliberately a separate project from ballpark-projections: Spark quotas (10 GB storage, ~360 MB/day transfer)
are per project, and the deploy identity is trusted by this repo only.

## Cost
Expected **$0**: no billing account is linked, so Google cannot charge the project; hitting a free limit stops
serving instead of billing. Never attach a billing account or accept a Blaze upgrade prompt. Cloud Storage, Cloud
Run and databases are not used (they need billing). See ballpark-projections' `docs/DEPLOY.md` for the Spark limit
details and the "if traffic outgrows the free plan" notes.

## Operations
```bash
gh run list --repo zachaustin01/circa-million-tracker
gh workflow run publish.yml --repo zachaustin01/circa-million-tracker   # manual refresh + deploy
```
Changes to `main` go through pull requests; merging redeploys.
