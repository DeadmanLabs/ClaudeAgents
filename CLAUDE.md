# ClaudeAgents Development Guide

## Build & Test Commands
- Python: `python -m pytest tests/` (all tests), `python -m pytest tests/test_file.py::test_name` (single test)
- JavaScript: `npm test` (all tests), `npm test -- -t "test name"` (single test)
- Lint Python: `ruff check .`
- Lint JS: `npm run lint`
- Type check Python: `mypy .`
- Type check JS: `npm run typecheck`

## Code Style Guidelines
- Python: Black formatting, typed with annotations, snake_case for variables/functions
- JavaScript: ESLint + Prettier, TypeScript with strict mode, camelCase for variables/functions
- Imports: Group by standard lib, third-party, local modules with a blank line between groups
- Classes: PascalCase for classes, follow single responsibility principle
- Error handling: Proper try/catch with specific error types
- Documentation: Docstrings for all functions/classes, JSDoc for JavaScript
- Logging: Use structured logging with appropriate levels for all operations