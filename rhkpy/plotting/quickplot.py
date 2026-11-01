"""Quick-plot internals for rhkdata instances.

These are the implementations behind :meth:`rhkpy.rhkdata.qplot` and the
``rhkdata._qplot_*`` methods.

Structure:

- ``_fwbw_lineplot`` - the shared forward/backward sweep overlay used by every
  1D spectrum plot (all repetitions dotted, average in bold)
- ``_mean_signal_image`` - the shared 2D density plot of the sweep-averaged
  signal used by map and line plots
- ``_QPLOT_LAYOUTS`` - registry mapping (datatype, spectype) to the panel
  layout of :func:`qplot`; add an entry here to support a new measurement type

Output is identical to rhkpy <= 1.3 (same data selections, colors, labels and
panel arrangement).
"""

import hvplot.xarray  # noqa: F401 - registers the .hvplot accessor
import panel as pn


## shared plot building blocks ----------------------------------------

def _fwbw_lineplot(da, x: str, scandir_dim: str, labels: tuple[str, str]):
	"""Overlay the forward/backward sweeps of a 1D signal.

	With a single repetition, plots the two sweeps in red/blue with legend
	labels. With multiple repetitions, plots every repetition as a dotted
	light-colored line and the repetition average in bold on top. A single sweep
	measurement only has the forward sweep.

	:param da: DataArray with dims (..., 'repetitions', scandir_dim)
	:param x: name of the sweep coordinate ('bias' or 'z')
	:param scandir_dim: name of the sweep direction dim ('biasscandir' or 'zscandir')
	:param labels: legend labels for the two sweep directions, e.g. ('left', 'right')
	"""
	label_fw, label_bw = labels

	def _sweep_plot(sweep, label, color, repetition_color):
		if len(da.repetitions) == 1:
			return da.isel({'repetitions': 0, scandir_dim: sweep}).hvplot.line(x = x, color = color, label = label)
		plot = da.isel({'repetitions': 0, scandir_dim: sweep}).hvplot.line(x = x, color = repetition_color, line_dash = 'dotted', line_width = 0.5, alpha = 1)
		for i in range(1, len(da.repetitions)):
			# iterate through the repetitions and plot on the same plot
			plot *= da.isel({'repetitions': i, scandir_dim: sweep}).hvplot.line(x = x, color = repetition_color, line_dash = 'dotted', line_width = 0.5, alpha = 1)
		plot *= da.mean(dim = 'repetitions').isel({scandir_dim: sweep}).hvplot.line(x = x, color = color, line_width = 2, label = 'avg ' + label)
		return plot

	plot_fw = _sweep_plot(0, label_fw, 'red', 'LightCoral')
	if da.sizes[scandir_dim] == 1:
		return plot_fw
	plot_bw = _sweep_plot(1, label_bw, 'blue', 'LightSkyBlue')

	# combine the forward and backward sweeps
	return plot_fw * plot_bw


def _mean_signal_image(rhkdata_obj, signal: str, scandir_dim: str, cmap_spec: str, **imageopts):
	"""2D density plot of a signal averaged over repetitions and sweep direction.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:param signal: name of the data variable in ``spectra`` ('lia' or 'current')
	:type signal: str
	:param scandir_dim: name of the sweep direction dim ('biasscandir' or 'zscandir')
	:type scandir_dim: str
	:param cmap_spec: colorscale of the density plot
	:type cmap_spec: str
	:param imageopts: further options passed to :py:mod:`hvplot` (x, y, groupby, title, ...)

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	meanmap = rhkdata_obj.spectra.mean(dim = ['repetitions', scandir_dim])
	return meanmap[signal].hvplot.image(cmap = cmap_spec, **imageopts)


## plots of the individual panels -------------------------------------

def plot_topo(rhkdata_obj, cmap_topo = 'fire', **kwargs):
	"""Plotting topography data using :py:mod:`hvplot`.

	:param cmap_topo: colorscale used for topography data, defaults to 'fire'
	:type cmap_topo: str, optional

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	# The backward direction should be plotted, since this is the direction in which the tip moves, when the spectroscopy data is measured.
	return rhkdata_obj.image.topography[:, :, 1].hvplot.image(x = 'x', y = 'y', cmap = cmap_topo, title = 'topography backward', **kwargs)


def plot_lia(rhkdata_obj, cmap_spec = 'viridis', **kwargs):
	"""Plotting dI/dV image data using :py:mod:`hvplot`.

	:param cmap_spec: colorscale used for dI/dV data, defaults to 'viridis'
	:type cmap_spec: str, optional

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return rhkdata_obj.image.lia[:, :, 1].hvplot.image(cmap = cmap_spec, x = 'x', y = 'y', title = 'dI/dV backward')


def plot_map_iv(rhkdata_obj, cmap_spec = 'viridis', **kwargs):
	"""Plotting dI/dV map data using :py:mod:`hvplot`.
	The mean values (biasscandir and repetitions) of the dI/dV signal are plotted on the density plot.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`
	:param cmap_spec: colorscale used for dI/dV data, defaults to 'viridis'
	:type cmap_spec: str, optional

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _mean_signal_image(rhkdata_obj, 'lia', 'biasscandir', cmap_spec,
		x = 'specpos_x', y = 'specpos_y', groupby = 'bias', title = 'dI/dV map')


def plot_map_iz(rhkdata_obj, cmap_spec = 'viridis', **kwargs):
	"""Plotting I(z) map data using :py:mod:`hvplot`.
	The mean values (zscandir and repetitions) of the I(z) signal are plotted on the density plot.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`
	:param cmap_spec: colorscale used for I(z) data, defaults to 'viridis'
	:type cmap_spec: str, optional

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _mean_signal_image(rhkdata_obj, 'current', 'zscandir', cmap_spec,
		x = 'specpos_x', y = 'specpos_y', groupby = 'z', title = 'I(z) map')


def plot_line_iv(rhkdata_obj, cmap_spec = 'viridis', **kwargs):
	"""Plotting dI/dV line data on a density plot (bias vs distance), using :py:mod:`hvplot`.
	The mean values of the dI/dV signal are plotted on the density plot.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`
	:param cmap_spec: colorscale used for dI/dV data, defaults to 'viridis'
	:type cmap_spec: str, optional

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _mean_signal_image(rhkdata_obj, 'lia', 'biasscandir', cmap_spec,
		x = 'bias', y = 'dist', title = 'dI/dV line spectra', aspect = 1)


def plot_line_iz(rhkdata_obj, cmap_spec = 'viridis', **kwargs):
	"""Plotting I(z) line data on a density plot (tip height vs distance), using :py:mod:`hvplot`.
	The mean values of the I(z) signal are plotted.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`
	:param cmap_spec: colorscale used for I(z) data, defaults to 'viridis'
	:type cmap_spec: str, optional

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _mean_signal_image(rhkdata_obj, 'current', 'zscandir', cmap_spec,
		x = 'z', y = 'dist', title = 'I(z) line spectra', aspect = 1)


def plot_line_spec_iv(rhkdata_obj, **kwargs):
	"""Plotting dI/dV spectra of a line spectroscopy instance, using :py:mod:`hvplot`.
	All repetitions are shown as dotted lines, with the repetition average in bold.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _fwbw_lineplot(rhkdata_obj.spectra.lia, 'bias', 'biasscandir', ('left', 'right'))


def plot_line_spec_iz(rhkdata_obj, **kwargs):
	"""Plotting I(z) spectra of a line spectroscopy instance, using :py:mod:`hvplot`.
	All repetitions are shown as dotted lines, with the repetition average in bold.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _fwbw_lineplot(rhkdata_obj.spectra.current, 'z', 'zscandir', ('up', 'down'))


def plot_spec_iv_lia(rhkdata_obj, **kwargs):
	"""Plotting the dI/dV signal of a single spectrum instance, using :py:mod:`hvplot`.
	All repetitions are shown as dotted lines, with the repetition average in bold.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	overlay = _fwbw_lineplot(rhkdata_obj.spectra.lia, 'bias', 'biasscandir', ('left', 'right'))
	return overlay.opts(width = 400, title = 'dI/dV')


def plot_spec_iv_curr(rhkdata_obj, **kwargs):
	"""Plotting the current signal of a single spectrum instance, using :py:mod:`hvplot`.
	All repetitions are shown as dotted lines, with the repetition average in bold.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	overlay = _fwbw_lineplot(rhkdata_obj.spectra.current, 'bias', 'biasscandir', ('left', 'right'))
	return overlay.opts(width = 400, title = 'current')


def plot_spec_iz(rhkdata_obj, **kwargs):
	"""Plotting an I(z) single spectrum instance, using :py:mod:`hvplot`.
	All repetitions are shown as dotted lines, with the repetition average in bold.

	:param rhkdata_obj: the :class:`~rhkpy.rhkpy_loader.rhkdata` instance to plot
	:type rhkdata_obj: :class:`~rhkpy.rhkpy_loader.rhkdata`

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`
	"""
	return _fwbw_lineplot(rhkdata_obj.spectra.current, 'z', 'zscandir', ('up', 'down'))


## qplot layouts per (datatype, spectype) ------------------------------

def _layout_image(rhkdata_obj, width, **kwargs):
	"""Topography and dI/dV image side by side."""
	topo_plot = plot_topo(rhkdata_obj, **kwargs)
	lia_plot = plot_lia(rhkdata_obj, **kwargs)
	return pn.Row(pn.panel(topo_plot), pn.panel(lia_plot))


def _layout_map(plot2d):
	"""Topography next to the (widget-driven) 2D spectroscopy plot."""
	def layout(rhkdata_obj, width, **kwargs):
		specplot = plot2d(rhkdata_obj, **kwargs)
		# plot the topography
		topoplot = plot_topo(rhkdata_obj, **kwargs)
		# adjust options
		topoplot.opts(frame_width = width)
		specplot.opts(frame_width = width)
		# separate the plots and the widget into panels, so I can place the widget
		topo_static = pn.panel(topoplot)
		spec_dynamic = pn.panel(specplot)
		# extract the widget
		widget_panel = spec_dynamic[0]
		specplot_static = spec_dynamic[1]
		# combined plot
		return pn.Row(topo_static, pn.Column(widget_panel, specplot_static))
	return layout


def _layout_line(plot2d, plotspec):
	"""2D density plot next to the (widget-driven) spectra overlay."""
	def layout(rhkdata_obj, width, **kwargs):
		specplot = plot2d(rhkdata_obj, **kwargs)
		# plot a selected spectrum along the dist dimension
		combined = plotspec(rhkdata_obj, **kwargs)
		# if the width parameter is specified, set the size of the plots
		if width is None:
			twod_plot_panel = pn.panel(specplot)
			combined_panel = pn.panel(combined)
		else:
			twod_plot_panel = pn.panel(specplot.opts(frame_width = int(0.8*width)))
			combined_panel = pn.panel(combined.opts(frame_width = width))
		# separate the widget and plot into panels
		plot_panel = combined_panel[0]
		plot_widget = combined_panel[1]
		# combined plot
		return pn.Row(twod_plot_panel, pn.Column(plot_widget, plot_panel))
	return layout


def _layout_spec_iv(rhkdata_obj, width, **kwargs):
	"""dI/dV and current signal of a single spectrum side by side."""
	leftpanel = plot_spec_iv_lia(rhkdata_obj, **kwargs)
	rightpanel = plot_spec_iv_curr(rhkdata_obj, **kwargs)
	return pn.Row(pn.panel(leftpanel), pn.panel(rightpanel))


def _layout_spec_iz(rhkdata_obj, width, **kwargs):
	"""Single panel with the I(z) sweep overlay."""
	combined = plot_spec_iz(rhkdata_obj, **kwargs)
	return pn.panel(combined.opts(width = 400, title = 'current'))


#: (datatype, spectype) -> layout function; register new measurement types here
_QPLOT_LAYOUTS = {
	('image', None): _layout_image,
	('map', 'iv'): _layout_map(plot_map_iv),
	('map', 'iz'): _layout_map(plot_map_iz),
	('line', 'iv'): _layout_line(plot_line_iv, plot_line_spec_iv),
	('line', 'iz'): _layout_line(plot_line_iz, plot_line_spec_iz),
	('spec', 'iv'): _layout_spec_iv,
	('spec', 'iz'): _layout_spec_iz,
}


def qplot(rhkdata_obj, width = None, **kwargs):
	"""Quick plot of an :class:`~rhkpy.rhkpy_loader.rhkdata` instance.
	See :meth:`rhkpy.rhkpy_loader.rhkdata.qplot` for the documented interface.
	"""
	key = (rhkdata_obj.datatype, rhkdata_obj.spectype)
	try:
		layout = _QPLOT_LAYOUTS[key]
	except KeyError:
		raise ValueError(f'qplot does not support datatype/spectype combination: {key}') from None
	return layout(rhkdata_obj, width, **kwargs)
