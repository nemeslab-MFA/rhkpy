"""Backward-compatibility shim (refactor phase 2).

The implementation now lives in:

- :mod:`rhkpy.core` - the rhkdata class
- :mod:`rhkpy.io` - sm4 file loading
- :mod:`rhkpy.builders` - construction of the image/spectra Datasets
- :mod:`rhkpy.plotting` - quick plots

This module re-exports the public (and historical) names so that existing
imports like ``from rhkpy.rhkpy_loader import rhkdata`` keep working
unchanged. Some spym features are gone since version 1.4.0: see CHANGELOG.md.
"""

# historical module-level imports, kept because they are part of the public
# namespace of this module (and of rhkpy itself, via the star import)
import matplotlib.pyplot as pl
import numpy as np
import xarray as xr
import re, copy
# the sm4 loader (ported from spym, which used to provide these names)
from .io.sm4 import load_dataset as load
from .io import sm4 as rhksm4
## flatten and plane fitting
from .analysis.level import align
from .analysis.level import plane
from .analysis.level import fixzero
from .analysis.level import destripe

# for fancy plotting
import hvplot.xarray
import holoviews as hv
import panel as pn

from .rhkpy_process import *

from .core import rhkdata
from .summary import scan
from .io import load_rhksm4, load_spym

# internal helpers, re-exported for backward compatibility of private imports
from .builders import _load_specmap, _load_line, _load_spec, _load_image
from .builders.detect import _checkrepetitions, _checkdatatype, _aspect_ratio, _get_filename
from .builders.spectra import _xr_map_iv, _xr_line_iv, _xr_spec_iv, _xr_map_iz, _xr_line_iz, _xr_spec_iz
from .builders.image import _xr_image, _xr_image_line
from .builders.metadata import _add_map_metadata, _add_line_metadata, _add_spec_metadata, _add_image_metadata
