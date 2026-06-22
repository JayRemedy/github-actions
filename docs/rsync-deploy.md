# Reusable rsync deploy

Reusable GitHub Actions workflow for real rsync uploads after a caller repo has already proven the target with dry-runs.

The workflow intentionally keeps destructive behavior disabled:

- does not use `--delete`
- refuses empty remote target directories
- uses strict known_hosts verification
- uses `--checksum --no-times --omit-dir-times` so GitHub checkout timestamp churn does not cause noisy uploads
- writes a bounded deploy report artifact and step summary

## Caller example

```yaml
name: 02 - Staging deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    uses: JayRemedy/github-actions/.github/workflows/rsync-deploy.yml@main
    with:
      source_path: .
      report_label: staging
      exclude_file: .github/rsync-excludes.txt
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
| `source_path` | No | `.` | Repo-relative source path to deploy. |
| `remote_target_dir` | No | empty | Remote target directory. If omitted, the `remote_target_dir` secret is used. |
| `ssh_port` | No | `22` | SSH port. The optional `ssh_port` secret overrides this. |
| `exclude_file` | No | empty | Caller repository file containing rsync exclude patterns. |
| `exclude_patterns` | No | empty | Newline-separated rsync exclude patterns supplied by the caller. |
| `report_label` | No | empty | Caller-provided target/environment label shown in the summary. |
| `artifact_retention_days` | No | `7` | Retention period for deploy report artifacts. |

## Secrets

| Secret | Required | Description |
| --- | --- | --- |
| `ssh_private_key` | Yes | SSH private key used for rsync authentication. |
| `known_hosts` | Yes | Known hosts content for strict host verification. |
| `remote_host` | Yes | Remote host. |
| `remote_user` | Yes | Remote user. |
| `remote_target_dir` | Optional | Remote target directory if not passed as input. |
| `ssh_port` | Optional | SSH port if not passed as input. |

## Artifacts

The workflow writes a deploy summary to the GitHub Actions run summary and uploads:

- `rsync-deploy-output-first-300-lines.txt`

The report is bounded to avoid leaking excessive server/path detail while still proving whether the deploy was a no-op.
