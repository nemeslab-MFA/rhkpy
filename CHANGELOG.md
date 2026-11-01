# Changelog

## 1.4.0 (unreleased)

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
- Older RHK Rev files (`RHK_MinorVer` < 6) whose line type contradicts the sweep axis units are classified by the units, with a warning.
- Internal refactor into the `rhkpy.core`, `rhkpy.io`, `rhkpy.builders`, `rhkpy.analysis` and `rhkpy.plotting` packages. `rhkpy.rhkpy_loader` and `rhkpy.rhkpy_process` remain as re-exports.
