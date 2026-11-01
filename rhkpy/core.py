"""The rhkdata class: an xarray-based container for RHK .sm4 measurement data.

The heavy lifting is delegated to the submodules:

- :mod:`rhkpy.io` - reading the .sm4 file
- :mod:`rhkpy.builders` - constructing the `image` and `spectra` Datasets
- :mod:`rhkpy.analysis` - coordinate transforms, flattening, fitting
- :mod:`rhkpy.plotting` - quick plots
"""

import copy
import logging as _logging
import numbers as _numbers

import numpy as _np

from .io import load_spym
from .builders import _load_specmap, _load_line, _load_spec, _load_image
from .builders.detect import _checkdatatype, _checkrepetitions, _is_single_sweep, _get_filename
from .analysis import ops as _ops
from .plotting import quickplot as _quickplot

_logger = _logging.getLogger('rhkpy')


class rhkdata:
	"""
	A container for the xarray based structure of the RHK data. Loads the RHK "sm4" file from the path at: ``filename``.

	:param filename: path and filename of the "sm4" file to be loaded
	:type filename: str
	:param repetitions: The number of repeated aquisitions of spectra in tip position. If 0, it is inferred from the file, defaults to 0
	:type repetitions: int, optional
	:param alternate: `True` if the bias is swept forward and backward, `False` if not, defaults to True. With `False`, every sweep counts as a repetition and the scan direction dimension has a single entry, labelled like the first sweep of an alternating measurement. If the file does alternate, forward and backward sweeps end up mixed in the repetitions and the label doesn't describe them. Files with one spectrum per tip position are always loaded with `False`.
	:type alternate: bool, optional
	:param loadraw: Set to `True` if you want the raw topography data, defaults to False
	:type loadraw: bool, optional

	Some variables of the :class:`rhkdata` class:

	:var filename: (type str) filename of the "sm4" file
	:var image: (type :py:mod:`xarray` Dataset) Dataset containing the image data
	:var spectra: (type :py:mod:`xarray` Dataset) Dataset containing the spectroscopy data
	:var spymdata: (type :py:mod:`spym` instance) Dataset, as loaded by the :py:mod:`spym` module

	All the variables can be listed by calling: :class:`rhkdata.print_info`.

	.. note::
		If you want to skip the "flatten" filter of the topography images, use: `loadraw = True`.

	:Example:

		.. code-block:: python

			import rhkpy

			# Load dI/dV spectra, measured along a line
			filename = 'linespectra.sm4'
			linespec = rhkpy.rhkdata(filename)

			# display the contents of the spectroscopy `xarray` instance
			linespec.spectra
			<xarray.Dataset>
			Dimensions:      (bias: 501, dist: 64, repetitions: 1, biasscandir: 2)
			Coordinates:
			* bias         (bias) float64 0.5 0.498 0.496 0.494 ... -0.496 -0.498 -0.5
			* dist         (dist) float64 0.0 0.5279 1.056 1.584 ... 32.2 32.73 33.26
			* repetitions  (repetitions) int32 0
			* biasscandir  (biasscandir) <U5 'left' 'right'
			Data variables:
				lia          (bias, dist, repetitions, biasscandir) float64 3.585 ... 5.185
				current      (bias, dist, repetitions, biasscandir) float64 99.49 ... -132.7
				x            (dist) float64 -37.48 -36.97 -36.45 ... -5.902 -5.384 -4.866
				y            (dist) float64 -173.5 -173.6 -173.7 ... -179.7 -179.9 -180.0
			Attributes: (12/15)
				filename:           line_9K_ABC6_2020_11_01_12_12_27_213.sm4
				bias:               0.49999988
				bias units:         V
				setpoint:           99.99999439624929
				setpoint units:     pA
				measurement date:   11/01/20
				...                 ...
				LI amplitude unit:  mV
				LI frequency:       1300.0
				LI frequency unit:  Hz
				LI phase:           -102.9999998
				datatype:           line
				spectype:           iv

			# select the dI/dV signal (lia) and average the
			# forward and backward bias sweeps and repetitions
			linespec_avg = linespec.spectra.lia.mean(dim = ['biasscandir', 'repetitions'])

			# plot the dI/dV values along the remaining coordinates: bias, dist
			linespec_avg.plot()

	"""
	def __init__(self, filename, repetitions = 0, alternate = True, loadraw = False, **kwargs):
		"""Initialize the :class:`rhkdata` instance
		"""

		if not isinstance(alternate, (bool, _np.bool_)):
			raise ValueError(f'alternate needs to be True or False, got: {alternate!r}')
		if isinstance(repetitions, bool) or not isinstance(repetitions, _numbers.Integral) or repetitions < 0:
			raise ValueError(f'repetitions needs to be an integer, 1 or above, or 0 to infer it from the file, got: {repetitions!r}')

		self.filename = filename
		self.loadraw = loadraw
		self.datatype = None
		self.spectype = None

		# Boolean value, True if alternate scan directions is turned on
		self.alternate = alternate

		# Load the data using spym
		self.spymdata = load_spym(self.filename)
		if self.spymdata is None:
			return

		# check software version. Not tested for MinorVer < 6
		l = list(self.spymdata.keys())
		if self.spymdata[l[-1]].attrs['RHK_MinorVer'] < 6:
			_logger.warning('stmdatastruct not tested for RHK Rev version < 6. Some things might not work as expected.')

		# check type of data and spectra contained in the file
		self.datatype, self.spectype = _checkdatatype(self)

		# one spectrum per tip position leaves no second sweep to separate
		if self.datatype in ('map', 'line', 'spec') and self.alternate and _is_single_sweep(self):
			_logger.warning('%s has one spectrum per tip position, loading it with alternate = False.', _get_filename(self.filename))
			self.alternate = False

		# number of spectra at a tip position
		# default value is 0, if this is changed, the code will use the given value, othewise it will try to infer the number of repetitions from the number of identical tip positions
		if self.datatype != 'image':
			if repetitions != 0:
				# overwrite the default value and the value inferred from tip coordinates
				self.repetitions = repetitions
			else:
				# determine the number of repetitions from the number of indentical tip coordinates in the beginning of RHK_SpecDrift_Xcoord
				self.repetitions = _checkrepetitions(self)
		else:
			self.repetitions = repetitions

		# load data into xarray, for all data types
		if self.datatype == 'map':
			self = _load_specmap(self)
		elif self.datatype == 'line':
			self = _load_line(self)
		elif self.datatype == 'spec':
			self = _load_spec(self)
		elif self.datatype == 'image':
			self = _load_image(self)

	def mrep(self):
		"""Returns a new instance of :class:`rhkdata`, with the data averaged (using :py:mod:`xarray.Variable.mean`) along the 'repetitions' coordinate.
		Meant to be shorthand for: ``rhkdata_instance.spectra.mean(dim = 'repetitions')``.

		:return: :class:`rhkdata` instance
		:rtype: :class:`rhkdata`
		"""
		# function to take the mean along the repetitions coordinate
		if self.datatype == 'image':
			print('An image instance doesn\'t have repetitions.')
			return
		newdata = copy.deepcopy(self)
		newdata.spectra = newdata.spectra.mean(dim = 'repetitions')
		return newdata

	def msw(self):
		"""Returns a new instance of :class:`rhkdata`, with the data averaged (using :py:mod:`xarray.Variable.mean`) along the 'biasscandir' or 'zscandir' coordinate.
		Meant to be shorthand for: ``rhkdata_instance.spectra.mean(dim = 'biasscandir')``, or ``rhkdata_instance.spectra.mean(dim = 'zscandir')``.

		:return: :class:`rhkdata` instance
		:rtype: :class:`rhkdata`
		"""
		# function to take the mean along the biasscan coordinate
		if self.datatype == 'image':
			print('An image instance doesn\'t have biasscandir or zscandir.')
			return
		newdata = copy.deepcopy(self)
		if self.spectype == 'iv':
			newdata.spectra = newdata.spectra.mean(dim = 'biasscandir')
		elif self.spectype == 'iz':
			newdata.spectra = newdata.spectra.mean(dim = 'zscandir')
		return newdata

	def print_info(self):
		"""List the variables of the :class:`rhkdata` instance.
		"""
		for item in self.__dict__:
			print(item)
		if 'image' in self.__dict__:
			print('\nimage:')
			for item in self.image.data_vars:
				print('\t', item)
		if 'spectra' in self.__dict__:
			print('\nspectra:')
			for item in self.spectra.data_vars:
				print('\t', item)

	def coord_to_absolute(self):
		"""Returns a new :class:`rhkdata` instance, with the coordinates updated to reflect the abolute tip position. This includes X, Y offset and rotation.

		:return: :class:`rhkdata` instance, with the same data and metadata, but the :class:`rhkdata.image`, :py:mod:`xarray` variable coordinates shifted to absolute tip positions.
		:rtype: :class:`rhkdata` instance

		:Example:

		.. code-block:: python

			import rhkpy

			m = rhkpy.rhkdata('didv map.sm4')

			# Take the `rhkdata` instance (image or map): `m`,
			# and convert the image coordinates to absolute values
			m_abs = m.coord_to_absolute()

			# coordinates of the instance `m`
			# We can see it runs from 0 to 100 nm
			print(m.image.x.min().data, m.image.x.max().data)
			0.0 100.0

			# check the same corrdinate for the new `m_abs`
			print(m_abs.image.x.min().data, m_abs.image.x.max().data)
			-877.0008892433623 -741.0633876547834

			# we can see it's now shows the exact tip position
			# the image is also rotated, as the "scan angle" attribute shows
			m_abs.image.attrs['scan angle']
			30.0

			# plot the rotated and offset image
			m_abs.image.topography.sel(scandir = 'forward').plot()

		"""
		# check if 'image' is present
		if 'image' not in self.__dict__:
			print('This `rhkdata` instance does not contain an image')
			return

		# copy the current instance
		rhkdataobj_new = copy.deepcopy(self)

		# update the coordinates
		rhkdataobj_new.image = _ops.coord_to_absolute(self.image)

		return rhkdataobj_new

	def polyflatten(self, **kwargs):
		"""Uses :func:`~rhkpy.rhkpy_process.polyflatten` to flatten the selected datafield in the :class:`rhkdata` instance.
		All keywords accepted by :func:`~rhkpy.rhkpy_process.polyflatten` can be passed.

		:return: :class:`rhdata` instance, with the selected ``field_type`` flattened. Default ``field_type`` = 'topography'.
		:rtype: :class:`rhdata` instance
		"""

		# check if 'image' is present
		if 'image' not in self.__dict__:
			print('This `rhkdata` instance does not contain an image')
			return
		# make a copy of the instance
		flattened_rhkdataobj = copy.deepcopy(self)
		# apply flatten to the copy
		flattened_rhkdataobj.image = _ops.polyflatten(self.image, **kwargs)

		return flattened_rhkdataobj

	def qplot(self, width = None, **kwargs):
		"""Quick plot of the :class:`rhkdata` instance

		:param width: set size of plot, defaults to None
		:type width: float, optional

		The colorscales used for density plots can be specified by the keywords below.
		For possible colorscale options see the `HoloViews colormaps <https://holoviews.org/user_guide/Colormaps.html>`_.

		:param cmap_topo: topography colorscale, defaults to 'fire'
		:type cmap_topo: str, optional
		:param cmap_spec: colorscale for plotting dI/dV data, defaults to 'viridis'
		:type cmap_spec: str, optional

		:return: :py:mod:`panel` plot
		:rtype: :py:mod:`panel`
		"""
		return _quickplot.qplot(self, width = width, **kwargs)

	## internal functions -----------------------------------------------------------------------------------------
	## plotting functions for qplot, delegating to rhkpy.plotting.quickplot

	def _qplot_topo(self, cmap_topo = 'fire', **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_topo`."""
		return _quickplot.plot_topo(self, cmap_topo = cmap_topo, **kwargs)

	def _qplot_lia(self, cmap_spec = 'viridis', **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_lia`."""
		return _quickplot.plot_lia(self, cmap_spec = cmap_spec, **kwargs)

	def _qplot_map_iv(self, cmap_spec = 'viridis', **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_map_iv`."""
		return _quickplot.plot_map_iv(self, cmap_spec = cmap_spec, **kwargs)

	def _qplot_map_iz(self, cmap_spec = 'viridis', **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_map_iz`."""
		return _quickplot.plot_map_iz(self, cmap_spec = cmap_spec, **kwargs)

	def _qplot_line_iv(self, cmap_spec = 'viridis', **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_line_iv`."""
		return _quickplot.plot_line_iv(self, cmap_spec = cmap_spec, **kwargs)

	def _qplot_line_spec_iv(self, **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_line_spec_iv`."""
		return _quickplot.plot_line_spec_iv(self, **kwargs)

	def _qplot_line_iz(self, cmap_spec = 'viridis', **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_line_iz`."""
		return _quickplot.plot_line_iz(self, cmap_spec = cmap_spec, **kwargs)

	def _qplot_line_spec_iz(self, **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_line_spec_iz`."""
		return _quickplot.plot_line_spec_iz(self, **kwargs)

	def _qplot_spec_iv_lia(self, **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_spec_iv_lia`."""
		return _quickplot.plot_spec_iv_lia(self, **kwargs)

	def _qplot_spec_iv_curr(self, **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_spec_iv_curr`."""
		return _quickplot.plot_spec_iv_curr(self, **kwargs)

	def _qplot_spec_iz(self, **kwargs):
		"""See :func:`rhkpy.plotting.quickplot.plot_spec_iz`."""
		return _quickplot.plot_spec_iz(self, **kwargs)
