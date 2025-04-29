This file is a standard representation of guidelines and rules for coding agents like Windsurf, Claude Code and Cursor. It replaces agent-specific files like `.windsurfrules`, `CLAUDE.md` etc.

# Jentic Project Development Guide for Coding Agents

## Code Style Guidelines
- Python version: 3.10+
- Line length: 100 characters
- Strict typing: Required for all functions (disallow_untyped_defs=true)
- Imports: Use isort with black profile (sorted alphabetically)
- Formatting: Use black for consistent code style
- Linting: ruff (E, F, B, W, I, N, UP, YTT, S rules)
- Type checking: mypy with strict settings (no_implicit_optional=true, strict_optional=true)
- Documentation: Triple double-quotes for docstrings
- Naming: snake_case for variables/functions, PascalCase for classes
- Error handling: Prefer explicit error handling with typed exceptions
- File size: Files should not exceed 600 lines. If they do, consider splitting them into logical components
  - Splitting strategy: Extract cohesive functionality into separate modules
  - Aim for single responsibility per module when refactoring large files

## Code Organization
- Keep concerns separated into different modules/components
- Maintain clean interfaces between components
- Write modular, testable code with single responsibilities
- Add extensive logging with appropriate log levels

### Testing Best Practices
- Tests should be deterministic and independent of each each other
- Mock external dependencies and services by default
- Each test should focus on a specific functionality
- Use appropriate fixtures to reduce test setup code
- Prioritize test readability and maintainability

## Commands
[commands]
# Transform Python commands to use PDM
python = pdm run python
pytest = pdm run pytest
pip = pdm run pip
black = pdm run black
isort = pdm run isort
mypy = pdm run mypy
ruff = pdm run ruff

# PDM script shortcuts
test = pdm run test
lint = pdm run lint

# Project information
[project]
name = Jentic SDK
description = Jentic SDK for API workflow execution and LLM tool generation
python_version = 3.10+
package_manager = pdm

# Prompt suggestions for AI assistants
[prompt]
test_command = pdm run test
lint_command = pdm run lint
preferred_python_style = black, isort, strict typing
line_length = 100
