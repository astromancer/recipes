DOCS_SPHINXOPTS = -W

.PHONY: checks pytest docs

checks: lint test docs build

# isort:
# 	uv run isort --profile black --line-length $(PYTHON_LINE_LENGTH) src/ tests/
# 	uv run nbqa isort --profile=black --line-length=$(PYTHON_LINE_LENGTH) notebooks/

lint:
	uv run python -m ruff check, -v

test:
	uv run pytest --cov=src/ --cov-report=term-missing tests/

# alias
pytest: test

docs:
	rm -rf docs/build
	uv run python -m sphinx.cmd.build docs/src/ docs/build/html/ -j4 -W

build:
	uv run python -m builf
