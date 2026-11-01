"""A static picture of a measurement, for when nobody can look at a widget.

:mod:`~rhkpy.plotting.quickplot` makes interactive plots, and saving those as png
needs a browser. This renders with matplotlib's Agg canvas instead, without pyplot,
so it works with no display and doesn't change any global plotting state.
"""

import colorcet
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# the same colormaps as qplot
_CMAP_TOPO = colorcet.cm['fire']
_CMAP_SPEC = 'viridis'

#: what to plot from the spectra, per spectype
_SWEEPS = {
	'iv': dict(sweep_dim = 'bias', scandir_dim = 'biasscandir', signal = 'lia', name = 'bias', unit = 'V', signal_label = 'dI/dV (pA)'),
	'iz': dict(sweep_dim = 'z', scandir_dim = 'zscandir', signal = 'current', name = 'z', unit = 'nm', signal_label = 'current (pA)'),
}


def _half_step(values):
	"""Half the distance between the coordinates, which are pixel centers."""
	return (values[-1] - values[0]) / (values.size - 1) / 2 if values.size > 1 else 0.5


def _show_image(ax, dataarray, x, y, cmap, label, title):
	"""Density plot of a 2D DataArray, with the dims selected by name and both axes
	ascending. Bias sweeps are often stored high to low."""
	data = dataarray.transpose(y, x).sortby([y, x])
	xvalues = data[x].values
	yvalues = data[y].values
	xstep = _half_step(xvalues)
	ystep = _half_step(yvalues)
	image = ax.imshow(
		data.values, origin = 'lower', cmap = cmap, aspect = 'auto',
		extent = (xvalues[0] - xstep, xvalues[-1] + xstep, yvalues[0] - ystep, yvalues[-1] + ystep),
	)
	ax.set_title(title)
	ax.figure.colorbar(image, ax = ax, label = label)
	return image


def _show_scan(ax, rhkdata_obj, channel, cmap, title):
	"""An image channel in the backward scan direction, as in qplot: the direction
	the tip moves in while the spectra are measured."""
	dataarray = rhkdata_obj.image[channel].sel(scandir = 'backward')
	_show_image(ax, dataarray, 'x', 'y', cmap, f'{channel} ({dataarray.attrs["units"]})', title)
	ax.set_xlabel('x (nm)')
	ax.set_ylabel('y (nm)')
	ax.set_aspect('equal')


def _sweep_lines(ax, dataarray, sweep_dim, scandir_dim, xlabel, ylabel):
	"""Every repetition as a thin line, and each scan direction's average on top."""
	for color, light, scandir in zip(('red', 'blue'), ('LightCoral', 'LightSkyBlue'), dataarray[scandir_dim].values):
		sweeps = dataarray.sel({scandir_dim: scandir})
		if sweeps.sizes['repetitions'] > 1:
			for repetition in sweeps.repetitions.values:
				ax.plot(sweeps[sweep_dim], sweeps.sel(repetitions = repetition), color = light, linewidth = 0.5)
		ax.plot(sweeps[sweep_dim], sweeps.mean(dim = 'repetitions'), color = color, linewidth = 1.5, label = f'{scandir}, average')
	ax.set_xlabel(xlabel)
	ax.set_ylabel(ylabel)
	ax.legend()


def _sweep_value_index(sweep, at):
	"""Index of the sweep point nearest `at`, or the middle of the sweep."""
	if at is None:
		return sweep.size // 2
	return int(abs(sweep.values - at).argmin())


def _draw_image(rhkdata_obj, figure, at):
	axes = figure.subplots(1, 2)
	_show_scan(axes[0], rhkdata_obj, 'topography', _CMAP_TOPO, 'topography, backward')
	_show_scan(axes[1], rhkdata_obj, 'lia', _CMAP_SPEC, 'dI/dV, backward')


def _draw_map(rhkdata_obj, figure, at):
	sweep = _SWEEPS[rhkdata_obj.spectype]
	sweep_dim = sweep['sweep_dim']
	xlabel = f'{sweep["name"]} ({sweep["unit"]})'
	axes = figure.subplots(1, 3)
	_show_scan(axes[0], rhkdata_obj, 'topography', _CMAP_TOPO, 'topography, backward')

	mean = rhkdata_obj.spectra[sweep['signal']].mean(dim = ['repetitions', sweep['scandir_dim']])
	index = _sweep_value_index(mean[sweep_dim], at)
	value = float(mean[sweep_dim][index])
	# rounding and adding zero, so that a value that is really 0 doesn't print as -2.37e-08 or -0
	title = f'map at {sweep["name"]} = {round(value, 6) + 0.0:.4g} {sweep["unit"]}'
	_show_image(axes[1], mean.isel({sweep_dim: index}), 'specpos_x', 'specpos_y', _CMAP_SPEC, sweep['signal_label'], title)
	axes[1].set_xlabel('x (nm)')
	axes[1].set_ylabel('y (nm)')
	axes[1].set_aspect('equal')

	average = mean.mean(dim = ['specpos_x', 'specpos_y'])
	axes[2].plot(average[sweep_dim], average, color = 'black')
	axes[2].axvline(value, color = 'red', linestyle = '--', label = 'mapped value')
	axes[2].set_xlabel(xlabel)
	axes[2].set_ylabel(sweep['signal_label'])
	axes[2].set_title('average over the map')
	axes[2].legend()


def _draw_line(rhkdata_obj, figure, at):
	sweep = _SWEEPS[rhkdata_obj.spectype]
	sweep_dim = sweep['sweep_dim']
	xlabel = f'{sweep["name"]} ({sweep["unit"]})'
	axes = figure.subplots(1, 2)
	mean = rhkdata_obj.spectra[sweep['signal']].mean(dim = ['repetitions', sweep['scandir_dim']])
	_show_image(axes[0], mean, sweep_dim, 'dist', _CMAP_SPEC, sweep['signal_label'], 'along the line')
	axes[0].set_xlabel(xlabel)
	axes[0].set_ylabel('distance (nm)')
	average = mean.mean(dim = 'dist')
	axes[1].plot(average[sweep_dim], average, color = 'black')
	axes[1].set_xlabel(xlabel)
	axes[1].set_ylabel(sweep['signal_label'])
	axes[1].set_title('average along the line')


def _draw_spec(rhkdata_obj, figure, at):
	sweep = _SWEEPS[rhkdata_obj.spectype]
	xlabel = f'{sweep["name"]} ({sweep["unit"]})'
	channels = [('lia', 'dI/dV (pA)', 'dI/dV'), ('current', 'current (pA)', 'current')] if sweep['signal'] == 'lia' else [('current', 'current (pA)', 'current')]
	axes = figure.subplots(1, len(channels), squeeze = False)[0]
	for ax, (channel, label, title) in zip(axes, channels):
		_sweep_lines(ax, rhkdata_obj.spectra[channel], sweep['sweep_dim'], sweep['scandir_dim'], xlabel, label)
		ax.set_title(title)


#: datatype -> function drawing the panels on a Figure; register new types here
_DRAWERS = {'image': _draw_image, 'map': _draw_map, 'line': _draw_line, 'spec': _draw_spec}


def _title(rhkdata_obj):
	"""File, type, and the tunneling conditions, if the file has them."""
	dataset = getattr(rhkdata_obj, 'spectra', getattr(rhkdata_obj, 'image', None))
	kind = rhkdata_obj.datatype if rhkdata_obj.spectype is None else f'{rhkdata_obj.datatype}, {rhkdata_obj.spectype}'
	title = f'{dataset.attrs["filename"]} ({kind})'
	if 'bias' in dataset.attrs and 'setpoint' in dataset.attrs:
		title += f'\nbias {float(dataset.attrs["bias"]):.3g} V, setpoint {float(dataset.attrs["setpoint"]):.4g} pA'
	return title


def preview(rhkdata_obj, path = None, dpi = 150, at = None):
	"""Draw a static picture of a measurement, see :meth:`rhkpy.core.rhkdata.preview`."""
	has_spectra = 'spectra' in rhkdata_obj.__dict__
	has_image = 'image' in rhkdata_obj.__dict__
	if not has_spectra and not has_image:
		raise ValueError(f'{rhkdata_obj.filename} has neither an image nor spectra that rhkpy can plot')

	figure = Figure(figsize = (12, 4.5), layout = 'constrained')
	FigureCanvasAgg(figure)
	# a file with an unsupported line type has only its image
	draw = _DRAWERS[rhkdata_obj.datatype] if has_spectra else _draw_image
	draw(rhkdata_obj, figure, at)
	figure.suptitle(_title(rhkdata_obj))
	if path is not None:
		figure.savefig(path, dpi = dpi)
	return figure
