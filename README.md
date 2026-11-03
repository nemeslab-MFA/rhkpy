# RHK STM data analysis tool

The sm4 reader is ported from the [spym project](https://github.com/rescipy-project/spym) (version 0.9.1).

Documentation can be found here: https://nemeslab-mfa.github.io/rhkpy/

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/nemeslab-MFA/rhkpy/HEAD)

If you use this package in your publication, consider citing it:
Peter Nemes-I., & Mirco Panighel. (2023). zrbyte/rhkpy: v1.3.3 (v1.3.3). Zenodo. https://zenodo.org/doi/10.5281/zenodo.10143224
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10143224.svg)](https://doi.org/10.5281/zenodo.10143224)

## Main features
- Able to handle spectroscopy measurements (both dI/dV and I(z)):
  - dI/dV maps
  - spectra along a line
  - individual spectra
- Resample dI/dV maps along a line (see [`mapsection`](https://nemeslab-mfa.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.mapsection))
- Quick, interactive visualization of spectroscopy data (see [`qplot`](https://nemeslab-mfa.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_loader.rhkdata.qplot))
- Recreating the "navigation" window in Rev9, by plotting the relative positions of measurements (see the [`navigation`](https://nemeslab-mfa.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.navigation) function).
- Generating thumbnails of your measurements (see [`genthumbs`](https://nemeslab-mfa.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.genthumbs))
- Peak fitting (see [`peakfit`](https://nemeslab-mfa.github.io/rhkpy/rhkpy.html#rhkpy.rhkpy_process.peakfit))

- Inspecting and picturing measurements without a notebook or browser (see [Scripts and AI agents](#scripts-and-ai-agents))

## Installation
`pip install rhkpy`

## Simple example
```python
import rhkpy

# Load an sm4 file
data = rhkpy.rhkdata('filename.sm4')

# "quick plot" of the data
data.qplot()

# make thumbnails of the sm4 files in the current working directory
rhkpy.genthumbs()
```

Also take a look at the `demo.ipynb` and `tutorial.ipynb` Jupyter notebooks in this repository.

## Scripts and AI agents
`qplot` is interactive, so it needs a notebook. For scripts, servers and AI agents, rhkpy also has plain-data and static-picture equivalents:

```python
import rhkpy

data = rhkpy.rhkdata('filename.sm4')
data.summary()             # a JSON-ready dict: type, date, bias, setpoint, shapes, ranges, units
data.preview('out.png')    # a picture, with no browser or display needed
rhkpy.scan('folder/')      # summaries of every file in a folder
```

The same from a shell:

```bash
rhkpy info filename.sm4 --json
rhkpy preview filename.sm4 -o out.png
rhkpy scan folder/ --json
```

AI agents should start with `rhkpy guide` (or `rhkpy.agent_guide()` in Python), which covers the data model, errors and pitfalls. Agents changing rhkpy itself should read [AGENTS.md](AGENTS.md).

To make the most of rhkpy, also consult the xarray documentation and check out plotting examples, with HoloViews. The HoloViews website has examples on how to customize plots, as well as tutorial notebooks.
