"""Operations on rhkdata xarray Datasets: coordinate transforms, flattening,
map sections.

Moved verbatim from rhkpy_process.py (refactor phase 2).
"""

import copy

import numpy as np
import xarray as xr
from scipy import ndimage

from .fitting import bgsubtract


def coord_to_absolute(xrobj):
	"""Takes as input the :class:`rhkdata.image` variable of an :class:`~rhkpy.rhkpy_loader.rhkdata` instance.
	Returns a new :py:mod:`xarray` instance, with the coordinates updated to reflect the abolute tip position. This includes X, Y offset and rotation.

	:param xrobj: :py:mod:`xarray` image variable of an :class:`~rhkpy.rhkpy_loader.rhkdata` object
	:type xrobj: :py:mod:`xarray` Dataset
	
	:return: :py:mod:`xarray` :class:`rhkdata.image` instance, with the same data and metadata as the input and the coordinates shifted to absolute tip positions.
	:rtype: :py:mod:`xarray` Dataset

	:Example:
		
		.. code-block:: python

			import rhkpy

			m = rhkpy.rhkdata('didv map.sm4')

			# Take the `rhkdata` instance (image or map): `m`,
			# and convert the image coordinates to absolute values
			m_abs_image = rhkpy.coord_to_absolute(m.image)

			# coordinates of the instance `m`
			# We can see it runs from 0 to 100 nm
			print(m.image.x.min().data, m.image.x.max().data)
			0.0 100.0

			# check the same corrdinate for the new `m_abs`
			print(m_abs_image.x.min().data, m_abs_image.x.max().data)
			-877.0008892433623 -741.0633876547834

			# we can see it's now shows the exact tip position
			# the image is also rotated, as the "scan angle" attribute shows
			m_abs_image.attrs['scan angle']
			30.0
			
			# plot the rotated and offset image
			m_abs_image.topography.sel(scandir = 'forward').plot()
	"""	
	# the xrobj passed to the function should always be and image
	if 'topography' not in xrobj.data_vars:
		raise TypeError('Wrong xarray type. The data needs to be an `image`, not `spectra`')
	if xrobj.attrs['datatype'] == 'line':
		raise NotImplementedError('Sorry, linespectra are not supported yet.')
	
	# get scan angle
	scangle = xrobj.attrs['scan angle']*np.pi/180 # in radians

	# Get the numpy data
	datatopofw = xrobj['topography'].sel(scandir = 'forward').data
	datatopobw = xrobj['topography'].sel(scandir = 'backward').data
	datacurrentfw = xrobj['current'].sel(scandir = 'forward').data
	datacurrentbw = xrobj['current'].sel(scandir = 'backward').data
	dataliafw = xrobj['lia'].sel(scandir = 'forward').data
	dataliabw = xrobj['lia'].sel(scandir = 'backward').data

	# rotate the data by the scan angle. Need to have negative degrees, because ndimage rotates clockwise
	rotatedtopofw = ndimage.rotate(
		datatopofw,
		-scangle*180/np.pi, # needs to be in degrees
		reshape = True, # expand
		mode = 'constant',
		cval = np.nan
		)
	rotatedtopobw = ndimage.rotate(
		datatopobw,
		-scangle*180/np.pi, # needs to be in degrees
		reshape = True, # expand
		mode = 'constant',
		cval = np.nan
		)
	rotatedcurrentfw = ndimage.rotate(
		datacurrentfw,
		-scangle*180/np.pi, # needs to be in degrees
		reshape = True, # expand
		mode = 'constant',
		cval = np.nan
		)
	rotatedcurrentbw = ndimage.rotate(
		datacurrentbw,
		-scangle*180/np.pi, # needs to be in degrees
		reshape = True, # expand
		mode = 'constant',
		cval = np.nan
		)
	rotatedliafw = ndimage.rotate(
		dataliafw,
		-scangle*180/np.pi, # needs to be in degrees
		reshape = True, # expand
		mode = 'constant',
		cval = np.nan
		)
	rotatedliabw = ndimage.rotate(
		dataliabw,
		-scangle*180/np.pi, # needs to be in degrees
		reshape = True, # expand
		mode = 'constant',
		cval = np.nan
		)

	# Create new coordinates for the rotated data
	# size of a pixel in nm
	pixelsizex = np.abs(xrobj.x.data[1] - xrobj.x.data[0])
	pixelsizey = np.abs(xrobj.y.data[1] - xrobj.y.data[0])
	
	# Get the sizes of the x and y coordinates
	xlen = np.abs(xrobj.x.data[-1] - xrobj.x.data[0]) + pixelsizex # need to add half pixel size twice (on both sides)
	ylen = np.abs(xrobj.y.data[-1] - xrobj.y.data[0]) + pixelsizey
	
	# This gives you the new "bounding box size" of the rotated image
	# newxlen = np.abs(xlen * np.sin(scangle)) + np.abs(ylen * np.sin(np.pi/2 - scangle))
	# newylen = np.abs(xlen * np.cos(scangle)) + np.abs(ylen * np.cos(np.pi/2 - scangle))
	newxlen = rotatedtopofw.shape[0] * pixelsizex
	newylen = rotatedtopofw.shape[1] * pixelsizey

	# new coordinate length
	# placing the zero in the middle of the image
	newxx = np.linspace(-newxlen/2, newxlen/2, num = rotatedtopofw.shape[0])
	newyy = np.linspace(-newylen/2, newylen/2, num = rotatedtopofw.shape[1])
	# new pixel size due to rotation
	# newpixelsizex = np.abs(newxx[1] - newxx[0])
	# newpixelsizey = np.abs(newyy[1] - newyy[0])

	# correction to the offset of the image
	# In the RHK Rev software, the offsets shown in the software refer to the bottom - left corner
	# of the image. This does NOT include the rotation. For the proper shift of the image
	# coordinates including rotation this has to be taken into account
	diag = np.sqrt(xlen**2 + ylen**2)
	offx = diag * np.sin(scangle/2) * np.cos(scangle/2 - np.pi/4) + diag * np.cos(np.pi/4 + scangle)/2 - pixelsizex
	offy = diag * np.sin(scangle/2) * np.sin(scangle/2 - np.pi/4) + diag * np.sin(np.pi/4 + scangle)/2 - pixelsizey

	# make a new instance of the object, where we will change the coordinates
	xrobj_abscoord = xr.Dataset(
		data_vars = dict(
			topography = (['y', 'x', 'scandir'], np.stack((rotatedtopofw, rotatedtopobw), axis=-1)),
			current = (['y', 'x', 'scandir'], np.stack((rotatedcurrentfw, rotatedcurrentbw), axis=-1)),
			lia = (['y', 'x', 'scandir'], np.stack((rotatedliafw, rotatedliabw), axis=-1))
			),
		coords = dict(
			x = newxx + xrobj.attrs['xoffset'] + offx,
			y = newyy + xrobj.attrs['yoffset'] + offy,
			scandir = np.array(['forward', 'backward'])
			)
		)
	# copy attributes from original dataset and modify them accordingly
	xrobj_abscoord.attrs = xrobj.attrs.copy()
	for c in xrobj.coords:
		xrobj_abscoord.coords[c].attrs = xrobj.coords[c].attrs.copy()
	for d in xrobj.data_vars:
		xrobj_abscoord[d].attrs = xrobj[d].attrs.copy()
	# append a note to the coordinate x, y attributes
	xrobj_abscoord.attrs['comment'] = 'absolute coordinates'
	xrobj_abscoord.coords['x'].attrs['note'] += 'absolute coordinates\n'
	xrobj_abscoord.coords['y'].attrs['note'] += 'absolute coordinates\n'

	return xrobj_abscoord

def polyflatten(xrobj, field_type = 'topography', **kwargs):
	"""Fits a polynomial to the fast scan lines of topography data and subtracts it from the lines.
	
	The keyword argument ``polyorder`` works the same way as in :func:`bgsubtract`.
	Keywords used by :func:`bgsubtract` can be passed.
	
	Still needs testing.

	:param xrobj: :py:mod:`xarray` image variable of an :class:`~rhkpy.rhkpy_loader.rhkdata` object
	:type xrobj: :py:mod:`xarray` Dataset, :class:`rhkdata.image`
	:param field_type: select the DataArray: 'topography', 'current' or 'lia', defaults to 'topography'
	:type field_type: str, optional
	
	:return: New :class:`rhkdata.image` Dataset of :class:`~rhkpy.rhkpy_loader.rhkdata`, with the DataArray specifiec by ``field_type`` flattened.
	:rtype: :py:mod:`xarray` Dataset
	"""	

	# check if the right object was passed
	# the xrobj passed to the function should always be and image
	if field_type not in xrobj.data_vars:
		raise TypeError('Wrong xarray type. The data needs to be an `image`')
	
	# make a copy of the xrobject
	flatxrobj = copy.deepcopy(xrobj)

	# iterate through the scan directions of the image
	for scand in flatxrobj.scandir:
		# select the scan direction
		datafield = flatxrobj[field_type].sel(scandir = scand.data)
		# iterate through the slow scan direction lines
		for yy in datafield.y:
			# fit the background
			_, bg_values, _, _, _, _ = bgsubtract(datafield.sel(y = yy).x.data, datafield.sel(y = yy).data, exclusion_factor = 1, **kwargs)
			# subtract the background
			datafield.sel(y = yy).data -= bg_values

	return flatxrobj

## plotting and data visualization -------------------------------------------

def mapsection(specmap, start_point, end_point):
	"""Makes a section across a dI/dV spectroscopy map: ``specmap``. Starting and end points: ``start_point`` to ``end_point``.
	It uses :py:mod:`xarray.Dataset.interp` to interpolate between data values.

	:param specmap: the `spectra` :py:mod:`xarray` variable of an :class:`~rhkpy.rhkpy_loader.rhkdata` instance. Found under: :class:`rhkpy.rhkpy_loader.rhkdata.spectra`.
	:type specmap: :py:mod:`xarray` DataSet
	:param start_point: starting point for the line section. In the format: `(x, y)`, found in the ``specpos_x``, ``specpos_y`` coordinates of ``specmap``.
	:type start_point: tuple: (float, float)
	:param end_point: end point for the line section. In the format: `(x, y)`, found in the ``specpos_x``, ``specpos_y`` coordinates of ``specmap``.
	:type end_point: tuple: (float, float)
	
	:return: :py:mod:`xarray` DataSet of the line section
	:rtype: :py:mod:`xarray` DataSet
	"""	
	# Extract the start and end coordinates
	x_start, y_start = start_point
	x_end, y_end = end_point
	
	# Get the pixel resolution needed for the section.
	pixelsize = np.abs(specmap.specpos_x[1] - specmap.specpos_x[0]).data
	dist_length = np.sqrt((x_end - x_start)**2 + (y_end - y_start)**2)

	# Define the line coordinates
	line_x_coords = xr.DataArray(np.linspace(x_start, x_end, int(dist_length / pixelsize) + 1), dims = 'dist')
	line_y_coords = xr.DataArray(np.linspace(y_start, y_end, int(dist_length / pixelsize) + 1), dims = 'dist')

	# Dictionary to store the sections for each variable
	sections_dict = {}

	# Loop through the variables in the dataset
	for var_name, var_data in specmap.data_vars.items():
		# Interpolate along the specified line
		interpolated_values = var_data.interp(specpos_x = line_x_coords, specpos_y = line_y_coords)
		# Store the interpolated values in the dictionary
		sections_dict[var_name] = interpolated_values
	
	# Create a new xarray Dataset containing the sections
	# new distance dimension coordinates
	dist = np.sqrt((line_x_coords.data - line_x_coords.data[0]) ** 2 + (line_y_coords.data - line_y_coords.data[0]) ** 2)
	
	sections_dataset = xr.Dataset(sections_dict)
	# drop the unused coordinates
	sections_dataset = sections_dataset.drop_vars(['specpos_x', 'specpos_y'])
	# assign the dist coordinate
	sections_dataset = sections_dataset.assign_coords(dist = dist)

	# add metadata to dist coordinate
	sections_dataset.coords['dist'].attrs['units'] = 'nm'
	sections_dataset.coords['dist'].attrs['long units'] = 'nanometer'
	
	return sections_dataset
