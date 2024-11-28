SSAP_DIR = ssap_dir

.PHONY: all
.DEFAULT_GOAL = help

.PHONY: clean
clean:
	rm -f .coverage
	rm -f requirements.txt
	rm -rf .pytest_cache
	rm -rf dist
	rm -rf reports
	rm -f poetry.lock
	rm -rf $(SSAP_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: dist-clean
dist-clean: clean ## Remove all build and test artifacts and the virtual environment
	rm -rf .venv

.PHONY: build
build: ## Create the virtual environment and install development dependencies
	python -m poetry install

.PHONY: update
update: ## Update dependencies
	python -m poetry update

.PHONY: test
test: ## Execute test cases
	python -m poetry run pytest

.PHONY: precommit
precommit:
	pre-commit install
	pre-commit run --all-files

.PHONY: cover
cover: ## Execute test cases and produce coverage reports
	python -m poetry run pytest --cov . --junitxml reports/xunit.xml \
		--cov-report xml:reports/coverage.xml --cov-report term-missing

.PHONY: ssap
ssap: ## Generates requirements.txt file
	@echo "Generating requirements.txt..."
	mkdir -p $(SSAP_DIR)
	pip install poetry-plugin-export
	python -m poetry export --without-hashes -o requirements.txt
	python -m poetry export -f requirements.txt --without-hashes --output $(SSAP_DIR)/pip_dependency_tree.txt
	@echo "requirements.txt content:"
	@cat requirements.txt

.PHONY: ci-prebuild
ci-prebuild:
	python -m pip install poetry setuptools
	cat /dev/null > requirements.txt

.PHONY: package
package:
	python -m poetry build --format=wheel
	mkdir -p dist

.PHONY: ci
ci: clean build package

.PHONY: format
format:
	ruff format .

.PHONY: lint
format:
	ruff check .

.PHONY: help
help: ## Show make target documentation
	@awk -F ':|##' '/^[a-zA-Z0-9_\-]+:.*##/ { \
	printf "\033[36m%-30s\033[0m %s\n", $$1, $$NF \
	}' $(MAKEFILE_LIST)
