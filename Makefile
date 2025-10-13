# Makefile for NewsRaag Crawler Test Pipeline
.PHONY: help test test-unit test-integration test-all test-fast test-smoke test-ci clean coverage

PYTHON := python
PYTEST := $(PYTHON) -m pytest
TESTS_DIR := tests
PYTEST_OPTS := --tb=short -v

help: ## Show available commands
	@echo "NewsRaag Crawler Test Pipeline"
	@echo "=============================="
	@echo ""
	@echo "Quick Commands:"
	@echo "  make test           # Run all tests (dashboard view)"
	@echo "  make test-fast      # Run fast tests only"
	@echo "  make test-unit      # Run unit tests"
	@echo "  make test-smoke     # Run smoke tests"
	@echo "  make coverage       # Generate coverage report"
	@echo "  make clean          # Clean test artifacts"

test: ## Run all tests (main dashboard)
	$(PYTEST) $(TESTS_DIR) $(PYTEST_OPTS)

test-fast: ## Run fast tests only
	$(PYTEST) -m "fast and not slow" $(PYTEST_OPTS) --no-cov

test-unit: ## Run unit tests
	$(PYTEST) $(TESTS_DIR)/unit $(PYTEST_OPTS)

test-integration: ## Run integration tests
	$(PYTEST) $(TESTS_DIR)/integration $(PYTEST_OPTS)

test-smoke: ## Run smoke tests
	$(PYTEST) -m smoke $(PYTEST_OPTS) --no-cov

test-llm: ## Run LLM tests
	$(PYTEST) $(TESTS_DIR)/llm $(PYTEST_OPTS)

coverage: ## Generate coverage report
	$(PYTEST) $(TESTS_DIR) $(PYTEST_OPTS) --cov-report=html --cov-report=term-missing

clean: ## Clean test artifacts
	rm -rf .pytest_cache __pycache__ .coverage htmlcov coverage.xml test_reports
	find . -name "*.pyc" -delete
