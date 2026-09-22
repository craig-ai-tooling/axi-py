# AGENTS.md

Primary context for every agent working in this repo. Read [README.md](./README.md)
first; it says what this is and how a change reaches the tools.

## Rules

- **Output is a contract.** Four tools print through `axi.py`, and agents and scripts
  parse what they print. A change to any expected string in `tests/test_axi.py` changes
  every tool's output. Make it only with evidence that the current output is wrong, and
  say which tool's caller it affects.
- **Stdlib only, Python 3.10+.** A tool's zipapp must keep having no dependencies.
- **No tool-specific code.** A helper belongs here only when two tools already carry the
  same copy of it. Anything else stays in the tool.
- **Every behaviour change bumps `__version__`** and is tagged `v<version>` after it
  merges. `vendor.py` refuses to vendor from an untagged checkout.
- **Never edit a vendored copy in a tool repo.** Its `tests/test_axi_vendored.py` fails on
  purpose. Change it here, tag it, re-vendor.

## Commands

| task | command |
|---|---|
| lint + test | `make check` |
| vendor into a tool | `make vendor-axi AXI_PY_REF=<tag>`, run in the tool repo |
