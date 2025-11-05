# AGENTS.md

This file provides essential guidelines for agentic coding agents in the SAM-FTP CLI repository.

## Build, Lint, and Test Commands
- **Install dependencies:** `rye sync`
- **Lint code:** `rye lint`
- **Format code:** `rye fmt`
- **Run all tests:** `pytest`
- **Run a single test:** `pytest path/to/test_file.py::test_function_name`
- **Run from source:** `python -m samftp_cli.main`

## Code Style & Development Practices
- Use strict type hints for all functions and variables.
- Organize imports: standard library, third-party, then local modules.
- Format code with Ruff; follow PEP8 and project conventions.
- Use descriptive variable and function names.
- Modularize code: keep models, services, controllers, and utilities in separate files.
- Manage configuration via environment variables (`.env.example`).
- Handle errors robustly; use custom exceptions and log with full context/traceback.
- Document complex logic with detailed comments and docstrings.
- Use async/await for all I/O operations.
- Use Rich for all terminal output (avoid raw print).
- Test all major features and error scenarios with pytest.
- Use Click for CLI commands and subcommands.
- Dependency management via Rye and virtual environments.

## Testing Checklist
- Test first-run experience, server selection, authentication, navigation, playback, downloads, batch selection, bookmarks, cache, player persistence, background playback, error scenarios, CLI flags, and all subcommands.
