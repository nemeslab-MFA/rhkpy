# Instructions for AI agents working on rhkpy

For how to use rhkpy rather than change it, read `rhkpy/AGENT_GUIDE.md`. `CONTRIBUTING.md` has the architecture and conventions.

## Rules

- **Measurement data stays local.** The `.sm4` files in `test/` are proprietary and gitignored. Never commit them, copy them elsewhere, or paste their contents into anything public.
- **Data loading must not change.** `rhkpy/io/sm4.py` and the reshaping in `rhkpy/builders/` match what the instrument and other software show. Things that look like bugs there, such as `reshape(xsize, ysize)` on image pages, are deliberate. Don't change them without the maintainer's explicit direction.
- **Measurement-domain decisions are the maintainer's.** For example, how to lay out data from a new measurement mode, or what a sweep direction label means. Ask rather than guess.
- **Commit and push only when asked.** Work on `devel`; `master` is what's released.

## Testing

Run the full suite locally after every change, using the `datadigger` conda environment:

```bash
/opt/anaconda3/envs/datadigger/bin/python -m pytest
```

- `python -m pytest -m "not slow"` skips the test that starts a browser.
- CI has no `.sm4` files, so tests that need them skip there. Passing CI doesn't show that data loading still works; the local suite does.
- Enable the hooks once per clone with `git config core.hooksPath .githooks`. The pre-commit hook tests the staged files, and the pre-push hook runs the full suite.

## Goldens

`tests/golden/` pins the public API, the structure of loaded data and hashes of every array.

- A golden failure means behaviour changed. Find out why before doing anything else.
- Regenerate with `python tests/make_golden.py` only after an intentional change, and review the diff. It rewrites every golden, so anything other than the files you expected to change is a bug.
- A new `.sm4` file in `test/` fails the suite until it has a golden. A golden only records current output, so it doesn't show that the data is correct.
- New public names change `tests/golden/api_surface.json`, and this is expected.

## Conventions

- Tabs for indentation, except code ported verbatim from spym, which keeps its own.
- Failures raise exceptions. Warnings go through `logging.getLogger('rhkpy')`. Use `print` only for output a command exists to produce.
- Don't add dependencies without asking.
- Add new measurement types through `_BUILDER_REGISTRY` in `rhkpy/builders/__init__.py`, following "Adding a new measurement type" in `CONTRIBUTING.md`.
- Record user-visible changes in `CHANGELOG.md` and keep `rhkpy/AGENT_GUIDE.md` true; its Python examples run as tests.
