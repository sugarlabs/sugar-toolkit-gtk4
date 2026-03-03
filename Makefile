.PHONY: help install test test-coverage format clean build upload check example tarball

help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install package
	pip install --root-user-action=ignore .

test:  ## Run all tests
	pytest tests/ -v

test-coverage:  ## Run tests with coverage report
	pytest tests/ -v --cov=src/sugar --cov-report=html --cov-report=term

format:  ## Format code with black
	black src tests examples

format-check:  ## Check code formatting without changes
	black --check src tests examples

clean:  ## Remove build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build the package
	python -m build

tarball: build  ## Build source tarball
	@echo "Creating tarball..."
	python -m build --sdist
	@echo "Tarball created in dist/"
	@ls -la dist/*.tar.gz

check:  ## Check distribution with twine
	twine check dist/*

upload-test:  ## Upload to Test PyPI
	twine upload --repository testpypi dist/*

upload:  ## Upload to PyPI
	twine upload dist/*

example:  ## Run the basic example activity
	cd examples && python basic_activity.py

test-toolkit:  ## Run sugar module as a script
	python -m sugar4

dev-test: clean test format-check  ## Run all development checks
	@echo "All development checks passed!"

dev-build: clean build check  ## Build and check package
	@echo "Package built and checked successfully!"

ci-test:  ## Simulate CI pipeline
	@echo "Running CI test simulation..."
	make clean
	make install-dev
	make test-coverage
	make build
	make check
	@echo "CI simulation completed successfully!"
