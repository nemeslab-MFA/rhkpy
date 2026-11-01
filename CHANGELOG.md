# Changelog

## 1.5.0 (unreleased)

Makes rhkpy usable without a notebook or browser, by scripts and AI agents. Data loading is unchanged.

### Changed, may need changes in your scripts

Failures now raise exceptions, instead of printing a message and returning `None` or a half-built object:

- `rhkdata()` raises `FileNotFoundError` for a missing file and `ValueError` for an invalid one. Check for these instead of `datatype is None`.
- `mrep()`, `msw()`, `coord_to_absolute()`, `polyflatten()` and `rhkpy.polyflatten` raise `TypeError` when the data type doesn't apply.
- `coord_to_absolute()` on a line spectrum raises `NotImplementedError`.
- `navigation()` raises `ValueError` when there is nothing to plot.

`load_spym` and `load_dataset` still print a message and return `None` for an invalid file.

### Added

- `rhkdata.summary()`: a JSON-ready description of a measurement.
- `rhkdata.preview()`: a static picture with matplotlib, needing no browser or display.
- `rhkpy.scan()`: summaries of every `.sm4` file in a folder.
- A command line tool: `rhkpy info`, `rhkpy scan`, `rhkpy preview` and `rhkpy guide`. It also runs as `python -m rhkpy`.
- `rhkpy.agent_guide()`: a guide for scripts and AI agents, shipped with the package.
- A useful `repr()` for `rhkdata`.
- `colorcet` is now declared as a dependency. It was already installed through `holoviews`.

## 1.4.0 (2026-11-01)

### Removed

rhkpy no longer imports or installs spym, which removes features that came with it:

- The `.spym` xarray accessor (align, plane, fixzero, destripe, the gauss, median, mean and sharpen filters, and plot).
- `rhkpy.load` for Omicron Scala `.par` and NeXus `.nx`/`.nxs` files. It now accepts only `.sm4` files.
- `rhkpy.rhksm4.to_nexus`.

### Migrating from the `.spym` accessor

The replacements take a NumPy array and return new data, rather than changing the DataArray in place:

- `.spym.align()`: `rhkpy.align`, which returns the aligned image and the background
- `.spym.plane()`: `rhkpy.plane`, which returns the flattened image and the background
- `.spym.fixzero()`: `rhkpy.fixzero`, which returns the shifted data
- `.spym.destripe()`: `rhkpy.destripe`, which returns the destriped image and the stripe mask

There is no rhkpy replacement for the accessor's filters or its plot. `scipy.ndimage` provides the filters, and `.plot()` from xarray or `qplot()` cover plotting.

### Added

- Files with one spectrum per tip position now load without arguments, instead of failing with a `ZeroDivisionError`. The scan direction dimension (`biasscandir` or `zscandir`) has one entry, labelled like the first sweep of an alternating measurement.
- `alternate=False` now works on files with several spectra per position, instead of failing with a `ValueError`. Every sweep counts as a repetition, with a one-entry scan direction. If the file does alternate, forward and backward sweeps end up mixed in `repetitions`, and a warning says so whenever the number of spectra per tip position is even.
- `rhkpy.fixzero` and `rhkpy.destripe`.

### Changed

- rhkpy's warnings now go to stderr through the `rhkpy` logger, instead of being printed to stdout.
- Invalid `alternate` or `repetitions` values raise a `ValueError` naming the argument, instead of a warning followed by an obscure crash.
- Files with an unsupported spectroscopy line type load without `spectra`, with a warning.
- `rhkpy.navigation()` prints a message and returns `None` when there is nothing to plot, instead of crashing.
- Older RHK Rev files (`RHK_MinorVer` < 6) whose line type contradicts the sweep axis units are classified by the units, with a warning.
- Internal refactor into the `rhkpy.core`, `rhkpy.io`, `rhkpy.builders`, `rhkpy.analysis` and `rhkpy.plotting` packages. `rhkpy.rhkpy_loader` and `rhkpy.rhkpy_process` remain as re-exports.
