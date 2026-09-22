# axi-py

The output and exit-code contract every Python AXI tool shares, in one file: `axi.py`.
Stdlib only, Python 3.10+.

It holds the TOON encoder (`toon`, `_tv`), `emit`, `nxt`, `die`, `size_hint`, and the
exit codes `E_OK` through `E_PARTIAL` from ai-lawnmower's `docs/axi-contract.md`.

## Who uses it

| tool | package | vendored copy |
|---|---|---|
| [opp-axi](https://github.com/craig-ai-tooling/opp-axi) | `opp_axi` | `opp_axi/axi.py` |
| [palette-axi](https://github.com/craig-ai-tooling/palette-axi) | `palette_axi` | `palette_axi/axi.py` |
| [monday-axi](https://github.com/craig-ai-tooling/monday-axi) | `monday_axi` | `monday_axi/axi.py` |
| [launchpad-axi](https://github.com/craig-ai-tooling/launchpad-axi) | `launchpad_axi` | `launchpad_axi/axi.py` |

## Why vendored, not installed

Each tool ships as a single-file zipapp with no dependencies, installed by curling a
release asset. A pip dependency would break that. So each tool carries a copy inside its
own package, and a generated test, `tests/test_axi_vendored.py`, fails if that copy is
edited in place. An in-place edit is how opp-axi and palette-axi had already started to
drift while carrying a comment that said "copied verbatim, both tools must agree".

There is no Python AXI SDK to use instead. Checked 9/22/26: PyPI `axi-sdk-py`,
`axi-sdk`, `python-axi` and `axi` are all 404. `toon-format` 0.1.0's `encode()` raises
`NotImplementedError`. `python-toon` 0.1.3 works, but it escapes a quote as `\"` and
prints None as `null`, where these tools double the quote and print None as an empty
cell. Adopting it would change every tool's output.

## Changing it

1. Edit `axi.py`, bump `__version__`, and pin the new behaviour in `tests/test_axi.py`.
   `make check` must pass.
2. Merge, then tag `v<__version__>` on main and push the tag.
3. In each tool: `make vendor-axi AXI_PY_REF=v<version>`, run its tests, open a PR.

`vendor.py` refuses to run anywhere but a clean checkout of the tag matching
`__version__`, because the header it writes names that tag and the file's sha256. A
tool's `make vendor-axi` clones this repo at the pinned tag and runs it, so step 3 needs
no local checkout of this repo.

`python3 vendor.py <tool-root> <package> --dev` vendors an untagged copy for a local
try. The generated test rejects a `-dev` header, so that copy cannot pass the tool's CI.
