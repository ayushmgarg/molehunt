.PHONY: test bench serve lint

test:
	uv run pytest -q

bench:
	uv run molehunt bench

serve:
	uv run molehunt serve

lint:
	uv run ruff check molehunt tests
