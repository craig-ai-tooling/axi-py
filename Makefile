# axi-py: one file (axi.py) that each Python AXI vendors. Nothing here is installed.
.PHONY: test lint check

test:
	python3 -m unittest discover -s tests

lint:
	ruff check .

check: lint test
