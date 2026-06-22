# AGENTS.md

This repository is a shared, public, secret-free GitHub Actions library. Treat it
as reusable infrastructure for multiple websites and applications across personal
and organization repositories.

## Scope

- Keep changes small, generic, and portable.
- Build reusable workflows, shared scripts, examples, and tests that can serve
  many caller repositories.
- Do not add repository-specific deployment details, private infrastructure
  details, or organization-specific assumptions.
- Do not add live deployment behavior before there is a small, reviewable PR
  with fixture or dry-run coverage.

## Required Workflow Architecture

- Prefer reusable workflows exposed with `workflow_call`.
- Caller repositories must supply their own runtime inputs, secrets, target
  directories, deployment configuration, and repository-specific exclude lists.
- Keep defaults conservative and safe. Optional behavior should be explicit.
- Design production deployment workflows so caller repositories can version-pin
  them later, such as `owner/repo/.github/workflows/deploy.yml@v1`.
- Avoid assumptions about branch names, build tools, package managers, hosting
  providers, domains, server paths, or application layouts unless exposed as
  caller-provided inputs.
- Keep report-only workflows read-only with respect to remote systems. They must
  not upload, delete, deploy, change permissions, move files, or write to remote
  servers.

## Shared Scripts

- Put reusable implementation logic in shared scripts when workflow YAML would
  otherwise become hard to review or duplicate.
- Scripts must accept configuration through explicit arguments, environment
  variables, or workflow inputs passed by caller repositories.
- Scripts must not hard-code domains, server paths, business names, client names,
  repository names, credentials, or other private values.
- Add fixture, dry-run, or report-only modes before adding live behavior.
- Prefer clear validation and failure messages when required caller inputs are
  missing.

## Versioning

- Keep workflow interfaces stable once caller repositories may depend on them.
- Treat workflow inputs, outputs, required secrets, side effects, and generated
  artifacts as public API.
- Document breaking changes clearly and reserve them for major version tags.
- Keep production-ready workflows safe to consume through immutable release tags
  or stable major tags.

## Safety

- Never commit secrets, tokens, keys, credentials, private hostnames, private
  paths, database dumps, logs, caches, uploaded files, or runtime data.
- Do not deploy production from this repository.
- Do not push directly to `main`.
- Use branches and pull requests for all changes.
- Do not change GitHub Actions deployment workflows unless the task explicitly
  requires it.
- Do not perform destructive actions unless explicitly requested and reviewed.
- Run `git diff --check` before committing.
- When changing shell, JavaScript, PHP, or other executable code, run the
  smallest relevant local syntax, lint, or test check available.

## Privacy And Portability

- Documentation, examples, commit messages, and PR bodies must stay generic.
- Do not mention specific sites, companies, organizations, clients, private
  repositories, domains, server paths, or local machine paths.
- Use portable wording such as "this repository", "repo root", "caller
  repository", "target directory", and "deployment host".
- Example values must be obviously placeholder values and must not resemble real
  infrastructure or customer data.

## Caller Repository Responsibilities

Caller repositories are responsible for:

- Pinning reusable workflows to an appropriate ref.
- Supplying required secrets through GitHub Actions secrets or environments.
- Supplying target directories, build commands, deployment options, and exclude
  patterns.
- Owning environment protection rules, approvals, and production rollout policy.
- Validating that reusable workflow behavior matches the caller repository's
  application, hosting platform, and compliance needs.
- Keeping repository-specific configuration outside this shared library.

## Pull Request Expectations

- Keep one task per branch and one task per PR unless explicitly directed
  otherwise.
- Prefer documentation, fixture, and dry-run improvements before live deployment
  functionality.
- Include a concise summary of behavior changes and checks run.
- Open PRs as ready for review unless work is incomplete, checks failed, or
  human input is still required.
