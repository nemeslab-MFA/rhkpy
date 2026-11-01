"""rhkpy: processing of Scanning Tunneling Microscopy (STM) data from RHK
Technology .sm4 files, built on :py:mod:`xarray`.

Load a measurement with :class:`~rhkpy.rhkpy_loader.rhkdata`, take a quick
look with its ``qplot()`` method, and use the analysis functions (
:func:`~rhkpy.rhkpy_process.peakfit`, :func:`~rhkpy.rhkpy_process.bgsubtract`,
:func:`~rhkpy.rhkpy_process.polyflatten`, ...) on the underlying Datasets.
See the tutorial notebook and https://zrbyte.github.io/rhkpy/ for examples.

For use from scripts and AI agents, without a notebook, read the guide:
``print(rhkpy.agent_guide())``, or run ``rhkpy guide`` in a shell.
"""

from .version import __version__
from .rhkpy_loader import *
from .rhkpy_process import *

import hvplot.xarray
import holoviews as hv
from holoviews import dim, opts

import logging
from bokeh.util import logconfig
# Suppress Bokeh's warnings
logconfig.basicConfig(level=logging.ERROR)
# this also sets the level of the root logger, so rhkpy's own warnings need their own level
logging.getLogger('rhkpy').setLevel(logging.WARNING)

import warnings
# suppress holoviews warnings
warnings.filterwarnings('ignore', category = UserWarning, module = 'holoviews.plotting.bokeh.plot')

# select bokeh
hvplot.extension('bokeh')

# global plotting options
from holoviews import opts
opts.defaults(
    opts.Image(
        aspect = 'equal'
        )
    ) # can't set default colormap with this