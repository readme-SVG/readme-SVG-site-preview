# Contributing Guide

## 1. Introduction

Thank you for your interest in contributing to this logging library. Contributions from the community are essential for improving reliability, performance, and developer experience across diverse runtime environments.

Whether you are reporting a defect, proposing a feature, improving documentation, or submitting a code change, we appreciate your time and effort. This guide defines contribution standards so maintainers can review changes efficiently and keep the project stable.

## 2. I Have a Question

If you have a usage or design question, please do **not** open a GitHub Issue.

The GitHub Issue tracker is reserved for:

- Reproducible bug reports
- Concrete feature requests

For general questions, usage troubleshooting, integration help, or architecture discussions, use one of the following channels:

- GitHub Discussions (preferred)
- Stack Overflow (tag your question with the project tag if available)
- Community chat channel (for quick, informal support)

Submitting non-actionable questions in Issues slows triage and delays bug fixes.

## 3. Reporting Bugs

A high-quality bug report should let a maintainer reproduce the issue on the first pass.

Before opening a new issue, complete this checklist.

### Search Duplicates

- Search existing open and closed issues for similar symptoms.
- If a related issue exists, add your reproduction details there instead of opening a duplicate.

### Environment

Include full environment metadata:

- Operating system and version (for example: Ubuntu 24.04, macOS 15.x, Windows 11)
- Library version (and whether installed from release, source, or local fork)
- Language runtime version (for example: Node.js, Python, JVM, .NET)
- Framework or platform version if applicable (for example: Express, FastAPI, Spring)
- Logger transport/back-end details (file, console, HTTP, syslog, cloud sink)

### Steps to Reproduce

Provide a deterministic sequence to trigger the bug:

1. Minimal configuration used
2. Exact code snippet or command
3. Input payloads or environment variables
4. Sequence of operations
5. Failure output

Use copy-pasteable commands where possible. A minimal reproducible example significantly reduces turnaround time.

### Expected vs. Actual Behavior

Clearly separate expected and actual behavior:

- **Expected**: What should happen according to documented behavior
- **Actual**: What happened instead (including full error text and stack trace)

Also include:

- Relevant logs at debug/trace level
- Screenshots only when they add context beyond logs
- Whether the issue is intermittent or deterministic

## 4. Suggesting Enhancements

We welcome feature requests and architectural improvements when they are problem-driven and technically scoped.

When opening an enhancement proposal, include the following.

### Justification

Describe the concrete problem your proposal solves:

- Current limitation or pain point
- Why existing APIs/workarounds are insufficient
- Impact on users (performance, reliability, ergonomics, observability)

### Use Cases

Provide real-world scenarios:

- Typical usage context (service type, throughput profile, deployment model)
- Example API usage and expected behavior
- Backward compatibility considerations
- Migration strategy if behavior changes are required

Proposals with clear operational value and compatibility analysis are prioritized.

## 5. Local Development / Setup

Use the following baseline workflow to prepare a local environment.

### Fork and Clone

1. Fork the repository to your personal GitHub account.
2. Clone your fork locally.
3. Add the upstream remote.

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
git remote add upstream https://github.com/<org-or-owner>/<repo-name>.git
```

### Dependencies

Install project dependencies based on the tech stack:

```bash
# Python projects
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Node.js projects (if applicable)
npm install
```

### Environment Variables

Create local environment configuration from the project template:

```bash
cp .env.example .env
```

Then edit `.env` and set required values (for example log level, formatter profile, output sink endpoints, API keys for integration tests).

### Running Locally

Start the project with the repository-defined entrypoint:

```bash
# Python example
python -m flask --app api/index.py run --host 0.0.0.0 --port 5000

# Node.js example (if applicable)
npm run dev
```

If this repository defines a task runner (`make`, `just`, `tox`, `nox`), prefer those commands for consistency.

## 6. Pull Request Process

Follow this workflow for every code contribution.

### Branching Strategy

Create a dedicated branch from `main` (or the default branch):

- `feature/<short-feature-name>` for new functionality
- `bugfix/<issue-number-or-short-name>` for bug fixes
- `docs/<short-topic>` for documentation-only changes
- `chore/<short-task-name>` for maintenance work

Avoid direct pushes to `main`.

### Commit Messages

This repository enforces Conventional Commits:

- `feat: add async file transport batching`
- `fix: prevent logger recursion in error handler`
- `docs: clarify structured logging configuration`
- `test: add regression case for formatter fallback`

Keep commits focused and logically grouped.

### Upstream Synchronization

Before opening or updating a PR:

```bash
git fetch upstream
git checkout main
git rebase upstream/main
git checkout <your-branch>
git rebase main
```

Resolve conflicts locally and rerun all checks before pushing.

### PR Description

Every PR body must include:

- Linked issue(s) (for example `Closes #123`)
- Problem statement and technical approach
- Scope boundaries and non-goals
- Test evidence (commands executed and results)
- Backward compatibility notes
- Documentation updates (if user-facing behavior changed)

PRs missing context or validation evidence may be sent back for revision.

## 7. Styleguides

Contributions must conform to established code quality standards.

### Linters and Formatters

Use the following tools before submitting:

- **Python**: `Black` (formatting), `Flake8` (linting), `isort` (import ordering)
- **JavaScript/TypeScript (if present)**: `ESLint` and `Prettier`

Run all format and lint targets defined by the repository scripts or CI configuration.

### Architectural and Naming Conventions

Follow these library conventions:

- Keep logging pipeline stages clearly separated (formatting, enrichment, transport)
- Prefer immutable log event payloads where practical
- Use explicit names for severity and sink components (for example `JsonFormatter`, `FileTransport`)
- Preserve backward compatibility for public APIs; add deprecation paths instead of abrupt removals
- Keep module responsibilities narrow; avoid cross-layer coupling

Consistency and readability are required for maintainability.

## 8. Testing

All code changes must include relevant tests.

- New features require unit and/or integration coverage.
- Bug fixes must include a regression test demonstrating the previous failure mode.
- Existing tests must continue to pass.

Run the local test suite before pushing:

```bash
# Python
pytest -q

# Optional quality gates
flake8 .
black --check .
isort --check-only .

# JavaScript/TypeScript (if present)
npm test
npm run lint
npm run format:check
```

If a test is intentionally skipped, document the reason in the PR.

## 9. Code Review Process

After opening a PR, the following review workflow applies:

1. CI checks must pass before maintainer review begins.
2. At least one maintainer with write access reviews the change.
3. A minimum of two approvals is required for non-trivial code changes; one approval may be sufficient for docs-only changes.
4. Review feedback must be addressed with either code updates or clear technical rationale.
5. After updates, request re-review from prior reviewers.
6. Maintainers squash-merge or rebase-merge based on repository policy.

### Review Expectations

- Keep discussions technical, concrete, and respectful.
- Resolve all review threads before merge.
- Do not force-push rewritten history after approval without notifying reviewers.
- Significant scope changes after initial review may require a fresh review cycle.

Thank you for helping improve the project quality and reliability.
