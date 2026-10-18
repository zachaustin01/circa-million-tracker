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

## Hosting setup status
**Not configured yet.** Deploy steps are skipped while the repo variable `GCP_PROJECT_ID` is unset, so CI is green
and only builds. To enable, reproduce ballpark-projections' setup (a dedicated no-billing GCP project, Firebase
Hosting, a deploy-only service account, Workload Identity Federation restricted to this repo); see
`ballpark-projections/docs/DEPLOY.md` "Reproducing the one-time setup" and substitute
`REPO=zachaustin01/circa-million-tracker`, `PROJECT_ID=circa-million-tracker-za`.

Cost target: $0 (no billing account on the project, Actions free on public repos, Firebase Spark).
