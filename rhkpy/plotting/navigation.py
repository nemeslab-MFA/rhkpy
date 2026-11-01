"""Overview plot of multiple rhkdata instances at absolute tip positions.

Moved verbatim from rhkpy_process.py (refactor phase 2).
"""

import hvplot.xarray  # noqa: F401 - registers the .hvplot accessor
import holoviews as hv


def navigation(*args, **kwargs):
	"""Takes any number of :class:`~rhkpy.rhkpy_loader.rhkdata` arguments: 'map', 'line', 'spec' and plots all of them on a single plot.
	Plotting of the spectroscopy positions can be skipped by setting the optional keyword: ``plot_spec`` to `False`.
	Plotting is done in the order of passing of the arguments. First argument will be plotted first.

	The color map used for plotting topography images can be specified by the ``cmap`` optional keyword argument. Default value is 'bone'.

	Colors for use in the labels can be specified by the optional keyword: ``palette_name``. If this is used, the number of colors also needs to be specified, by: ``num_colors``.
	For possible palette options look at the `bokeh palettes <https://docs.bokeh.org/en/latest/docs/reference/palettes.html>`_.

	:return: :py:mod:`holoviews` plot
	:rtype: :py:mod:`holoviews`

	:Example:
		
		.. code-block:: python

			import rhkpy

			# Load some data
			didvmap = rhkpy.rhkdata('didvmap path/map.sm4')
			topography = rhkpy.rhkdata('topo path/topo1.sm4')
			single_spec = rhkpy.rhkdata('single spec path/single spec.sm4')

			# plot the topography and spectroscopy positions
			rhkpy.navigation(topography, didvmap, single_spec)

			# skip plotting the spectroscopy positions
			rhkpy.navigation(topography, didvmap, single_spec, plot_spec = False)

			# In the above examples, the image from topography
			# is plotted before the image data of didivmap!
			# You can change the plotting order by changing
			# the order of the `rhkdata` instances in the arguments.
			rhkpy.navigation(didvmap, topography, single_spec) # now didvmap is plotted first

	.. note::

		Arguments are plotted in the order they are passed to :func:`navigation`.

		The spectroscopy positions in dI/dV maps can be simply visualized by just passing the map :class:`~rhkpy.rhkpy_loader.rhkdata` instance.

	"""	
	# arguments should be rhkdata instances
	# take care of optional keyword arguments
	# an optional argument is plot_spec. If False, the spectroscopy positions are not plotted
	if 'plot_spec' not in kwargs:
		plot_spec = True
	else:
		plot_spec = kwargs['plot_spec']
	if 'cmap' not in kwargs:
		cmap = 'bone'
	else:
		cmap = kwargs['cmap']
	if 'palette_name' not in kwargs:
		palette_name = 'Category10'
	else:
		palette_name = kwargs['palette_name']
	if 'num_colors' not in kwargs:
		num_colors = 10
	else:
		num_colors = kwargs['num_colors']

	# we need a function to plot a bounding box around the topo data
	def bounding_box(rhkdata_obj, c):
		l_top = rhkdata_obj.image.topography.drop_vars('scandir')[-1, :].hvplot.line(x = 'x', y = 'y', color = c, label = rhkdata_obj.image.attrs['filename']) # label = rhkdata_obj.image.attrs['filename']
		l_bottom = rhkdata_obj.image.topography.drop_vars('scandir')[0, :].hvplot.line(x = 'x', y = 'y', color = c, label = rhkdata_obj.image.attrs['filename'])
		l_left = rhkdata_obj.image.topography.drop_vars('scandir')[:, 0].hvplot.line(x = 'x', y = 'y', color = c, label = rhkdata_obj.image.attrs['filename'])
		l_right = rhkdata_obj.image.topography.drop_vars('scandir')[:, -1].hvplot.line(x = 'x', y = 'y', color = c, label = rhkdata_obj.image.attrs['filename'])
		return l_bottom * l_left * l_right * l_top

	def plot_spec_positions(rhkdata_obj, c):
		if rhkdata_obj.datatype == 'map':
			if rhkdata_obj.spectype == 'iv':
				_ = rhkdata_obj.spectra.drop_vars(['bias', 'repetitions', 'biasscandir']).drop_vars(['lia', 'current'])
				specplot = _.hvplot.scatter(x = 'x', y = 'y', groupby = [], marker = 'x', color = c, label = 'spec pos: ' + rhkdata_obj.image.attrs['filename'])
			elif rhkdata_obj.spectype == 'iz':
				_ = rhkdata_obj.spectra.drop_vars(['z', 'repetitions', 'zscandir']).drop_vars(['current'])
				specplot = _.hvplot.scatter(x = 'x', y = 'y', groupby = [], marker = 'x', color = c, label = 'spec pos: ' + rhkdata_obj.image.attrs['filename'])
		elif rhkdata_obj.datatype == 'line':
			if rhkdata_obj.spectype == 'iv':
				_ = rhkdata_obj.spectra.drop_vars(['lia', 'current']).drop_vars(['biasscandir', 'repetitions', 'bias'])
				specplot = _.hvplot.scatter(x = 'x', y = 'y', groupby = [], marker = 'x', color = c, label = 'spec pos: ' + rhkdata_obj.spectra.attrs['filename'])
			elif rhkdata_obj.spectype == 'iz':
				_ = rhkdata_obj.spectra.drop_vars(['current']).drop_vars(['zscandir', 'repetitions', 'z'])
				specplot = _.hvplot.scatter(x = 'x', y = 'y', groupby = [], marker = 'x', color = c, label = 'spec pos: ' + rhkdata_obj.spectra.attrs['filename'])
		elif rhkdata_obj.datatype == 'spec':
			# specplot = rhkdata_obj.spectra.hvplot.scatter(x = 'x', y = 'y', groupby = [], marker = 'x', color = c, size = 200, line_width = 3, label = 'spec pos: ' + rhkdata_obj.spectra.attrs['filename'])
			specplot = hv.Scatter((rhkdata_obj.spectra.x.data, rhkdata_obj.spectra.y.data), label = 'spec pos: ' + rhkdata_obj.spectra.attrs['filename']).opts(marker = 'x', size = 20, line_width = 3)
		else:
			# it should never get to this point
			specplot = hv.Empty()
		return specplot

	if len(args) == 0:
		raise ValueError('Please supply some rhkdata instances to plot.')

	datatypes = []
	spectypes = []
	for stmdata in args:
		datatypes += [stmdata.datatype]
		spectypes += [stmdata.spectype]

	# get the indices, where the datatype has an image or has spectroscopy data
	indices_topo = []
	indices_spec = []
	for index, value in enumerate(datatypes):
		if value in ('map', 'image'):
			indices_topo += [index]
		if value in ('map', 'line', 'spec'):
			indices_spec += [index]
	# indices_topo = [index for index, value in enumerate(datatypes) if value in ('map', 'image')]

	if indices_topo == [] and (plot_spec is not True or indices_spec == []):
		raise ValueError('Nothing to plot: the rhkdata instances have no images, and spectrum positions are not requested.')

	# plot those images
	# get a color map for the bounding boxes
	from bokeh.palettes import all_palettes
	from itertools import cycle
	colors = all_palettes[palette_name][num_colors]
	# make the color list cyclic
	color_cycle = cycle(colors)

	# do the first plot
	if indices_topo != []:
		# plot the first one
		topo_abs = args[indices_topo[0]].coord_to_absolute()
		navi_plot = topo_abs._qplot_topo(cmap_topo = cmap, clabel = 'height (nm)', label = topo_abs.image.attrs['filename'])
		# draw a bounding box
		navi_plot *= bounding_box(topo_abs, next(color_cycle))
		for i in indices_topo[1:]:
			topo_abs = args[i].coord_to_absolute()
			navi_plot *= topo_abs._qplot_topo(cmap_topo = cmap, label = topo_abs.image.attrs['filename'])
			# plot a bounding box around the image
			navi_plot *= bounding_box(topo_abs, next(color_cycle))
		
	# if plot_spec is True, plot the spectra positions
	if plot_spec is True:
		if indices_spec != []:
			# plot the first one if no topography data was passed
			if indices_topo == []:
				navi_plot = plot_spec_positions(args[indices_spec[0]], next(color_cycle))
			else:
				navi_plot *= plot_spec_positions(args[indices_spec[0]], next(color_cycle))
			# for datatypes containing a spectrum, plot the spectrum positions
			for i in indices_spec[1:]:
				navi_plot *= plot_spec_positions(args[i], next(color_cycle))

	return navi_plot.opts(frame_width = 400, frame_height = 400, legend_position = 'right', title = ' ')
