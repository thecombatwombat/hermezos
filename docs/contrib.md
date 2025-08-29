# Contributing to HermezOS

Thank you for your interest in contributing to HermezOS! This document provides guidelines and information for contributors.

## Ways to Contribute

### 1. Report Issues

- **Bug Reports**: Use the [issue tracker](https://github.com/hermezos/hermezos/issues) to report bugs
- **Feature Requests**: Suggest new features or improvements
- **Documentation Issues**: Report unclear or missing documentation

### 2. Contribute Code

- **Fix Bugs**: Look for issues labeled "good first issue" or "bug"
- **Add Features**: Check the roadmap and issue tracker for planned features
- **Improve Documentation**: Help make docs clearer and more comprehensive

### 3. Contribute Rules

- **Domain Expertise**: Share rules for your area of expertise
- **Best Practices**: Contribute industry-standard rules
- **Tool Integration**: Create rules for popular frameworks and tools

### 4. Improve Tests

- **Add Test Cases**: Increase test coverage
- **Test Edge Cases**: Ensure robustness
- **Performance Tests**: Help optimize performance

## Development Setup

### Prerequisites

- Python 3.12+
- Git
- Make (optional, for using Makefile)

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/hermezos/hermezos.git
cd hermezos

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to ensure everything works
make test
```

### Development Workflow

1. **Create a Branch**: `git checkout -b feature/your-feature-name`
2. **Make Changes**: Implement your feature or fix
3. **Add Tests**: Ensure your changes are well-tested
4. **Run Checks**: `make fmt && make lint && make typecheck && make test`
5. **Commit**: Use clear, descriptive commit messages
6. **Push**: Push your branch to GitHub
7. **Create PR**: Open a pull request with a clear description

## Coding Standards

### Python Code

- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Write comprehensive docstrings using Google style
- **Formatting**: Code is automatically formatted with Black
- **Linting**: Follow Ruff rules (extends pycodestyle, pyflakes, etc.)

### Example

```python
def pack_rules(
    self,
    request: PackRequest,
    config: Optional[Config] = None
) -> PackBundle:
    """Pack rules based on the given request.

    Args:
        request: The pack request containing path and filters
        config: Optional configuration override

    Returns:
        A PackBundle containing matched rules and metadata

    Raises:
        PackingError: If packing fails for any reason
    """
    # Implementation here
    pass
```

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

Examples:
```
feat(packer): add support for custom sort keys
fix(cli): handle empty registry directory gracefully
docs(api): update MCP integration examples
```

## Rule Contribution Guidelines

### Rule Quality Standards

1. **Clarity**: Rules should be clear and actionable
2. **Accuracy**: Rules should be technically correct
3. **Helpfulness**: Include hints and references
4. **Testability**: Rules should be verifiable

### Rule Structure

```yaml
schema_version: 1
id: RULE-<domain>-<slug>
name: Descriptive Rule Name
version: 1
status: active
severity: warning
domain: <domain>
intent_tags: [tag1, tag2]
scope:
  file_globs: ["*.ext"]
  languages: [language]
triggers:
  - type: path_contains
    value: "pattern"
detectors:
  - type: regex
    pattern: "regex_pattern"
action:
  type: manual
  steps:
    - "Step 1"
    - "Step 2"
hint: Brief helpful hint
references:
  - doc_url: https://example.com/docs
    note: Additional context
provenance:
  author: Your Name
  created: "2024-01-15T10:00:00Z"
  last_updated: "2024-01-15T10:00:00Z"
```

### Testing Rules

1. **Create Test Cases**: Add test files that should trigger your rule
2. **Verify Detection**: Ensure your rule correctly identifies violations
3. **Test Edge Cases**: Consider various scenarios and edge cases
4. **Document Examples**: Include examples in the rule description

## Documentation

### Documentation Standards

- Use Markdown for all documentation
- Include code examples where helpful
- Keep documentation up to date with code changes
- Use clear, concise language

### Documentation Structure

```
docs/
├── index.md              # Main documentation index
├── installation.md       # Installation instructions
├── getting-started.md    # Quick start guide
├── authoring-rules.md    # How to write rules
├── cli-reference.md      # CLI command reference
├── configuration.md      # Configuration options
├── python-library.md     # Python API documentation
├── mcp-integration.md    # MCP integration guide
├── extending.md          # How to extend HermezOS
├── troubleshooting.md    # Common issues and solutions
├── android/              # Android-specific docs
│   ├── index.md
│   └── gradle_plugins.md
└── api-reference.md      # API reference
```

## Testing

### Test Structure

```
tests/
├── test_models.py        # Test data models
├── test_storage.py       # Test storage layer
├── test_packer.py        # Test packing logic
├── test_cli.py           # Test CLI commands
├── test_mcp.py           # Test MCP server
├── data/                 # Test data files
│   ├── golden_packbundle.json
│   └── sample_rules/
└── conftest.py           # Pytest configuration
```

### Writing Tests

```python
import pytest
from hermezos.models import RuleCard, Status

def test_rule_card_validation():
    """Test rule card validation."""
    # Test valid rule
    rule = RuleCard(
        schema_version=1,
        id="RULE-test-example",
        name="Test Rule",
        version=1,
        status=Status.ACTIVE,
        severity=Severity.INFO,
        domain="test",
        action=Action(type=ActionType.MANUAL, steps=["Do something"])
    )

    assert rule.id == "RULE-test-example"
    assert rule.status == Status.ACTIVE

def test_invalid_rule_id():
    """Test invalid rule ID handling."""
    with pytest.raises(ValidationError):
        RuleCard(
            schema_version=1,
            id="invalid-id",  # Missing RULE- prefix
            name="Test Rule",
            version=1,
            status=Status.ACTIVE,
            severity=Severity.INFO,
            domain="test",
            action=Action(type=ActionType.MANUAL, steps=["Do something"])
        )
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::test_rule_card_validation
```

## Release Process

### Version Numbering

HermezOS follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `src/hermezos/__init__.py`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Create git tag
- [ ] Create GitHub release
- [ ] Update documentation

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## License

By contributing to HermezOS, you agree that your contributions will be licensed under the MIT License.

## Getting Help

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Search existing [issues](https://github.com/hermezos/hermezos/issues)
- **Discussions**: Use [GitHub Discussions](https://github.com/hermezos/hermezos/discussions) for questions
- **Discord**: Join our community Discord (link TBD)

Thank you for contributing to HermezOS! 🎉