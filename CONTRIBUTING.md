# Contributing to rhkpy

## Development setup

```bash
git clone https://github.com/zrbyte/rhkpy.git
cd rhkpy
pip install -e . pytest
```

The full test suite needs the `.sm4` measurement files in the (gitignored)
`test/` directory at the repo root. These files are proprietary and live only
on the maintainer's machine, so the complete suite runs locally.

```bash
python -m pytest                  # full suite
python -m pytest -m "not slow"    # skip the headless-browser thumbnail test
```

### Run tests automatically on every change

Enable the versioned git hooks once per clone:

```bash
git config core.hooksPath .githooks
```

After that, every `git commit` runs the fast suite (`-m "not slow"`, ~10 s)
and every `git push` runs the full suite; both abort on failure
(`--no-verify` bypasses in an emergency). If your Python is not the default
conda env, point the hooks at it with `export RHKPY_TEST_PYTHON=/path/to/python`.

### Continuous integration

`.github/workflows/tests.yml` runs the **data-free tier** on GitHub Actions
(package install on Python 3.10/3.13, import, the API-surface pin, the
synthetic-data analysis tests, and the docs build). Tests that need the
`.sm4` files skip themselves cleanly when `test/` is absent, so CI stays
green without the proprietary data — the golden-master characterization runs
are the responsibility of the local hooks.

## Architecture

- `rhkpy/core.py` — the `rhkdata` class. Thin: loading, dispatching and the
  public methods; the work happens in the submodules below.
- `rhkpy/io/` — reading `.sm4` files. `io/sm4.py` is the binary reader
  (ported from the spym project) plus the conversion to a raw xarray Dataset
  (`spymdata`).
- `rhkpy/builders/` — turn `spymdata` into the user-facing `image` and
  `spectra` Datasets. `detect.py` classifies the file
  (datatype: image/map/line/spec; spectype: iv/iz), `spectra.py` holds the
  geometry builders, `metadata.py` the metadata attachment, and
  `builders/__init__.py` the `(datatype, spectype)` registry.
- `rhkpy/analysis/` — fitting (`fitting.py`), Dataset operations (`ops.py`),
  image leveling (`level.py`).
- `rhkpy/plotting/` — `quickplot.py` (the `qplot` panels and its layout
  registry), `navigation.py`, `thumbnails.py`.
- `rhkpy/rhkpy_loader.py`, `rhkpy/rhkpy_process.py` — backward-compatibility
  shims re-exporting the historical names. Do not add new code here.
- `spym/` — legacy vendored copy of the spym project, used ONLY by
  `tests/test_sm4_loader.py` to cross-validate `rhkpy.io.sm4`. Not packaged,
  never imported from `rhkpy/`.

## Backward-compatibility policy

The public API and the numerical output are pinned by golden-master tests:

- `tests/golden/api_surface.json` — every public `rhkpy.<name>` with its
  signature. Any addition, removal or signature change fails
  `test_api_surface.py`.
- `tests/golden/fixtures/*.json` — the full structure and content hashes of
  every fixture loaded with `rhkdata()`.

If a test fails after an *intentional* change, regenerate with
`python tests/make_golden.py` and review the golden diff in your PR — the
diff is the API-change review.

## Adding a new measurement type

Supporting a new `(datatype, spectype)` combination is registry work:

1. **Detection** — teach `builders/detect.py:_checkdatatype` to recognize the
   RHK page/line type.
2. **Spectra builder** — add an entry to `_SPECTYPE_CONFIG` in
   `builders/spectra.py` (channels, sweep coordinate, scan direction labels)
   and reuse a geometry builder (`_build_map` / `_build_line` /
   `_build_spec`), or add a new geometry function if the layout is new.
3. **Metadata** — reuse `_add_spectra_metadata` (flags for scan angle and
   bias-coordinate units) in `builders/metadata.py`, or extend it.
4. **Register** — add the `(datatype, spectype) -> (builder, metadata)` pair
   to `_BUILDER_REGISTRY` in `builders/__init__.py`.
5. **Quick plot** — add a layout to `_QPLOT_LAYOUTS` in
   `plotting/quickplot.py`, composing the shared helpers
   (`_fwbw_lineplot`, `_mean_signal_image`).
6. **Pin it** — drop a small example `.sm4` file into `test/`, run
   `python tests/make_golden.py`, and commit the new golden snapshot.

## Conventions

- Failures raise exceptions, so that code using rhkpy can't miss them. Warnings
  and other load-time diagnostics go through `logging.getLogger('rhkpy')`; prints
  are reserved for user-facing command output (e.g. `print_info`, `genthumbs`
  progress).
- Indentation: tabs (matching the existing code).
- Historical quirks that the golden tests pin (e.g. the position-dim order of
  iv vs iz maps) are marked with comments at the source — do not "fix" them
  without a deliberate, documented behavior change.
