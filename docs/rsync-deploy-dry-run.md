# Reusable rsync deploy dry-run

Reusable GitHub Actions workflow for previewing what an rsync deploy would upload or update.

The workflow is intentionally dry-run only:

- uses `rsync -n`
- uses `--checksum --no-times --omit-dir-times` so GitHub checkout timestamp churn does not appear as deploy drift
- does not use `--delete`
- does not upload files
- does not delete files
- does not deploy files
- does not change permissions or timestamps
- uploads only sanitized summary artifacts

## Caller example

```yaml
name: 01 - Staging deploy dry-run

on:
  workflow_dispatch:

jobs:
  dry-run:
    uses: JayRemedy/github-actions/.github/workflows/rsync-deploy-dry-run.yml@main
    with:
      source_path: .
      report_label: staging
      exclude_patterns: |
        .git/**
        .github/**
        .gitignore
        **/.gitkeep
        README.md
    secrets:
      ssh_private_key: ${{ secrets.STAGING_SSH_PRIVATE_KEY }}
      known_hosts: ${{ secrets.STAGING_SSH_KNOWN_HOSTS }}
      remote_host: ${{ secrets.STAGING_SSH_HOST }}
      remote_user: ${{ secrets.STAGING_SSH_USERNAME }}
      remote_target_dir: ${{ secrets.STAGING_RSYNC_TARGET_DIR }}
      ssh_port: ${{ secrets.STAGING_SSH_PORT }}
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `source_path` | No | `.` | Repo-relative source path to dry-run deploy. |
| `remote_target_dir` | No | empty | Remote target directory. If omitted, the `remote_target_dir` secret is used. |
| `ssh_port` | No | `22` | SSH port. The optional `ssh_port` secret overrides this. |
| `exclude_file` | No | empty | Caller repository file containing rsync exclude patterns. |
| `exclude_patterns` | No | empty | Newline-separated rsync exclude patterns supplied by the caller. |
| `report_label` | No | empty | Caller-provided target/environment label shown in the summary and JSON. |
| `toolkit_repository` | No | `JayRemedy/github-actions` | Shared toolkit repository containing scripts. |
| `toolkit_ref` | No | `main` | Shared toolkit repository ref to check out. Pin this when callers need stability. |
| `artifact_retention_days` | No | `14` | Retention period for sanitized report artifacts. |

## Secrets

| Secret | Required | Description |
| --- | --- | --- |
| `ssh_private_key` | Yes | SSH private key used for rsync authentication. Dry-run still validates auth. |
| `known_hosts` | Yes | Known hosts content for strict host verification. |
| `remote_host` | Yes | Remote host. |
| `remote_user` | Yes | Remote user. |
| `remote_target_dir` | Optional | Remote target directory if not passed as input. |
| `ssh_port` | Optional | SSH port if not passed as input. |

## Artifacts

The workflow writes the same sanitized Markdown report to the GitHub Actions run summary and uploads:

- `rsync-dry-run-report.md`
- `rsync-dry-run-summary.json`

The report includes:

- safety booleans: `dry_run=true`, `deleted=false`, `uploaded=false`, `deployed=false`
- aggregate rsync dry-run change counts
- change buckets by rsync action and file type
- bounded repo-side changed path samples, up to 50 entries

## Local fixture run

```bash
cat > /tmp/rsync-itemize.log <<'LOG'
>f+++++++++ index.php
>f.st...... assets/app.css
cd+++++++++ downloads/jd/
LOG

python3 scripts/rsync_dry_run_summary.py \
  --itemize-log /tmp/rsync-itemize.log \
  --output-dir build/rsync-dry-run-fixture \
  --report-label staging

python3 -m json.tool build/rsync-dry-run-fixture/rsync-dry-run-summary.json >/dev/null
```
