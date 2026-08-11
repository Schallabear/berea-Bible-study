# Deployment notes

The site deploys to GitHub Pages from `main` via `pages.yml`.

Two repository settings have to agree with that workflow, and neither can be
set from CI — both return 403 to the Actions token:

1. **Settings → Pages → Source** must be **GitHub Actions**. If Pages has never
   been enabled, `actions/configure-pages` fails with
   `Get Pages site failed … Not Found`. Adding `enablement: true` does not help;
   creating a Pages site needs admin rights the workflow token lacks
   (`Create Pages site failed … Resource not accessible by integration`).

2. **Settings → Environments → github-pages → Deployment branches** must list
   the branch the workflow pushes from. This environment is created with the
   *then-default* branch recorded **by name**, and changing the repository's
   default branch later does not update it. When the two disagree, the job is
   rejected before it starts: the run fails in ~2 seconds with no runner
   assigned, no steps, and no logs — which looks like a broken workflow but is
   an environment policy refusal.

So if `branches:` in `pages.yml` ever changes, add the new branch to that
environment's rules at the same time.
