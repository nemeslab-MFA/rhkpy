"""Detection of datatype/spectype and small filename/geometry helpers.

Moved verbatim from rhkpy_loader.py (refactor phase 2).
"""

import logging
import re

import numpy as np

_logger = logging.getLogger('rhkpy')

# spectype implied by the units of the sweep axis of the spectra
_SPECTYPE_FROM_XUNITS = {'V': 'iv', 'm': 'iz'}


def _spectra_per_position(stmdata_object):
	"""Number of spectra per tip position, from the number of identical tip
	coordinates in the RHK_SpecDrift attributes."""
	# make an array of x and y coordinates
	coordlist = np.column_stack((
		np.array(stmdata_object.spymdata.Current.attrs['RHK_SpecDrift_Xcoord']),
		np.array(stmdata_object.spymdata.Current.attrs['RHK_SpecDrift_Ycoord'])
	))
	# get the number of unique pairs
	_, counts = np.unique(coordlist, axis=0, return_counts=True)
	return counts.max()


def _is_single_sweep(stmdata_object):
	"""`True` if the file has one spectrum per tip position, so there is neither
	a second sweep direction nor a repetition to separate."""
	return _spectra_per_position(stmdata_object) == 1


def _checkrepetitions(stmdata_object):
	"""Infer the number of repeated spectra per tip position."""
	reps = _spectra_per_position(stmdata_object)
	reps = int(reps / (stmdata_object.alternate + 1))
	return reps

def _fix_spectype_from_units(stmdata_object, spectype):
	"""Cross-check the spectype declared by RHK_LineType against the sweep
	axis units, for files written by old RHK Rev versions (RHK_MinorVer < 6).

	Old Rev versions can stamp ramp spectroscopy pages with the wrong
	RHK_LineType (e.g. IV_SPECTRUM for an I(z) ramp). The sweep axis units are
	reliable even in these files: 'V' (bias sweep) means dI/dV, 'm' (tip
	height sweep) means I(z).
	"""
	current = stmdata_object.spymdata['Current']
	if current.attrs['RHK_MinorVer'] >= 6:
		return spectype
	units_spectype = _SPECTYPE_FROM_XUNITS.get(current.attrs['RHK_Xunits'])
	if units_spectype is not None and units_spectype != spectype:
		_logger.warning(
			'%s: file declares %s, but the sweep axis units are %r; '
			'treating the spectra as %r (file written by RHK Rev version < 6).',
			current.attrs['filename'], current.attrs['RHK_LineTypeName'],
			current.attrs['RHK_Xunits'], units_spectype,
		)
		return units_spectype
	return spectype


def _checkdatatype(stmdata_object):
	"""Classify the file into (datatype, spectype).

	datatype: 'image', 'map', 'line' or 'spec', based on the RHK page type and
	the aspect ratio of the spectroscopy tip positions.
	spectype: 'iv' or 'iz' based on the RHK line type, `None` for images.
	For files written by old RHK Rev versions (RHK_MinorVer < 6), the spectype
	is cross-checked against the sweep axis units, since the RHK line type is
	unreliable there (see :func:`_fix_spectype_from_units`).
	"""
	# check if the list of keys in the spym data contain 'Current'
	# If yes, it is not a pure topo image
	l = list(stmdata_object.spymdata.keys())
	if 'Current' in l:
		# it's a single spec, line spec or map
		if stmdata_object.spymdata['Current'].attrs['RHK_PageType'] == 38:
			stmdata_object.datatype = 'spec'
			# determine if it's Iz or dI/dV
			if stmdata_object.spymdata['Current'].attrs['RHK_LineType'] == 7:
				stmdata_object.spectype = 'iv'
			elif stmdata_object.spymdata['Current'].attrs['RHK_LineType'] == 8:
				stmdata_object.spectype = 'iz'
		elif stmdata_object.spymdata['Current'].attrs['RHK_PageType'] == 16:
			# this can be either a line spectrum or a map
			# decide based on the aspect ratio of the spectroscopy tip positions
			xcoo = np.array(stmdata_object.spymdata['Current'].attrs['RHK_SpecDrift_Xcoord'])
			ycoo = np.array(stmdata_object.spymdata['Current'].attrs['RHK_SpecDrift_Ycoord'])
			if _aspect_ratio(xcoo, ycoo) > 10:
				stmdata_object.datatype = 'line'
			else:
				stmdata_object.datatype = 'map'
			# determine if it's Iz or dI/dV
			if stmdata_object.spymdata['Current'].attrs['RHK_LineType'] == 7:
				stmdata_object.spectype = 'iv'
			elif stmdata_object.spymdata['Current'].attrs['RHK_LineType'] == 8:
				stmdata_object.spectype = 'iz'
	else:
		stmdata_object.datatype = 'image'
		stmdata_object.spectype = None

	# old RHK Rev versions can declare the wrong line type; trust the sweep
	# axis units instead for those files
	if stmdata_object.spectype is not None:
		stmdata_object.spectype = _fix_spectype_from_units(stmdata_object, stmdata_object.spectype)

	return stmdata_object.datatype, stmdata_object.spectype

def _aspect_ratio(x, y):
    """Aspect ratio of a point cloud (ratio of covariance eigenvalues), used to
    tell a line of tip positions (large ratio) from a 2D grid (ratio near 1)."""
    xy = np.stack((x, y), axis=0)
    eigvals, eigvecs = np.linalg.eig(np.cov(xy))
    center = xy.mean(axis=-1)
    for val, vec in zip(eigvals, eigvecs.T):
        val *= 2
        xcov,ycov = np.vstack((center + val * vec, center, center - val * vec)).T
    aspect = max(eigvals) / min(eigvals)
    return aspect

def _get_filename(s):
	"""Return the last path component of ``s`` (the bare filename), handling
	both forward slashes and backslashes."""
	# If the string ends with a slash or backslash, remove it first
	s = s.rstrip("/\\")
	# Then, match any character other than backslash or slash until the end of the string
	match = re.search(r'[^/\\]+$', s)
	return match.group(0) if match else None
