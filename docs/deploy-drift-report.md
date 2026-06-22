# Deploy Drift Report Workflow

`deploy-drift-report.yml` is a reusable, report-only workflow for comparing a
caller repository file tree with a remote target directory. It produces sanitized
artifacts with aggregate drift counts and path bucket analysis.

The workflow does not upload, delete, deploy, change permissions, move files, or
write to remote servers.

## Reusable Workflow

Caller repositories use this workflow through `workflow_call`:

```yaml
name: Deploy drift report

on:
  schedule:
    - cron: "0 6 * * 1"

jobs:
  deploy-drift-report:
    uses: placeholder-owner/placeholder-actions/.github/workflows/deploy-drift-report.yml@v1
    with:
      fixture_mode: false
      source_path: build-output
      remote_host: ${{ vars.DEPLOY_HOST }}
      remote_user: ${{ vars.DEPLOY_USER }}
      remote_target_dir: ${{ vars.DEPLOY_TARGET_DIR }}
      report_label: staging
      exclude_file: .github/deploy-drift-excludes.txt
    secrets:
      ssh_private_key: ${{ secrets.DEPLOY_READONLY_SSH_KEY }}
      known_hosts: ${{ secrets.DEPLOY_KNOWN_HOSTS }}
```

All values in this example are placeholders. Caller repositories own their
secrets, hostnames, usernames, target directories, and exclude configuration.

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `fixture_mode` | No | `true` | Runs against bundled fixture file lists instead of SSH. |
| `source_path` | No | `.` | Caller repository path to compare in live mode. |
| `remote_host` | Live mode | empty | Deployment host from the caller repository. |
| `remote_user` | Live mode | empty | SSH username from the caller repository. |
| `remote_target_dir` | Live mode | empty | Remote target directory from the caller repository. |
| `ssh_port` | No | `22` | SSH port from the caller repository. |
| `exclude_file` | No | empty | Caller repository file containing exclude patterns. |
| `exclude_patterns` | No | empty | Newline-separated exclude patterns supplied by the caller. |
| `report_label` | No | empty | Caller-provided target/environment label shown in the summary and JSON. |
| `toolkit_repository` | No | `JayRemedy/github-actions` | Shared toolkit repository containing scripts and fixtures. |
| `toolkit_ref` | No | `main` | Shared toolkit repository ref to check out. Pin this when callers need stability. |
| `artifact_retention_days` | No | `14` | Retention period for sanitized report artifacts. |

## Secrets

| Secret | Required | Description |
| --- | --- | --- |
| `ssh_private_key` | Live mode | Read-only SSH private key supplied by the caller repository. |
| `known_hosts` | Live mode | Known hosts content supplied by the caller repository. |
| `remote_host` | Optional | Deployment host, for callers that keep connection values in secrets instead of variables. |
| `remote_user` | Optional | SSH username, for callers that keep connection values in secrets instead of variables. |
| `remote_target_dir` | Optional | Remote target directory, for callers that keep connection values in secrets instead of variables. |
| `ssh_port` | Optional | SSH port, for callers that keep connection values in secrets instead of inputs. |

## Artifacts

The workflow writes the same sanitized Markdown report to the GitHub Actions run summary and uploads only these sanitized artifacts:

- `deploy-drift-report.md`
- `deploy-drift-summary.json`

The artifacts include:

- safety booleans: `deleted=false`, `uploaded=false`, `deployed=false`
- local, remote, matching, local-only, and remote-only file counts
- extra remote path bucket analysis by depth, generic category, and extension
- a possible copied-site-tree heuristic based on aggregate signals

Raw remote file lists are not uploaded.

## Local Fixture Run

Run the bundled fixture mode locally:

```bash
python3 scripts/deploy_drift_report.py \
  --local-list fixtures/deploy-drift/local-files.txt \
  --remote-list fixtures/deploy-drift/remote-files.txt \
  --exclude-file fixtures/deploy-drift/excludes.txt \
  --output-dir build/deploy-drift-fixture \
  --fixture-name bundled
```

Validate the JSON artifact:

```bash
python3 -m json.tool build/deploy-drift-fixture/deploy-drift-summary.json >/dev/null
```
