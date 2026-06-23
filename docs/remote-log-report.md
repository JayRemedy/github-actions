# Remote log report

Reusable, read-only workflow for collecting recent remote log excerpts over SSH.

The caller repository supplies SSH secrets and the remote search scope. This
workflow does not upload, delete, deploy, or modify remote files.

## Caller workflow example

```yaml
name: Remote log report

on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        required: true
        default: production
        options:
          - staging
          - production

permissions:
  contents: read

jobs:
  remote-log-report:
    uses: JayRemedy/github-actions/.github/workflows/remote-log-report.yml@main
    with:
      report_label: ${{ inputs.environment }}
      remote_target_dir: ${{ inputs.environment == 'production' && vars.PRODUCTION_TARGET_DIR || vars.STAGING_TARGET_DIR }}
      log_roots: |
        .
      log_name_patterns: |
        error_log
        *.log
      max_depth: 6
      max_files: 20
      tail_lines: 200
    secrets:
      ssh_private_key: ${{ inputs.environment == 'production' && secrets.PRODUCTION_SSH_PRIVATE_KEY || secrets.STAGING_SSH_PRIVATE_KEY }}
      known_hosts: ${{ inputs.environment == 'production' && secrets.PRODUCTION_SSH_KNOWN_HOSTS || secrets.STAGING_SSH_KNOWN_HOSTS }}
      remote_host: ${{ inputs.environment == 'production' && secrets.PRODUCTION_SSH_HOST || secrets.STAGING_SSH_HOST }}
      remote_user: ${{ inputs.environment == 'production' && secrets.PRODUCTION_SSH_USERNAME || secrets.STAGING_SSH_USERNAME }}
      ssh_port: ${{ inputs.environment == 'production' && secrets.PRODUCTION_SSH_PORT || secrets.STAGING_SSH_PORT }}
```

If the target directory is stored as a secret instead of a variable, pass it as
`secrets.remote_target_dir` instead of `with.remote_target_dir`.

## Inputs

- `remote_target_dir`: optional remote base directory. When set, relative
  `log_roots` are resolved from this directory.
- `log_roots`: newline-separated paths to search. Defaults to `.`.
- `log_name_patterns`: newline-separated file-name patterns. Defaults to
  `error_log` and `*.log`.
- `max_depth`: maximum `find` depth under each log root. Default: `6`.
- `max_files`: maximum newest matching files to include. Default: `20`.
- `tail_lines`: trailing lines collected from each file. Default: `200`.
- `max_bytes_per_file`: max bytes retained per tailed excerpt. Default:
  `131072`.
- `ssh_port`: SSH port. Default: `22`; callers can also supply it as a secret.
- `report_label`: optional environment/target label.
- `artifact_retention_days`: retention for report artifacts. Default: `7`.

## Required secrets

- `ssh_private_key`
- `known_hosts`
- `remote_host`
- `remote_user`

Optional secrets:

- `remote_target_dir`
- `ssh_port`

## Outputs and artifacts

The workflow uploads a `remote-log-report` artifact containing:

- `remote-log-report.md`: human-readable report with redacted excerpts.
- `remote-log-summary.json`: structured report data.

The GitHub step summary intentionally shows only the report header, file paths,
modified timestamps, and sizes. Full excerpts are kept in the artifact and are
best-effort redacted for common secret-shaped values.

## Safety notes

- This is read-only over SSH: it runs `find`, `wc`, `date`, and `tail`.
- It does not print full log excerpts to the workflow summary.
- Redaction is best-effort, not a guarantee. Treat artifacts as sensitive and do
  not share them outside the caller repository without review.
- Keep search roots narrow enough to avoid collecting customer uploads, backups,
  or unrelated runtime data.
