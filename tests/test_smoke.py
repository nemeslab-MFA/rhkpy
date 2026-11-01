"""Smoke and behavior tests: exercise the public entry points end-to-end on
the real fixture data and on small synthetic datasets. The characterization
tests pin exact numerical output; the tests here verify that the public
functions run and BEHAVE as documented (dimensions averaged out, backgrounds
removed, expected plot elements produced, ...).
"""

import shutil

import numpy as np
import pytest
import xarray as xr

from conftest import TESTDATA_DIR, sm4_fixture_names


def _first(loaded_fixtures, datatype, spectype=None):
	"""First successfully loaded fixture with the given datatype/spectype."""
	for name, (status, data) in loaded_fixtures.items():
		if status != 'ok':
			continue
		if data.datatype == datatype and (spectype is None or data.spectype == spectype):
			return data
	pytest.skip(f'no loadable fixture with datatype={datatype} spectype={spectype}')


def _first_with_repetitions(loaded_fixtures, spectype=None):
	"""First loadable spectroscopy fixture with more than one repetition."""
	for name, (status, data) in loaded_fixtures.items():
		if status != 'ok' or data.datatype == 'image':
			continue
		if spectype is not None and data.spectype != spectype:
			continue
		if len(data.spectra.repetitions) > 1:
			return data
	pytest.skip(f'no loadable fixture with repetitions > 1 and spectype={spectype}')


def _one_of_each_type(loaded_fixtures):
	"""One loaded instance per available (datatype, spectype) combination."""
	picked = {}
	for name, (status, data) in loaded_fixtures.items():
		if status == 'ok':
			picked.setdefault((data.datatype, data.spectype), data)
	return list(picked.values())


# ---------------------------------------------------------------- plotting

@pytest.mark.parametrize('sm4name', sm4_fixture_names())
def test_qplot(sm4name, loaded_fixtures):
	status, data = loaded_fixtures[sm4name]
	if status != 'ok':
		pytest.skip(f'{sm4name} does not load (characterized separately)')
	plot = data.qplot()
	assert plot is not None


def test_navigation(loaded_fixtures):
	import rhkpy
	topo = _first(loaded_fixtures, 'image')
	specmap = _first(loaded_fixtures, 'map', 'iv')
	plot = rhkpy.navigation(topo, specmap)
	assert plot is not None


def _expected_navigation_layers(args, plot_spec):
	"""Each image-bearing instance contributes 1 image + 4 bounding-box lines;
	each spectroscopy instance contributes 1 spec-position layer."""
	n_imagebearing = sum(1 for a in args if a.datatype in ('image', 'map'))
	n_spec = sum(1 for a in args if a.datatype in ('map', 'line', 'spec'))
	return 5*n_imagebearing + (n_spec if plot_spec else 0)


def test_navigation_all_types(loaded_fixtures):
	"""navigation() over every available (datatype, spectype) combination,
	checking the overlay has exactly the expected number of layers."""
	import rhkpy
	args = _one_of_each_type(loaded_fixtures)
	if len(args) < 2:
		pytest.skip('not enough loadable fixtures')
	plot = rhkpy.navigation(*args)
	assert len(plot) == _expected_navigation_layers(args, plot_spec = True)


def test_navigation_plot_spec_false(loaded_fixtures):
	"""plot_spec=False leaves only the images and their bounding boxes."""
	import rhkpy
	args = _one_of_each_type(loaded_fixtures)
	if len(args) < 2:
		pytest.skip('not enough loadable fixtures')
	plot = rhkpy.navigation(*args, plot_spec = False)
	assert len(plot) == _expected_navigation_layers(args, plot_spec = False)


def test_navigation_nothing_to_plot(loaded_fixtures, capsys):
	"""No image and no spectrum positions: a message instead of a crash."""
	import rhkpy
	spec = _first(loaded_fixtures, 'spec')
	assert rhkpy.navigation(spec, plot_spec = False) is None
	assert 'Nothing to plot' in capsys.readouterr().out


def test_navigation_spec_positions_only(loaded_fixtures):
	"""A single spectrum with no image data plots just its tip position."""
	import rhkpy
	spec = _first(loaded_fixtures, 'spec')
	plot = rhkpy.navigation(spec)
	assert type(plot).__name__ == 'Scatter'


@pytest.mark.slow
def test_genthumbs(loaded_fixtures, tmp_path):
	"""End-to-end thumbnail generation (starts a headless browser - slow)."""
	import rhkpy
	# two small fixtures that are known to load
	for name in ['Iz_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_15_28_529.sm4',
			'dI-dV_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_23_58_152.sm4']:
		src = TESTDATA_DIR / name
		if src.is_file():
			shutil.copy(src, tmp_path / name)
	copied = list(tmp_path.glob('*.sm4'))
	if not copied:
		pytest.skip('no .sm4 fixtures present in test/ (local-only, proprietary data)')
	rhkpy.genthumbs(str(tmp_path))
	pngs = list(tmp_path.glob('*.png'))
	assert len(pngs) == len(copied)


# ------------------------------------------------------------ rhkdata methods

def test_mrep_averages_repetitions(loaded_fixtures):
	data = _first_with_repetitions(loaded_fixtures)
	averaged = data.mrep()
	# the repetitions dim is averaged out; values equal the manual mean
	assert 'repetitions' not in averaged.spectra.dims
	signal = 'lia' if data.spectype == 'iv' else 'current'
	np.testing.assert_allclose(
		averaged.spectra[signal].values,
		data.spectra[signal].mean(dim = 'repetitions').values)
	# the original instance is untouched
	assert 'repetitions' in data.spectra.dims


def test_msw_averages_scan_direction(loaded_fixtures):
	for spectype, scandir_dim, signal in [('iv', 'biasscandir', 'lia'), ('iz', 'zscandir', 'current')]:
		data = _first(loaded_fixtures, 'spec', spectype)
		averaged = data.msw()
		assert scandir_dim not in averaged.spectra.dims
		np.testing.assert_allclose(
			averaged.spectra[signal].values,
			data.spectra[signal].mean(dim = scandir_dim).values)
		assert scandir_dim in data.spectra.dims


def test_mrep_msw_on_image(loaded_fixtures, capsys):
	image = _first(loaded_fixtures, 'image')
	assert image.mrep() is None
	assert image.msw() is None
	out = capsys.readouterr().out
	assert "doesn't have repetitions" in out
	assert "doesn't have biasscandir or zscandir" in out


def test_coord_to_absolute(loaded_fixtures):
	specmap = _first(loaded_fixtures, 'map')
	absolute = specmap.coord_to_absolute()
	assert absolute is not specmap
	assert absolute.datatype == specmap.datatype
	# the result is marked as absolute and the coordinate notes say so
	assert absolute.image.attrs['comment'] == 'absolute coordinates'
	assert 'absolute coordinates' in absolute.image.coords['x'].attrs['note']
	# the original is untouched
	assert 'comment' not in specmap.image.attrs


def test_polyflatten(loaded_fixtures):
	image = _first(loaded_fixtures, 'image')
	flattened = image.polyflatten()
	assert flattened is not image
	assert 'topography' in flattened.image


def test_polyflatten_removes_background(loaded_fixtures):
	"""Flattening a raw (tilted) topography must remove the per-scanline
	background: the spread of the scanline means collapses."""
	raw_name = next((n for n, (s, d) in loaded_fixtures.items() if s == 'ok' and d.datatype == 'image'), None)
	if raw_name is None:
		pytest.skip('no loadable image fixture')
	import rhkpy
	raw = rhkpy.rhkdata(str(TESTDATA_DIR / raw_name), loadraw = True)
	flattened = raw.polyflatten()
	rowmean_std_raw = np.std(raw.image.topography.sel(scandir = 'forward').values.mean(axis = 1))
	rowmean_std_flat = np.std(flattened.image.topography.sel(scandir = 'forward').values.mean(axis = 1))
	assert rowmean_std_flat < 1e-3 * rowmean_std_raw


def test_print_info(loaded_fixtures, capsys):
	data = _first(loaded_fixtures, 'map')
	data.print_info()
	out = capsys.readouterr().out
	# lists the instance variables and the Dataset contents
	for expected in ['filename', 'datatype', 'image:', 'spectra:', 'topography']:
		assert expected in out


# ------------------------------------------------------------------ analysis

def test_mapsection(loaded_fixtures):
	import rhkpy
	specmap = _first(loaded_fixtures, 'map', 'iv')
	x = specmap.spectra.specpos_x.values
	y = specmap.spectra.specpos_y.values
	start, end = (x.min(), y.min()), (x.max(), y.max())
	section = rhkpy.mapsection(specmap.spectra, start, end)
	# the section runs along a 'dist' coordinate starting at 0, monotonically,
	# ending at the euclidean length of the requested line
	assert 'dist' in section.dims
	dist = section.dist.values
	assert dist[0] == 0
	assert np.all(np.diff(dist) > 0)
	linelength = np.hypot(end[0] - start[0], end[1] - start[1])
	assert abs(dist[-1] - linelength) < linelength * 0.05
	# the signal variables survive the interpolation
	assert 'lia' in section and 'current' in section


def test_bgsubtract_synthetic():
	import rhkpy
	x = np.linspace(-10, 10, 500)
	y = rhkpy.gaussian(x, x0=0, ampl=5, width=0.5) + 0.1 * x + 1
	y_nobg, bg_values, coeff, params, mask, covar = rhkpy.bgsubtract(x, y)
	assert y_nobg.shape == y.shape
	# background (offset + slope) should be mostly removed far from the peak
	assert abs(np.mean(y_nobg[:50])) < 0.5
	# the fitted polynomial recovers the synthetic background: 0.1*x + 1
	np.testing.assert_allclose(coeff, [0.1, 1.0], atol = 0.05)
	# y_nobg + bg reconstructs the input, and the peak region is masked out
	np.testing.assert_allclose(y_nobg + bg_values, y)
	assert not mask[np.argmax(y)]


def test_peakfit_synthetic():
	import rhkpy
	bias = np.linspace(-1, 1, 200)
	da = xr.DataArray(
		rhkpy.gaussian(bias, x0=0.1, ampl=2, width=0.3),
		coords={'bias': bias}, dims=['bias'],
	)
	fit = rhkpy.peakfit(da, stval={'x0': 0.0, 'ampl': 1.5, 'width': 0.2})
	assert 'curvefit_coefficients' in fit
	x0_fitted = float(fit.curvefit_coefficients.sel(param='x0'))
	assert abs(x0_fitted - 0.1) < 0.01


def test_fit_functions_evaluate():
	import rhkpy
	x = np.linspace(-5, 5, 2001)
	# gaussian and lorentz: peak of `ampl` above `offset` at x0, FWHM = width
	for func in (rhkpy.gaussian, rhkpy.lorentz):
		y = func(x, x0 = 1, ampl = 3, width = 0.8, offset = 0.5)
		assert abs(y.max() - 3.5) < 1e-6
		assert abs(x[np.argmax(y)] - 1) < 0.01
		halfmax_width = np.ptp(x[y >= 0.5 + 3/2])
		assert abs(halfmax_width - 0.8) < 0.02
	# double gaussian: two peaks of the requested amplitudes
	y2 = rhkpy.gaussian2(x, x01 = -2, ampl1 = 1, width1 = 0.5, x02 = 2, ampl2 = 2, width2 = 0.5, offset = 0)
	assert abs(y2[x < 0].max() - 1) < 1e-6
	assert abs(y2[x > 0].max() - 2) < 1e-6
	# polynomial_fit recovers known coefficients (numpy.polyval convention)
	coeffs, covar = rhkpy.polynomial_fit(2, x, 2*x**2 + 3*x + 4)
	np.testing.assert_allclose(coeffs, [2, 3, 4], atol = 1e-6)
	assert covar.shape == (3, 3)


# ---------------------------------------------------- image leveling

def test_align_rows():
	import rhkpy
	# rows with different offsets; align must remove the per-row baseline
	img = np.add.outer(np.array([1.0, 5.0, -2.0, 3.0]), np.zeros(50))
	for baseline in ('mean', 'median', 'poly'):
		aligned, bkg = rhkpy.align(img, baseline = baseline)
		np.testing.assert_allclose(aligned + bkg, img)
		np.testing.assert_allclose(aligned, 0, atol = 1e-12)


def test_plane_removes_tilt():
	import rhkpy
	yy, xx = np.mgrid[0:30, 0:40]
	img = 0.1*xx + 0.2*yy + 5.0
	planned, bkg = rhkpy.plane(img)
	# a pure plane must come out flat (constant)
	assert np.ptp(planned) < 1e-9
	np.testing.assert_allclose(planned + bkg, img)


# ---------------------------------------------------- low-level loader

def test_load_rhksm4(loaded_fixtures):
	import rhkpy
	name = next((n for n, (s, d) in loaded_fixtures.items() if s == 'ok'), None)
	if name is None:
		pytest.skip('no loadable fixture')
	pages = rhkpy.load_rhksm4(str(TESTDATA_DIR / name))
	# the page labels are exactly the variables of the high-level Dataset
	ds = rhkpy.load_spym(str(TESTDATA_DIR / name))
	assert {p.label for p in pages._pages} == set(ds.keys())
	for p in pages._pages:
		assert isinstance(p.data, np.ndarray)
		assert 'RHK_PageType' in p.attrs
