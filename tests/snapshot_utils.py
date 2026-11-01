"""Utilities to build JSON-safe structural snapshots ("golden masters") of
rhkpy objects and of the public API surface.

Used by ``make_golden.py`` to create the reference snapshots (committed under
``tests/golden/``) and by the characterization tests to compare the current
behavior of the code against those references. Any refactoring that changes
the public API, the structure of the loaded data, or the numerical values of
the data will show up as a snapshot mismatch.
"""

import hashlib
import inspect
import re
import types

import numpy as np
import xarray as xr

# sequences longer than this are stored as length + content hash instead of inline
MAX_INLINE_SEQ = 16


def _hash_bytes(b):
	return hashlib.sha256(b).hexdigest()


def _hash_array(arr):
	a = np.ascontiguousarray(arr)
	return _hash_bytes(a.tobytes())


def _strip_addresses(s):
	"""Remove memory addresses from reprs, e.g. '<function gaussian at 0x1e0>'."""
	return re.sub(r' at 0x[0-9a-fA-F]+', '', s)


def jsonify(value, norm=None):
	"""Convert ``value`` to a JSON-serializable, deterministic representation.

	``norm`` is an optional callable applied to every string (used to replace
	machine-specific paths with a placeholder).
	"""
	if norm is None:
		norm = lambda s: s
	# numpy scalars -> python scalars
	if isinstance(value, np.generic):
		value = value.item()
	if value is None or isinstance(value, (bool, int)):
		return value
	if isinstance(value, float):
		if np.isfinite(value):
			return value
		return {'__nonfinite__': repr(value)}
	if isinstance(value, str):
		return norm(value)
	if isinstance(value, bytes):
		return {'__bytes__': {'len': len(value), 'sha256': _hash_bytes(value)}}
	if isinstance(value, np.ndarray):
		if value.size > MAX_INLINE_SEQ:
			return {'__array__': {
				'shape': list(value.shape),
				'dtype': str(value.dtype),
				'sha256': _hash_array(value),
			}}
		return [jsonify(v, norm) for v in value.tolist()]
	if isinstance(value, (list, tuple)):
		if len(value) > MAX_INLINE_SEQ:
			try:
				# only real numbers: np.asarray(value, dtype=float) would also
				# convert numeric strings, hiding a change from float to str
				if np.asarray(value).dtype.kind in 'biuf':
					arr = np.asarray(value, dtype=float)
					return {'__seq__': {'len': len(value), 'sha256': _hash_array(arr)}}
			except (ValueError, TypeError):
				pass
		return [jsonify(v, norm) for v in value]
	if isinstance(value, dict):
		return {str(k): jsonify(v, norm) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
	# fallback: record only the type name (reprs may contain addresses)
	return {'__type__': type(value).__name__}


def dataarray_snapshot(da, norm=None):
	"""Structural + numerical snapshot of an xarray DataArray."""
	snap = {
		'dims': list(da.dims),
		'shape': list(da.shape),
		'dtype': str(da.dtype),
		'sha256': _hash_array(da.values),
		'attrs': jsonify(dict(da.attrs), norm),
	}
	# summary statistics for numeric data, useful when debugging a hash mismatch
	if np.issubdtype(da.dtype, np.number) and da.size > 0:
		vals = da.values.astype(float)
		with np.errstate(all='ignore'):
			import warnings
			with warnings.catch_warnings():
				warnings.simplefilter('ignore')
				snap['stats'] = {
					'nanmin': jsonify(float(np.nanmin(vals))),
					'nanmax': jsonify(float(np.nanmax(vals))),
					'nanmean': jsonify(float(np.nanmean(vals))),
				}
	return snap


def dataset_snapshot(ds, norm=None):
	"""Structural + numerical snapshot of an xarray Dataset."""
	return {
		'dims': {str(k): int(v) for k, v in sorted(ds.sizes.items())},
		'coords': {str(k): dataarray_snapshot(ds.coords[k], norm) for k in sorted(ds.coords)},
		'data_vars': {str(k): dataarray_snapshot(ds[k], norm) for k in sorted(ds.data_vars)},
		'attrs': jsonify(dict(ds.attrs), norm),
	}


def rhkdata_snapshot(obj, norm=None):
	"""Snapshot of an rhkdata instance: all instance attributes, with xarray
	Datasets expanded to full structural snapshots."""
	snap = {}
	for name, value in sorted(vars(obj).items()):
		if isinstance(value, xr.Dataset):
			snap[name] = {'__dataset__': dataset_snapshot(value, norm)}
		elif isinstance(value, xr.DataArray):
			snap[name] = {'__dataarray__': dataarray_snapshot(value, norm)}
		else:
			snap[name] = jsonify(value, norm)
	return snap


def exception_snapshot(exc, norm=None):
	if norm is None:
		norm = lambda s: s
	return {'exception': type(exc).__name__, 'message': norm(str(exc))}


def _describe_callable(obj):
	try:
		sig = _strip_addresses(str(inspect.signature(obj)))
	except (ValueError, TypeError):
		sig = None
	return sig


def api_surface_snapshot(module):
	"""Snapshot of the public API surface of a module: every public name with
	its kind and, for callables defined in the module's own package, their
	signatures (for classes: all public methods plus __init__).

	Objects that rhkpy merely re-exports from third-party packages (e.g. the
	holoviews ``dim``/``opts`` classes, scipy's ``find_peaks``) are pinned by
	name and origin module only - their signatures belong to the dependency
	and vary with its version, which would make the snapshot depend on the
	environment instead of on rhkpy's API.
	"""
	package = module.__name__.split('.')[0]

	def _origin(obj):
		# top-level package only: private module paths inside dependencies
		# (e.g. scipy.optimize._minpack_py) move between versions
		return (getattr(obj, '__module__', None) or '').split('.')[0]

	def _is_own(obj):
		return _origin(obj) == package

	surface = {}
	for name in sorted(dir(module)):
		if name.startswith('_'):
			continue
		obj = getattr(module, name)
		if inspect.isclass(obj):
			if _is_own(obj):
				methods = {}
				for mname, member in sorted(vars(obj).items()):
					if mname.startswith('_') and mname != '__init__':
						continue
					if callable(member):
						methods[mname] = _describe_callable(member)
				surface[name] = {'kind': 'class', 'methods': methods}
			else:
				surface[name] = {'kind': 'class', 'origin': _origin(obj)}
		elif inspect.isroutine(obj):
			if _is_own(obj):
				surface[name] = {'kind': 'function', 'signature': _describe_callable(obj)}
			else:
				surface[name] = {'kind': 'function', 'origin': _origin(obj)}
		elif isinstance(obj, types.ModuleType):
			surface[name] = {'kind': 'module', 'name': obj.__name__}
		else:
			surface[name] = {'kind': type(obj).__name__}
	return surface


def diff_snapshots(expected, current, path='', out=None, limit=50):
	"""Recursively compare two snapshot structures. Returns a list of
	human-readable difference descriptions (empty list = identical)."""
	if out is None:
		out = []
	if len(out) >= limit:
		return out
	if type(expected) is not type(current):
		out.append(f'{path or "<root>"}: type changed {type(expected).__name__} -> {type(current).__name__} '
			f'(golden={expected!r}, current={current!r})')
		return out
	if isinstance(expected, dict):
		for key in sorted(set(expected) | set(current)):
			p = f'{path}.{key}' if path else key
			if key not in expected:
				out.append(f'{p}: ADDED in current: {current[key]!r}')
			elif key not in current:
				out.append(f'{p}: MISSING in current (golden={expected[key]!r})')
			else:
				diff_snapshots(expected[key], current[key], p, out, limit)
			if len(out) >= limit:
				return out
	elif isinstance(expected, list):
		if len(expected) != len(current):
			out.append(f'{path}: list length {len(expected)} -> {len(current)}')
			return out
		for i, (e, c) in enumerate(zip(expected, current)):
			diff_snapshots(e, c, f'{path}[{i}]', out, limit)
			if len(out) >= limit:
				return out
	else:
		if expected != current:
			out.append(f'{path}: golden={expected!r} current={current!r}')
	return out
