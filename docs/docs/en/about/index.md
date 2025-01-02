---
hide:
  - navigation
---

# About
Welcome to the "About" section! Here you will find information about **Rapidy**.

## About the Project
### Owner
My name is **Daniil Grois** **<a href="https://github.com/daniil-grois" target="_blank">@daniil-grois</a>**, and I am the creator, owner, and lead developer of **Rapidy**.

Thank you for your interest in the project! I hope **Rapidy** helps you build your own solutions.

I welcome your ideas and contributions—feel free to open **Pull Requests**, and I will do my best to integrate your work into **Rapidy**.

Let's make the world a better place together! 🚀

### Maintenance and Development
Current maintainers of **Rapidy**:

- Daniil Grois - **<a href="https://github.com/daniil-grois" target="_blank">@daniil-grois</a>**
- Lev Zaplatin - **<a href="https://github.com/LevZaplatin" target="_blank">@LevZaplatin</a>**
- Nikita Tolstoy - **<a href="https://github.com/Nikita-Tolstoy" target="_blank">@Nikita-Tolstoy</a>**

The maintainers define the development strategy, prioritize enhancements, and manage the project's **roadmap**.

## Version Numbering
**Rapidy** follows the **<a href="https://semver.org/" target="_blank">Semantic Versioning standard</a>**.

```
Version format: MAJOR.MINOR.PATCH

MAJOR – incremented for incompatible API changes
MINOR – incremented for new functionality that is backward compatible
PATCH – incremented for bug fixes that do not break compatibility
Additional labels are available for pre-release and build metadata.
```

## How to Contribute
Want to help improve **Rapidy**? Here’s how!

### Workflow
1. Fork the **Rapidy** repository <a href="https://github.com/rapidy-org/rapidy/fork" target="_blank">here</a>.
2. Clone your fork locally:
   ```sh
   git clone https://github.com/your-username/rapidy.git
   ```
3. (Optional) Install **Poetry** if not already installed:
   ```sh
   pipx install poetry
   ```
   For more installation options, check the [Poetry documentation](https://python-poetry.org/docs/#installation).
4. Navigate to the repository folder.
5. Set up the environment:
   ```sh
   poetry env use python3.9
   ```
6. Install dependencies:
   ```sh
   poetry install --with dev,test,docs
   ```
7. Install pre-commit hooks:
   ```sh
   pre-commit install
   ```
8. Activate the virtual environment:
   ```sh
   poetry shell
   ```
9. Run tests to ensure everything is working:
   ```sh
   pytest
   ```
10. Create a new branch. All branches should start with a `<prefix>/` indicating the type of change.
    For example: `bug/fix-any` / `feature/my-awesome-feature`.
11. Make your code changes.
12. Write tests for your changes.
13. Run linters and format the code:
    ```sh
    pre-commit run --all-files
    ```
14. Commit your changes using the format `<branch number>: <commit message>`.
15. Push your changes to your fork:
    ```sh
    git push
    ```
16. Open a **Pull Request** <a href="https://github.com/rAPIdy-org/rAPIdy/issues/new" target="_blank">here</a>,
    providing a clear description in the format `<branch number>: <PR description>`.

### Code Style
1. The code must be fully type-annotated.
2. All changes must be covered by tests.
3. The code should follow **PEP 8**.
4. Backward compatibility should be maintained whenever possible.
5. Add yourself to `CONTRIBUTORS.md` and this documentation section.
6. Update the documentation _(if needed)_.

### Discussion
- <a href="https://t.me/+PsAvQnlVIcJlOGU6" target="_blank">Telegram (EN)</a>
