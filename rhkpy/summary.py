"""A plain, JSON-ready description of what a measurement contains.

Meant for scripts and AI agents, which can't look at a :meth:`~rhkpy.core.rhkdata.qplot`
widget. Everything comes from the Datasets the builders already constructed.
"""

import datetime
import os

import numpy as np

from .builders.detect import _is_single_sweep, _may_alternate


def _number(value, digits = 6):
	"""A numpy or Python number as a Python float, without float32 rounding noise.
	Missing values stay `None`."""
	return None if value is None else round(float(value), digits)


def _isodate(date):
	"""RHK's MM/DD/YY date as YYYY-MM-DD, or unchanged if it has another form."""
	try:
		return datetime.datetime.strptime(date, '%m/%d/%y').date().isoformat()
	except (TypeError, ValueError):
		return date


def _channels(dataset, names):
	"""Units of the given data variables of a Dataset."""
	return {name: dataset[name].attrs.get('units') for name in names if name in dataset.data_vars}


def _image_summary(image, loadraw):
	attrs = image.attrs
	return {
		'pixels': {'x': image.sizes['x'], 'y': image.sizes['y']},
		'size_nm': {'x': _number(attrs.get('size_x')), 'y': _number(attrs.get('size_y'))},
		'offset_nm': {'x': _number(attrs.get('xoffset')), 'y': _number(attrs.get('yoffset'))},
		'scan_angle': _number(attrs.get('scan angle')),
		'flattened': not loadraw,
		'channels': _channels(image, ['topography', 'current', 'lia']),
	}


def _spectra_summary(spectra):
	attrs = spectra.attrs
	sweep_name = 'bias' if 'bias' in spectra.coords else 'z'
	sweep = spectra.coords[sweep_name]
	summary = {
		'sizes': dict(spectra.sizes),
		'sweep': {
			'name': sweep_name,
			'start': _number(sweep.values[0]),
			'stop': _number(sweep.values[-1]),
			'points': sweep.size,
			'units': sweep.attrs.get('units', 'V' if sweep_name == 'bias' else 'nm'),
		},
		'channels': _channels(spectra, ['lia', 'current']),
		'tip_position_nm': {
			'x': [_number(spectra['x'].min()), _number(spectra['x'].max())],
			'y': [_number(spectra['y'].min()), _number(spectra['y'].max())],
		},
		'time_per_point_s': _number(spectra['current'].attrs.get('time_per_point'), 9),
		'lock_in': None,
	}
	if 'LI frequency' in attrs:
		summary['lock_in'] = {
			'amplitude_mV': _number(attrs.get('LI amplitude')),
			'frequency_Hz': _number(attrs.get('LI frequency')),
			'phase': _number(attrs.get('LI phase')),
		}
	return summary


def _notes(rhkdata_obj, minor_version):
	"""Things the numbers don't say, which change how the data should be read."""
	notes = []
	if minor_version < 6:
		notes.append('Written by an RHK Rev version before 6, which rhkpy is less tested on.')
	if rhkdata_obj.datatype in ('map', 'line', 'spec'):
		if _is_single_sweep(rhkdata_obj):
			notes.append('One spectrum per tip position, so there is a single scan direction. Its label comes from the sweep axis order and is not a measured direction.')
		elif not rhkdata_obj.alternate and _may_alternate(rhkdata_obj):
			notes.append('Loaded with alternate = False: if the file has forward and backward sweeps, they are mixed in the repetitions.')
		if not hasattr(rhkdata_obj, 'spectra'):
			line_type = rhkdata_obj.spymdata.Current.attrs['RHK_LineTypeName']
			notes.append(f'Spectra with line type {line_type} are not supported, so there is no `spectra` Dataset.')
	return notes


def summarize(rhkdata_obj):
	"""Describe a measurement, see :meth:`rhkpy.core.rhkdata.summary`."""
	image = getattr(rhkdata_obj, 'image', None)
	spectra = getattr(rhkdata_obj, 'spectra', None)
	attrs = spectra.attrs if spectra is not None else image.attrs if image is not None else {}
	pages = list(rhkdata_obj.spymdata.keys())
	minor_version = int(rhkdata_obj.spymdata[pages[-1]].attrs['RHK_MinorVer'])

	return {
		'filename': os.path.basename(rhkdata_obj.filename),
		'path': str(rhkdata_obj.filename),
		'datatype': rhkdata_obj.datatype,
		'spectype': rhkdata_obj.spectype,
		'measurement_date': _isodate(attrs.get('measurement date')),
		'measurement_time': attrs.get('measurement time'),
		'rhk_minor_version': minor_version,
		'bias_V': _number(attrs.get('bias')),
		'setpoint_pA': _number(attrs.get('setpoint'), 3),
		'alternate': bool(rhkdata_obj.alternate),
		'repetitions': int(rhkdata_obj.repetitions),
		'image': None if image is None else _image_summary(image, rhkdata_obj.loadraw),
		'spectra': None if spectra is None else _spectra_summary(spectra),
		'notes': _notes(rhkdata_obj, minor_version),
	}


def scan(folder = './', recursive = False):
	"""Describe every .sm4 file in a folder, using :meth:`rhkpy.core.rhkdata.summary`.
	A file that can't be loaded gets an entry with its error, and the scan continues.

	:param folder: path of the folder, defaults to the current folder
	:type folder: str, optional
	:param recursive: also look in subfolders, defaults to False
	:type recursive: bool, optional

	:return: one dict per file, in sorted path order. Files that failed to load have only the keys 'filename', 'path' and 'error'.
	:rtype: list
	:raises FileNotFoundError: if the folder doesn't exist

	:Example:

		.. code-block:: python

			import rhkpy

			maps = [s['filename'] for s in rhkpy.scan('data/') if s.get('datatype') == 'map']
	"""
	# imported here because rhkpy.core uses this module
	from .core import rhkdata

	if not os.path.isdir(folder):
		raise FileNotFoundError(f'No such folder: {folder}')

	paths = []
	for root, subfolders, filenames in os.walk(folder):
		paths += [os.path.join(root, f) for f in filenames if f.lower().endswith('.sm4')]
		if not recursive:
			break

	summaries = []
	for path in sorted(paths):
		try:
			summaries.append(rhkdata(path).summary())
		except Exception as exc:
			summaries.append({'filename': os.path.basename(path), 'path': path, 'error': f'{type(exc).__name__}: {exc}'})
	return summaries
