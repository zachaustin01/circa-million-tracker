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

Schedule (UTC, in `.github/workflows/publish.yml`): every 3 hours as a baseline, plus every 15 minutes during
the game windows: Thu 23:00-04:59 (Thu night game), Sun 13:00 through Mon 04:59, and Mon 23:00-Tue 04:59.
Not covered: Saturday games late in the season, Thanksgiving, Christmas and international Friday games; use
**Run workflow** (or add a cron line) for those. Every run also deploys, which is free (public repo, Spark plan).

## What is configured (as of 2026-10-18)
Live site: https://circa-million-tracker-za.web.app

- GCP project `circa-million-tracker-za`, owned by the repo owner's Google account, **billing: disabled**.
  Verify any time (must print False):
  `gcloud billing projects describe circa-million-tracker-za --format="value(billingEnabled)"`
- Firebase added (Spark plan); Hosting site `circa-million-tracker-za`; live channel keeps 1 release.
- APIs: the six we use (firebase, firebasehosting, iam, iamcredentials, sts, serviceusage) plus GCP's default
  new-project set (BigQuery, Storage, Datastore, logging, etc.), which cannot be disabled without breaking each
  other and are unusable without billing. Firebase's extras (Identity Toolkit, Pub/Sub, Remote Config, Rules, FCM,
  Testing, App Engine, ...) and its auto-created browser API key were removed on 2026-10-18.
- The Firebase Admin service account (`firebase-adminsdk-*`) was auto-created, has no downloadable keys, and is
  unused; left alone to avoid breaking Firebase management.
- Deploy service account `gh-deployer` (in that project) with only
  `roles/firebasehosting.admin` and `roles/serviceusage.serviceUsageConsumer`.
- Workload identity pool `github`, provider `github-oidc`. Condition (hardened 2026-10-18): repository is this repo AND
  `ref == refs/heads/main` AND `job_workflow_ref == .../.github/workflows/publish.yml@refs/heads/main`, so only the
  deploy workflow on `main` can mint deploy credentials.
- Repo variables (identifiers, not secrets; values are in the repo's Actions settings): `GCP_PROJECT_ID`, `GCP_DEPLOY_SA`, `GCP_WIF_PROVIDER`.
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

## Security model
- CI is two jobs. `build` (read-only token, no Google credentials) runs everything that executes third-party code:
  the PDF parser, `npm ci --ignore-scripts`, the build. `deploy` is the only job with `id-token: write`; it runs no
  repo code, only downloads the built site and publishes it with a pinned `firebase-tools`. Caveat: a compromised
  build could still alter the site content it hands over; the split removes credential theft and arbitrary
  Google API use, not content tampering.
- Third-party actions are pinned to commit SHAs (Dependabot keeps them current).
- The site sends a strict Content-Security-Policy (`default-src 'none'`, scripts/styles/connect from self only).
- PDFs are fetched only from `https://www.circasports.com/wp-content/uploads/` (no redirects, 50 MB / 500 page caps).
- The site shows when scores were last fetched and warns if live games have stale scores.
- GitHub repo: secret scanning + push protection, Dependabot alerts + security updates + weekly version updates
  (actions, uv, npm), private vulnerability reporting, actions must be pinned to SHAs, fork PRs from all outside
  contributors need approval, default token read-only, wiki/projects off, branches deleted on merge.
- Scheduled workflows are paused by GitHub after 60 days without repo activity; push a commit before next season.
