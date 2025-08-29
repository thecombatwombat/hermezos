.PHONY: install fmt typecheck test help

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Create venv and install package with dev dependencies"
	@echo "  fmt         - Format code with black and ruff"
	@echo "  typecheck   - Run mypy type checking"
	@echo "  test        - Run tests with pytest"
	@echo "  help        - Show this help message"

# Installation
install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -e .[dev]

# Code formatting
fmt:
	black src/ tests/
	ruff check --fix src/ tests/

# Linting
lint:
	ruff check src/ tests/

# Type checking
typecheck:
	mypy src/hermezos/

# Testing
test:
	pytest tests/ -q

test-cov:
	pytest tests/ -v --cov=hermezos --cov-report=term-missing --cov-report=html

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete

# Development setup
setup-dev: clean install-dev
	pre-commit install

# CI/CD targets
ci: fmt lint typecheck test-cov

# Quick development cycle
dev: fmt lint typecheck test