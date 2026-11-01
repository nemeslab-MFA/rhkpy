"""Builders: turn the raw sm4 Dataset (`spymdata`) into the `image` and
`spectra` xarray Datasets of an rhkdata instance.

The central piece is ``_BUILDER_REGISTRY``: it maps every supported
(datatype, spectype) combination to its spectra builder and metadata
function. To add support for a new measurement type:

1. add a spectra builder (see :mod:`rhkpy.builders.spectra`),
2. add or reuse a metadata function (see :mod:`rhkpy.builders.metadata`),
3. register the pair here,
4. teach :func:`rhkpy.builders.detect._checkdatatype` to recognize the type,
5. add a quick plot layout in :mod:`rhkpy.plotting.quickplot`.
"""

from ..analysis.ops import polyflatten

from .detect import _checkrepetitions, _checkdatatype, _aspect_ratio, _get_filename, _is_single_sweep
from .spectra import _xr_map_iv, _xr_line_iv, _xr_spec_iv, _xr_map_iz, _xr_line_iz, _xr_spec_iz
from .image import _xr_image, _xr_image_line
from .metadata import _add_map_metadata, _add_line_metadata, _add_spec_metadata, _add_image_metadata

#: (datatype, spectype) -> (spectra builder, metadata function)
_BUILDER_REGISTRY = {
	('map', 'iv'): (_xr_map_iv, _add_map_metadata),
	('map', 'iz'): (_xr_map_iz, _add_map_metadata),
	('line', 'iv'): (_xr_line_iv, _add_line_metadata),
	# historical quirk, preserved: I(z) lines get the single-spectrum metadata
	('line', 'iz'): (_xr_line_iz, _add_spec_metadata),
	('spec', 'iv'): (_xr_spec_iv, _add_spec_metadata),
	('spec', 'iz'): (_xr_spec_iz, _add_spec_metadata),
}


def _build_spectra(stmdata_object):
	"""Build the `spectra` Dataset and attach its metadata, dispatching on
	(datatype, spectype) through the registry."""
	key = (stmdata_object.datatype, stmdata_object.spectype)
	builder, add_metadata = _BUILDER_REGISTRY[key]
	stmdata_object = builder(stmdata_object)
	stmdata_object = add_metadata(stmdata_object)
	return stmdata_object


def _load_specmap(stmdata_object):
	"""Populate an rhkdata instance of datatype 'map': image plus spectra grid."""
	# total number of spectra in one postion of the tip
	stmdata_object.numberofspectra = int((stmdata_object.alternate + 1)*stmdata_object.repetitions)
	# load the image
	stmdata_object = _load_image(stmdata_object)
	# create a DataSet containing the spectroscopy data, with metadata
	return _build_spectra(stmdata_object)


def _load_line(stmdata_object):
	"""Populate an rhkdata instance of datatype 'line': image plus spectra along a line."""
	# total number of spectra in one postion of the tip
	stmdata_object.numberofspectra = int((stmdata_object.alternate + 1)*stmdata_object.repetitions)
	# load the image data
	stmdata_object = _load_image(stmdata_object)
	# create a DataSet containing the spectroscopy data, with metadata
	return _build_spectra(stmdata_object)


def _load_spec(stmdata_object):
	"""Populate an rhkdata instance of datatype 'spec': repeated spectra at one position."""
	# in this case the total number of spectra can be inferred
	# total number of spectra in one postion of the tip
	stmdata_object.repetitions = int(stmdata_object.spymdata.Current.data.shape[1] / (stmdata_object.alternate + 1))
	stmdata_object.numberofspectra = int((stmdata_object.alternate + 1)*stmdata_object.repetitions)
	# create a DataSet containing the spectroscopy data, with metadata
	return _build_spectra(stmdata_object)


def _load_image(stmdata_object):
	"""Build the `image` Dataset with metadata; unless loadraw is set, flatten
	the topography with a first order polynomial background subtraction."""
	# load the image data
	if stmdata_object.datatype == 'image' or stmdata_object.datatype == 'map':
		stmdata_object = _xr_image(stmdata_object)
	elif stmdata_object.datatype == 'line':
		stmdata_object = _xr_image_line(stmdata_object)
	# add metadata
	stmdata_object = _add_image_metadata(stmdata_object)

	# make a polynomial background subtraction to the topography data (flatten)
	if stmdata_object.loadraw is False:
		stmdata_object.image = polyflatten(stmdata_object.image, polyorder = 1)
	return stmdata_object
