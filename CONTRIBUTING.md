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
