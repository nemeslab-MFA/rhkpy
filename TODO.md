# TODO

## Check `spectra.x` and `spectra.y` on maps

**Status:** left as is for now. It needs testing by the maintainer against the microscope software before anything changes.

### The issue

The map builders flip the spectra along both position axes (`np.flip(..., axis=(1, 2))` in `_build_map`, `rhkpy/builders/spectra.py`). The purpose, as remembered and as the code comment says, is to show the data in the measured orientation, with the first topography pixel also being the first spectroscopy pixel. This flip stays.

The `x` and `y` data variables of `spectra` don't get that flip. They stay in measurement order, so on maps the spectrum at `[i, j]` was measured at `x[-1 - i, -1 - j]`, `y[-1 - i, -1 - j]`, not at `x[i, j]`, `y[i, j]`.

Single spectra and line spectra aren't affected, because their data isn't flipped.

### What's known

- Checked against the raw columns and `RHK_SpecDrift_Xcoord`/`RHK_SpecDrift_Ycoord` on four maps, including rotated scans and both dI/dV and I(z). `tests/test_agent_guide.py::test_map_tip_position_flip` pins it on two of them.
- The v1.3.10 code does the same, so this isn't a regression from the refactor.
- `qplot` and `preview` place spectra with `specpos_x` and `specpos_y`, so displayed maps don't depend on `x` and `y`. `navigation` draws all the positions as a scatter, so their order doesn't matter there. `mapsection` interpolates `x` and `y` along with the data, so its `x` and `y` carry the mismatch.
- `specpos_x` and `specpos_y` have no scan rotation applied, so on rotated scans they differ from the measured tip positions.
- Not checked: agreement with the microscope software. That is what this item needs.

### To test

Run this from the repo root with a map whose `specpos` coordinates and positions you can look up in the microscope software. It finds which measured spectrum sits at a loaded index:

```python
import numpy as np
import rhkpy

data = rhkpy.rhkdata('map.sm4')
spectra = data.spectra
current = spectra.current.isel(repetitions = 0, biasscandir = 0).transpose('bias', 'specpos_y', 'specpos_x').values
x = spectra.x.transpose('specpos_y', 'specpos_x').values
y = spectra.y.transpose('specpos_y', 'specpos_x').values
raw = data.spymdata.Current

i, j = 3, 5
k = [k for k in range(raw.data.shape[1]) if np.allclose(raw.data[:, k] * 1e12, current[:, i, j])][0]
print('raw column of this spectrum:', k)
print('measured tip position:', raw.attrs['RHK_SpecDrift_Xcoord'][k] * 1e9, raw.attrs['RHK_SpecDrift_Ycoord'][k] * 1e9)
print('x, y at [i, j]:', x[i, j], y[i, j])
print('x, y at [-1 - i, -1 - j]:', x[-1 - i, -1 - j], y[-1 - i, -1 - j])
print('specpos at [i, j]:', spectra.specpos_x.values[j], spectra.specpos_y.values[i])
```

For `dI-dV_ABC_Graphite-Sample5_9K_2021_08_24_11_54_33_632.sm4` it prints:

```
raw column of this spectrum: 1844
measured tip position: -546.58014 -818.16016
x, y at [i, j]: -480.9551 -740.03516
x, y at [-1 - i, -1 - j]: -546.58014 -818.16016
specpos at [i, j]: -546.3848326555265 -817.9648483917802
```

Check that:

1. A distinctive spectrum, at the same place in the microscope software, matches the spectrum at this `[i, j]` in rhkpy.
2. The microscope software's position for that spectrum matches the measured tip position printed above.
3. For a rotated scan, the same holds, and note how far `specpos` is from it.

### If `x` and `y` should change

Flip `meshx` and `meshy` in `_build_map` to match the data, and leave the data flip alone. Then:

- Regenerate the goldens with `python tests/make_golden.py` and check that only the `x` and `y` of map files changed.
- Update `test_map_tip_position_flip`, and the "Tip positions on maps" section in `rhkpy/AGENT_GUIDE.md`.
- Add a changelog entry, since this would differ from earlier versions and any script compensating for the offset would break.

## Check other output against the microscope software

Also needs testing by the maintainer:

- **Single-sweep files.** `dI-dV_9K_ABC6_2020_07_02_08_50_47_967.sm4` and `line_hopg_300k_2020_08_11_16_20_04_378.sm4` load since 1.4.0, but nobody has compared them with the instrument software.
- **Their sweep label.** Those two files are labelled `left`, from the order of their bias axis, although their pages are tagged `RHK_SCAN_RIGHT`. The goldens record `left`.
- **The four `RHK_MinorVer` 5 files added in 1.4.0.** Their goldens only record current output.

## Test data gaps

`test/` has no older (`RHK_MinorVer` 5) line spectrum and no older map with several spectra per position. In `test/`, files up to 2 Jul 2020 are version 5 and files from 11 Aug 2020 on are version 6, so look for measurements from before August 2020.

## Known reader bugs

These are in `rhkpy/io/sm4.py`, and are deliberately not fixed: the reader must match what the instrument and other software show, so it changes only on the maintainer's explicit direction. They are recorded here to explain a failure if a file ever hits one.

- **Non-square images load wrongly.** In `_reshape_data`, image pages are reshaped as `(xsize, ysize)` rather than `(ysize, xsize)`, so a rectangular scan gets its axes mislabelled. The image and map files in `test/` are all square; only the line files have rectangular images, and those go through `_xr_image_line`.
- **ScanType 2 or 3 image pages crash.** In `RHKPage._read`, `scan_direction` is only set for `RHK_ScanType` 0 and 1, so `RHK_SCAN_UP` or `RHK_SCAN_DOWN` pages with a label raise `UnboundLocalError`. Through `rhkdata()`, this surfaces as an invalid file error.
- **Uncompressed PRM data crashes.** `_read_PRMdata` calls `.decode('CP437')` on a NumPy array when `_PRM_CompressionFlag` is 0, and leaves `PRMdata` unset for any flag other than 0 or 1.

## Code cleanups

From the July 2026 pre-merge review; all still present as of 1.5.0. None change behaviour, and the goldens should stay identical. The ones in `builders` and `sm4.py` need extra care because of the loader rule in `AGENTS.md`.

- `_xr_image_line` in `rhkpy/builders/image.py` is a copy of `_xr_image`, differing in the flipud calls, swapped coordinates and y attributes. The copies have already drifted, for example `size_x` and `size_y` exist only in `_xr_image`.
- `_load_line` and `_load_specmap` in `rhkpy/builders/__init__.py` are identical, and `core.py` dispatches on datatype as well as the registry.
- `coord_to_absolute` in `rhkpy/analysis/ops.py` has six copy-pasted `ndimage.rotate` blocks that a loop could replace.
- `mrep()` and `msw()` in `rhkpy/core.py` use `copy.deepcopy(self)`, duplicating the raw data and images just to replace `spectra`, so chaining them multiplies memory use.
- `_aspect_ratio` in `rhkpy/builders/detect.py` has a loop with no effect on its result.
- `numberofspectra` is set in all three `_load_*` wrappers in `rhkpy/builders/__init__.py`, but nothing in `rhkpy` reads it. It is part of the public object, so removing it changes the goldens.
- The `RHK_LineType` to spectype mapping is repeated in both branches of `_checkdatatype` in `rhkpy/builders/detect.py`.
- `rhkpy/builders/image.py` has blocks of commented-out code: the flipud calls in `_xr_image_line` and the align and plane calls in `_xr_image`.
- The interpreter lookup is duplicated between `.githooks/pre-commit` and `.githooks/pre-push`.
- The docs job in `.github/workflows/tests.yml` repeats the build in `publish docs workflow.yml` with different install steps, so one can pass while the other fails.
- `_read_ColorInfo` in `rhkpy/io/sm4.py` is never called.
- `rhkpy/rhkpy_loader.py` re-exports underscore-private helpers, freezing those names in a second place. Removing them is a candidate for 2.0.

## Smaller usability gaps

From a usability test by a fresh AI agent:

- `print_info()` lists only variable names; `summary()` is more useful.
- `summary()`'s `notes` doesn't flag lock-in modulation that is large compared with the sweep step. The guide mentions it instead.
- `preview()` defaults to the middle of the sweep for maps, which is an arbitrary choice.
