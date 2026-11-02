# Contributing to Open5G2GO

Thank you for your interest in contributing to Open5G2GO! This document provides guidelines for contributing to the project.

## Contributor License Agreement

Before your first contribution can be merged, you must sign our Contributor License Agreement (CLA). This is handled automatically via CLA Assistant when you open a pull request.

**[Read the full CLA](CLA.md)**

The CLA ensures that:
- You have the right to submit your contribution
- Waveriders Collective Inc. can distribute your contribution under the project license
- The project can be dual-licensed if needed in the future

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [GitHub Issues](https://github.com/Waveriders-Collective/open5G2GO/issues)
2. If not, create a new issue with:
   - Clear title describing the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Docker version, etc.)

Do not report security vulnerabilities as public issues. See [SECURITY.md](SECURITY.md)
for how to report them privately.

### Suggesting Features

1. Check existing issues and discussions for similar suggestions
2. Open a new issue with the "enhancement" label
3. Describe the feature and its use case

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Run tests: `poetry run pytest`
5. Run linters: `poetry run ruff check .`
6. Commit with a clear message
7. Push to your fork
8. Open a pull request

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use `ruff` for linting
- Use `black` for formatting

### TypeScript/React

- Use TypeScript strict mode
- Follow ESLint configuration
- Use functional components with hooks

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep first line under 72 characters
- Reference issues when applicable

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/open5G2GO.git
cd open5G2GO

# Install Python dependencies
poetry install

# Install frontend dependencies
cd web_frontend && npm install && cd ..

# Run tests
poetry run pytest

# Run linters
poetry run ruff check .
```

## Running CI Checks Locally

GitHub Actions runs checks on pull requests and pushes to `main`. The Python
matrix uses 3.11, 3.12, and 3.15 on Ubuntu; frontend checks use Node.js 26. Container
CI exercises the same Buildx, metadata, and build Actions as publishing, with
registry pushes disabled. The Docker publishing workflow runs separately after
pushes to `main`.

Use an isolated Python environment to match CI's test and lint tools:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ci.txt
poetry check --lock
poetry install --with dev --no-interaction --no-ansi
poetry run ruff check .
poetry run python -m pytest -q
```

Application and development packages are pinned in `poetry.lock`; CI and the
backend image install that lock without regenerating it. The SIM key tests
require `cryptography`, included in the locked development dependencies.
Installer and SIM tests use mocks and temporary
files; they do not install packages or start Docker. The interactive SIM tests
require a POSIX terminal, so run them on Linux or macOS. Pytest's importlib mode
and the explicit `tests` package keep test modules separate from application imports.

From the repository root, with Bash, ShellCheck, and Docker Compose installed:

```bash
for script in install.sh scripts/*.sh; do
  bash -n "$script"
done
shellcheck --severity=warning install.sh scripts/*.sh
for config in docker-compose*.yml; do
  docker compose --env-file env.example -f "$config" config --quiet
done
```

Compose validation uses the example configuration and does not start containers.

```bash
cd web_frontend
npm ci
npm run lint
npm run build
```

Security checks run separately from functional CI. To reproduce the dependency audits:

```bash
# From the repository root, with the CI tooling installed above
python scripts/audit-python-lock.py
pip-audit --requirement requirements-ci.txt
cd web_frontend
npm audit --omit=dev --audit-level=low
npm audit --audit-level=high
```

Production npm findings fail at every severity. The full npm audit and dependency
review gate high/critical findings across development and runtime dependencies;
the known moderate lint-tool advisory is tracked in
[issue #35](https://github.com/Waveriders-Collective/open5G2GO/issues/35) and is still
reported, not suppressed. Python audits fail on any known vulnerability.
The lock audit checks every locked package version without environment markers,
including alternatives for other Python versions and operating systems.
Dependency review additionally requires the repository dependency graph and the
repository variable `DEPENDENCY_REVIEW_ENABLED=true`; the full audits always run.
CodeQL runs the extended security queries and uploads results to code scanning;
a successful scan means analysis completed, not that no alerts exist. Merge
enforcement depends on repository rules configured by a maintainer.

## Dependency Updates

Dependabot groups version updates for Python, npm, Docker, and GitHub Actions
into one weekly pull request using the `dependencies` multi-ecosystem group in
[`.github/dependabot.yml`](.github/dependabot.yml). Major updates participate too;
grouping does not imply automatic approval or merging. Validate the combined
lockfiles, application checks, package audits, and affected containers before merge.

GitHub handles security updates separately from scheduled version updates and
cannot group them across ecosystems. The configuration groups security fixes
within each ecosystem so they can arrive without waiting for the weekly batch.
See [GitHub's security-update grouping limits](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates).

Explicit version holds document upgrades that need compatibility work, including
the frontend toolchain/React migrations and the Open5GS base-OS migration. A hold
can also exclude a security fix in that version range: continue reviewing alerts
and audits, and remove the hold as part of the tested migration. Keep working
updates together; document any deferred update and its failing check rather than
merging it solely because other dependencies pass.
The [November 2026 consolidation review](docs/dependency-review-2026-11-01.md)
records the current holds, compatibility fixes, and validation limits.

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Add yourself to CONTRIBUTORS.md (if it exists)
4. Request review from maintainers
5. Address review feedback
6. Once approved, a maintainer will merge your PR

## Code of Conduct

Be respectful and constructive in all interactions. We're all here to build something useful together.

## Questions?

- Open a [GitHub Discussion](https://github.com/Waveriders-Collective/open5G2GO/discussions)
- Check existing documentation

Thank you for contributing!
