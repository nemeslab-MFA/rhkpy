# Using rhkpy from scripts and AI agents

rhkpy loads RHK `.sm4` scanning tunneling microscopy (STM) files into xarray Datasets. This guide covers working without a notebook, where nobody can look at an interactive plot.

## Start here

From a shell:

```bash
rhkpy info measurement.sm4 --json        # what is in this file
rhkpy scan data/ --json                  # what is in this folder; add --recursive for subfolders
rhkpy preview measurement.sm4 -o out.png # save a picture, then open out.png to look at it
```

From Python:

```python
import rhkpy

data = rhkpy.rhkdata('map.sm4')
info = data.summary()                     # plain dict: type, date, bias, setpoint, shapes, ranges, units
print(info['datatype'], info['spectype'], info['notes'])
data.preview('out.png')                   # static picture, no browser or display needed
print(data.spectra)                       # the xarray Dataset itself
```

Read `notes` in the summary. It lists anything that changes how the data should be read.

Don't use `qplot()` here: it returns an interactive widget that is only useful in a notebook. `genthumbs()` needs a real browser; use `preview()` instead.

## Data model

`rhkdata.datatype` is `image`, `map`, `line` or `spec`. `rhkdata.spectype` is `iv` (dI/dV, bias sweep), `iz` (current against tip height) or `None`. Every file has only some of these Datasets:

- `image`: present for `image`, `map` and `line`.
- `spectra`: present for `map`, `line` and `spec`.
- `spymdata`: every page of the file, in raw form, with all the instrument metadata in its attributes (`RHK_...`).

`image` has dimensions `y`, `x`, `scandir` (`forward`, `backward`) and data variables `topography` (nm), `current` (pA) and `lia` (pA).

`spectra` depends on the type. The sweep is `bias` (V) for `iv` and `z` (nm) for `iz`, with the scan direction in `biasscandir` (`left`, `right`) or `zscandir` (`up`, `down`):

- `map`, `iv`: `bias`, `specpos_y`, `specpos_x`, `repetitions`, `biasscandir`
- `map`, `iz`: `z`, `specpos_x`, `specpos_y`, `repetitions`, `zscandir`
- `line`: the sweep, `dist` (nm along the line), `repetitions`, the scan direction
- `spec`: the sweep, `repetitions`, the scan direction

`iv` spectra have data variables `lia` and `current`; `iz` spectra have only `current`, in pA. `x` and `y` hold the tip positions in nm. `lia` is the lock-in signal, which is proportional to dI/dV; its `pA` label is not a calibrated conductance.

Measurement settings are in the `attrs` of each Dataset, for example `data.spectra.attrs['setpoint']`.

## Working with the data

Always select dimensions by name, because their order differs between types (see the two `map` entries above).

```python
import rhkpy

specmap = rhkpy.rhkdata('map.sm4')

# average over repetitions and scan direction, then take one spectrum and one map
mean = specmap.mrep().msw().spectra.lia
spectrum = mean.sel(specpos_x = mean.specpos_x[0], specpos_y = mean.specpos_y[0])
slice_at_bias = mean.sel(bias = 0.1, method = 'nearest')

# the same averages without the shorthand
same_mean = specmap.spectra.lia.mean(dim = ['repetitions', 'biasscandir'])

# the average spectrum of the whole map
average = mean.mean(dim = ['specpos_x', 'specpos_y'])

# a picture of the map at a chosen bias
specmap.preview('map_at_bias.png', at = 0.1)

# a section between two points, in the specpos_x and specpos_y coordinates
x = specmap.spectra.specpos_x.values
y = specmap.spectra.specpos_y.values
section = rhkpy.mapsection(specmap.spectra, (x[0], y[0]), (x[-1], y[-1]))
```

Bias sweeps are often stored from high to low, so sort before slicing a range:

```python
import rhkpy

spectrum = rhkpy.rhkdata('spec.sm4').mrep().msw().spectra.lia
near_zero = spectrum.sortby('bias').sel(bias = slice(-0.2, 0.2))
fit = rhkpy.peakfit(near_zero, stval = {'x0': 0.0, 'ampl': 5.0, 'width': 0.1})
print(fit.curvefit_coefficients)
```

Images are flattened on loading; pass `loadraw = True` to `rhkdata` for the raw topography. Image coordinates start at 0, while `specpos_x` and `specpos_y` are absolute tip positions, so use `coord_to_absolute()` to compare them. It takes scan rotation into account:

```python
import rhkpy

raw = rhkpy.rhkdata('image.sm4', loadraw = True)
flat, background = rhkpy.plane(raw.image.topography.sel(scandir = 'forward').values)
absolute = rhkpy.rhkdata('map.sm4').coord_to_absolute()
print(absolute.image.x.min().item(), absolute.image.x.max().item())
```

Other functions: `rhkpy.align`, `rhkpy.fixzero` and `rhkpy.destripe` level images, `rhkpy.polyflatten` flattens image Datasets, `rhkpy.bgsubtract` removes spectral backgrounds, and `rhkpy.navigation` plots where measurements were taken. Check `help(rhkpy.<name>)` for each.

## Errors and warnings

Failures raise exceptions:

- `FileNotFoundError`: the file or folder doesn't exist.
- `ValueError`: the file isn't a valid `.sm4` file, or an argument of `rhkdata` is invalid. `qplot()` and `navigation()` also raise it when they have nothing to plot.
- `TypeError`: the method doesn't apply to this data type, for example `mrep()` on an image.
- `NotImplementedError`: `coord_to_absolute()` on a line spectrum.

Warnings go to stderr through the `rhkpy` logger, so stdout stays clean. `rhkpy.scan` records a file's error in its entry and continues, so check for the `error` key.

## Pitfalls

- **Scan direction labels can be assumptions.** A file with one spectrum per tip position loads with a single scan direction, labelled like the first sweep of an alternating measurement. That label isn't a measured direction.
- **`alternate = False` mixes sweeps if the file alternates.** Every sweep then counts as a repetition. Leave it at its default unless you know the measurement used one direction.
- **Older files.** Files written by RHK Rev versions before 6 give a warning and are less tested. Their spectrum type is taken from the sweep axis units if the declared line type disagrees.
- **Unsupported spectroscopy.** Other line types, such as time spectroscopy, load without `spectra`, with a warning and a note in the summary.
- **`load_spym` and `load_dataset` return `None` for an invalid file**, instead of raising. Prefer `rhkdata`.
- **Measurement data may be confidential.** Don't publish `.sm4` files or data from them without permission.
