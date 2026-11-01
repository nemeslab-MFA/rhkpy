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
