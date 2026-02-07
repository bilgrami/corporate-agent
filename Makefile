.PHONY: help setup test lint format build clean run

help:            ## Show this help
	@sh scripts/help.sh $(MAKEFILE_LIST)

setup:           ## Create venv and install dependencies
	@sh scripts/setup.sh

test:            ## Run tests
	@sh scripts/test.sh

lint:            ## Run linter (ruff + mypy)
	@sh scripts/lint.sh

format:          ## Format code (ruff format)
	@sh scripts/format.sh

build:           ## Build distribution
	@sh scripts/build.sh

clean:           ## Remove build artifacts
	@sh scripts/clean.sh

run:             ## Run the CLI
	@sh scripts/run.sh
