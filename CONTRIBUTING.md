# Contributing Guidelines

Thank you for considering contributing to this project! Your help is greatly appreciated. Please follow these guidelines
to ensure a smooth contribution process.

## Table of Contents

- [Getting Started](#getting-started)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)

## Getting Started

1. Fork the repository and clone your fork.
2. (Optional) Install Poetry if not already installed:
    ```sh
    pipx install poetry
    ```
    For more installation options, refer to the [Poetry documentation](https://python-poetry.org/docs/#installation).
3. Create a virtual environment:
    ```sh
    poetry env use python3.12
    ```
4. Install dependencies using Poetry:
    ```sh
    poetry install --with dev,test,docs
    ```
5. Install pre-commit hook
    ```sh
    pre-commit install
    ```
6. Activate the virtual environment:
   ```sh
   poetry shell
   ```

## Code Style

- Follow **PEP 8** for Python code.
- Format and verify your code using pre-commit, which includes pre-configured linters (`mypy`, `ruff`):
    ```shell
    pre-commit run --all-files
    ```
- Respect the **ruff** configuration in `pyproject.toml`.

## Testing

This project supports **aiohttp**, and **pydantic**, so ensure your changes are compatible with all frameworks where
applicable.

- Use **pytest** for testing:
   ```sh
   pytest ./tests
   ```
- Ensure **100% test coverage** where possible.
- Mock external dependencies appropriately.
- Respect the test configuration in `pyproject.toml`.

## Submitting Changes

1. Create a new branch:
   ```sh
   git checkout -b feature/my-feature
   ```
2. Make your changes and commit with a clear message:
   ```sh
   git commit -m "feature/my-feature: Add new feature."
   ```
3. Push to your fork and open a **Pull Request (PR)**.
4. Ensure your PR description includes:
   - A summary of changes
   - Relevant issue references
   - Any necessary documentation updates

## Documentation

- Use **MkDocs** for documentation where applicable.
- Ensure that docstrings follow the **Google docstring style**.
- Follow the documentation conventions set in `pyproject.toml`.

## Issue Reporting

- Before opening an issue, check if it already exists.
- Provide clear steps to reproduce bugs.
- Suggest possible solutions if applicable.

Thank you for contributing! 🎉
