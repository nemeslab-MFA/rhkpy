"""Construction of the `spectra` xarray Dataset for each (datatype, spectype).

One parametrized builder per measurement geometry (map / line / single spec),
driven by the per-spectype configuration in ``_SPECTYPE_CONFIG``. The
``_xr_*`` wrappers keep the historical function names.

To support a new spectroscopy type, add an entry to ``_SPECTYPE_CONFIG`` and
register it in ``rhkpy.builders._BUILDER_REGISTRY``.

.. note::
	The builders reproduce the historical output of rhkpy <= 1.3 bit-for-bit
	(verified by the golden-master characterization tests), including a few
	quirks that are called out in comments below.
"""

import numpy as np
import xarray as xr

from .detect import _get_filename

# attribute blocks reused across builders
_PA_ATTRS = {'units': 'pA', 'long units': 'picoampere'}
_NM_ATTRS = {'units': 'nm', 'long units': 'nanometer'}
_BIAS_ATTRS = {'units': 'V', 'long units': 'Volt'}

#: Per-spectype configuration used by the geometry builders.
#: channels: (data_var name, spym page name) - the FIRST channel is the
#: "primary" page, whose attributes provide the tip position coordinates
#: and whose array determines the map/line size.
_SPECTYPE_CONFIG = {
	'iv': dict(
		channels = [('lia', 'LIA_Current'), ('current', 'Current')],
		sweep_dim = 'bias',
		sweep_coord = 'LIA_Current_x',
		sweep_scale = 1,             # bias stays in V
		sweep_attrs = _BIAS_ATTRS,
		scandir_dim = 'biasscandir',
		scandir_labels = ['left', 'right'],
		# historical quirk: dI/dV maps use (y, x) ordered position dims
		map_pos_dims = ('specpos_y', 'specpos_x'),
	),
	'iz': dict(
		channels = [('current', 'Current')],
		sweep_dim = 'z',
		sweep_coord = 'Current_x',
		sweep_scale = 10**9,         # z is converted to nm
		sweep_attrs = _NM_ATTRS,
		scandir_dim = 'zscandir',
		scandir_labels = ['up', 'down'],
		# historical quirk: I(z) maps use (x, y) ordered position dims
		map_pos_dims = ('specpos_x', 'specpos_y'),
	),
}


## helpers ------------------------------------------------------------

def _page(stmdata_object, page_name: str) -> xr.DataArray:
	"""The raw DataArray of one page (channel) of the sm4 file."""
	# attribute access (not item access), so that a missing channel raises the
	# same AttributeError as the historical code, e.g.
	# "'Dataset' object has no attribute 'LIA_Current'"
	return getattr(stmdata_object.spymdata, page_name)


def _split_scandir(array: np.ndarray, numberofspectra: int, single_sweep: bool = False) -> list[np.ndarray]:
	"""Collect all spectra measured at the same tip position into the last axis
	and separate the alternating forward/backward sweeps by slicing.

	Returns [forward, backward], or just [forward] if `single_sweep` is set, each
	of shape (npoints, npositions, nrepetitions).
	"""
	temp = np.reshape(array, (array.shape[0], -1, numberofspectra), order='C')
	if single_sweep:
		return [temp]
	return [temp[:, :, 0::2], temp[:, :, 1::2]]


def _scandir_labels(cfg, single_sweep: bool) -> np.ndarray:
	"""Values of the scan direction coordinate. With a single scan direction, the
	label is that of the first sweep of an alternating measurement."""
	labels = cfg['scandir_labels'][:1] if single_sweep else cfg['scandir_labels']
	return np.array(labels, dtype = 'U')


def _spec_positions(stmdata_object, page_name: str) -> tuple[np.ndarray, np.ndarray]:
	"""Tip positions of the spectra, in the order the spectra were measured."""
	attrs = _page(stmdata_object, page_name).attrs
	xcoo = np.array(attrs['RHK_SpecDrift_Xcoord'])
	ycoo = np.array(attrs['RHK_SpecDrift_Ycoord'])
	return xcoo, ycoo


def _sweep_coord_values(stmdata_object, cfg):
	"""Values of the sweep coordinate (bias in V, or z converted to nm)."""
	return stmdata_object.spymdata.coords[cfg['sweep_coord']].data * cfg['sweep_scale']


def _apply_channel_attrs(xrspec, cfg):
	"""Set the units attributes on the channels, positions and sweep coordinate."""
	for var_name, _ in cfg['channels']:
		xrspec[var_name].attrs.update(_PA_ATTRS)
	xrspec['x'].attrs.update(_NM_ATTRS)
	xrspec['y'].attrs.update(_NM_ATTRS)
	xrspec.coords[cfg['sweep_dim']].attrs.update(cfg['sweep_attrs'])


## geometry builders --------------------------------------------------

def _build_map(stmdata_object, cfg):
	"""Spectroscopy map: spectra on a mapsize x mapsize grid of tip positions."""
	primary = cfg['channels'][0][1]
	single_sweep = not stmdata_object.alternate

	# total number of spectra in one position of the tip
	numberofspectra = (stmdata_object.alternate + 1)*stmdata_object.repetitions
	# size of the map in mapsize x mapsize
	mapsize = int(np.sqrt(_page(stmdata_object, primary).data.shape[1] / numberofspectra))

	# reshape each channel: separate forward/backward sweeps, arrange into the
	# mapsize x mapsize grid, then flip the position axes so that the spectra
	# line up with the topography image (first topo pixel = first spec pixel)
	data_vars = {}
	for var_name, page_name in cfg['channels']:
		sweeps = _split_scandir(_page(stmdata_object, page_name).data, numberofspectra, single_sweep)
		grids = [np.flip(np.reshape(s, (s.shape[0], mapsize, mapsize, s.shape[2]), order='C'), axis=(1, 2)) for s in sweeps]
		dims = [cfg['sweep_dim'], *cfg['map_pos_dims'], 'repetitions', cfg['scandir_dim']]
		# stack the forward and backward sweeps along the scandir dim; convert to pA
		data_vars[var_name] = (dims, np.stack(grids, axis=-1)*10**12)

	# tip positions of the spectra, arranged on the same grid (in nm)
	xcoo, ycoo = _spec_positions(stmdata_object, primary)
	meshx = np.reshape(xcoo, (mapsize, mapsize, numberofspectra), order='C')[:, :, 0]
	meshy = np.reshape(ycoo, (mapsize, mapsize, numberofspectra), order='C')[:, :, 0]
	data_vars['x'] = (list(cfg['map_pos_dims']), meshx*10**9)
	data_vars['y'] = (list(cfg['map_pos_dims']), meshy*10**9)

	# grid coordinates for the spectra positions: pixel centers, shifted by the
	# image offset
	pixelsizex = stmdata_object.image.attrs['size_x'] / mapsize
	pixelsizey = stmdata_object.image.attrs['size_y'] / mapsize
	tempx = np.linspace(pixelsizex/2, stmdata_object.image.attrs['size_x'] - pixelsizex/2, num=mapsize) + stmdata_object.image.attrs['xoffset']
	tempy = np.linspace(pixelsizey/2, stmdata_object.image.attrs['size_y'] - pixelsizey/2, num=mapsize) + stmdata_object.image.attrs['yoffset']

	xrspec = xr.Dataset(
		data_vars = data_vars,
		coords = {
			cfg['sweep_dim']: _sweep_coord_values(stmdata_object, cfg),
			'specpos_x': tempx,
			'specpos_y': tempy,
			'repetitions': np.array(range(stmdata_object.repetitions)),
			cfg['scandir_dim']: _scandir_labels(cfg, single_sweep),
			},
		attrs = dict(filename = _get_filename(stmdata_object.filename))
	)

	_apply_channel_attrs(xrspec, cfg)
	xrspec.coords['specpos_x'].attrs.update(_NM_ATTRS)
	xrspec.coords['specpos_y'].attrs.update(_NM_ATTRS)

	stmdata_object.spectra = xrspec
	return stmdata_object


def _build_line(stmdata_object, cfg):
	"""Line spectroscopy: spectra along a line of tip positions."""
	primary = cfg['channels'][0][1]
	single_sweep = not stmdata_object.alternate

	# total number of spectra in one position of the tip
	numberofspectra = int((stmdata_object.alternate + 1)*stmdata_object.repetitions)

	# separate the forward/backward sweeps of each channel; convert to pA
	data_vars = {}
	for var_name, page_name in cfg['channels']:
		sweeps = _split_scandir(_page(stmdata_object, page_name).data, numberofspectra, single_sweep)
		dims = [cfg['sweep_dim'], 'dist', 'repetitions', cfg['scandir_dim']]
		data_vars[var_name] = (dims, np.stack(sweeps, axis=-1)*10**12)

	# tip positions: need only every nth coordinate, where n is the number of
	# spectra in a tip position
	xcoo, ycoo = _spec_positions(stmdata_object, primary)
	tempx = xcoo[0::numberofspectra]
	tempy = ycoo[0::numberofspectra]
	linelength = np.sqrt((tempx[-1] - tempx[0])**2 + (tempy[-1] - tempy[0])**2)
	# distance coordinates along the line in [nm]
	linecoord = np.linspace(0, linelength, num=tempx.shape[0])*10**9
	data_vars['x'] = (['dist'], tempx*10**9)
	data_vars['y'] = (['dist'], tempy*10**9)

	xrspec = xr.Dataset(
		data_vars = data_vars,
		coords = {
			cfg['sweep_dim']: _sweep_coord_values(stmdata_object, cfg),
			'dist': linecoord,
			'repetitions': np.array(range(stmdata_object.repetitions)),
			cfg['scandir_dim']: _scandir_labels(cfg, single_sweep),
			},
		attrs = dict(filename = _get_filename(stmdata_object.filename))
	)

	_apply_channel_attrs(xrspec, cfg)
	xrspec.coords['dist'].attrs.update(_NM_ATTRS)

	stmdata_object.spectra = xrspec
	return stmdata_object


def _build_spec(stmdata_object, cfg):
	"""Single-point spectroscopy: repeated spectra at one tip position."""
	primary = cfg['channels'][0][1]
	single_sweep = not stmdata_object.alternate

	# separate the alternating forward/backward sweeps; convert to pA
	data_vars = {}
	for var_name, page_name in cfg['channels']:
		arr = _page(stmdata_object, page_name).data
		sweeps = [arr] if single_sweep else [arr[:, 0::2], arr[:, 1::2]]
		dims = [cfg['sweep_dim'], 'repetitions', cfg['scandir_dim']]
		data_vars[var_name] = (dims, np.stack(sweeps, axis=-1)*10**12)

	# tip position: only the first x and y components are needed
	xcoo, ycoo = _spec_positions(stmdata_object, primary)
	tempx = xcoo[0]
	tempy = ycoo[0]
	data_vars['x'] = tempx*10**9
	data_vars['y'] = tempy*10**9

	xrspec = xr.Dataset(
		data_vars = data_vars,
		coords = {
			cfg['sweep_dim']: _sweep_coord_values(stmdata_object, cfg),
			'repetitions': np.array(range(stmdata_object.repetitions)),
			cfg['scandir_dim']: _scandir_labels(cfg, single_sweep),
			},
		attrs = dict(filename = _get_filename(stmdata_object.filename))
	)

	_apply_channel_attrs(xrspec, cfg)
	# the tip position is also stored in the Dataset attributes
	xrspec.attrs['speccoord_x'] = tempx*10**9
	xrspec.attrs['speccoord_y'] = tempy*10**9
	xrspec.attrs['speccoord_x units'] = 'nm'
	xrspec.attrs['speccoord_y units'] = 'nm'

	stmdata_object.spectra = xrspec
	return stmdata_object


## historical entry points --------------------------------------------

def _xr_map_iv(stmdata_object):
	"""Create the `spectra` Dataset of a dI/dV map (LIA + Current channels)."""
	return _build_map(stmdata_object, _SPECTYPE_CONFIG['iv'])


def _xr_map_iz(stmdata_object):
	"""Create the `spectra` Dataset of an I(z) map (Current channel)."""
	return _build_map(stmdata_object, _SPECTYPE_CONFIG['iz'])


def _xr_line_iv(stmdata_object):
	"""Create the `spectra` Dataset of a dI/dV line spectroscopy."""
	return _build_line(stmdata_object, _SPECTYPE_CONFIG['iv'])


def _xr_line_iz(stmdata_object):
	"""Create the `spectra` Dataset of an I(z) line spectroscopy."""
	return _build_line(stmdata_object, _SPECTYPE_CONFIG['iz'])


def _xr_spec_iv(stmdata_object):
	"""Create the `spectra` Dataset of a single-point dI/dV spectrum."""
	return _build_spec(stmdata_object, _SPECTYPE_CONFIG['iv'])


def _xr_spec_iz(stmdata_object):
	"""Create the `spectra` Dataset of a single-point I(z) spectrum."""
	return _build_spec(stmdata_object, _SPECTYPE_CONFIG['iz'])
