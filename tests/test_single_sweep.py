"""Files with one spectrum per tip position: a single sweep direction and no
repetitions. They load with alternate = False and a one-entry scan direction
dimension, labelled like the first sweep of an alternating measurement.
"""

import numpy as np
import pytest
import xarray as xr

import rhkpy
from conftest import TESTDATA_DIR
from rhkpy.plotting.quickplot import _fwbw_lineplot

MAP_FILE = 'dI-dV_9K_ABC6_2020_07_02_08_50_47_967.sm4'
LINE_FILE = 'line_hopg_300k_2020_08_11_16_20_04_378.sm4'
SPEC_FILE = 'dI-dV_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_23_58_152.sm4'


def _fixture_path(name):
	path = TESTDATA_DIR / name
	if not path.is_file():
		pytest.skip(f'{name} not present in test/ (local-only, proprietary data)')
	return str(path)


def test_map(caplog):
	data = rhkpy.rhkdata(_fixture_path(MAP_FILE))
	assert 'one spectrum per tip position' in caplog.text
	assert (data.datatype, data.spectype) == ('map', 'iv')
	assert data.alternate is False
	assert (data.repetitions, data.numberofspectra) == (1, 1)
	spectra = data.spectra
	assert dict(spectra.sizes) == {'bias': 81, 'specpos_y': 32, 'specpos_x': 32, 'repetitions': 1, 'biasscandir': 1}
	assert list(spectra.biasscandir.values) == ['left']

	# same raster as alternating maps: the grid is flipped along both position axes
	raw = data.spymdata.Current.data * 10**12
	current = spectra.current.isel(repetitions = 0, biasscandir = 0).values
	np.testing.assert_allclose(current[:, -1, -1], raw[:, 0])
	np.testing.assert_allclose(current[:, -1, 0], raw[:, 31])
	np.testing.assert_allclose(current[:, -2, -1], raw[:, 32])


def test_line():
	data = rhkpy.rhkdata(_fixture_path(LINE_FILE))
	assert (data.datatype, data.spectype) == ('line', 'iv')
	assert data.alternate is False
	spectra = data.spectra
	assert dict(spectra.sizes) == {'bias': 241, 'dist': 32, 'repetitions': 1, 'biasscandir': 1}
	assert list(spectra.biasscandir.values) == ['left']

	# every spectrum is at its own position along the line
	raw = data.spymdata.Current.data * 10**12
	np.testing.assert_allclose(spectra.current.isel(repetitions = 0, biasscandir = 0).values, raw)
	np.testing.assert_allclose(spectra.dist.values[1] - spectra.dist.values[0], np.hypot(np.diff(spectra.x), np.diff(spectra.y))[0], rtol = 1e-5)


@pytest.mark.parametrize('name', [MAP_FILE, LINE_FILE])
def test_qplot_and_averages(name):
	data = rhkpy.rhkdata(_fixture_path(name))
	assert data.qplot() is not None
	assert 'repetitions' not in data.mrep().spectra.sizes
	assert 'biasscandir' not in data.msw().spectra.sizes


@pytest.mark.parametrize('name', [MAP_FILE, LINE_FILE])
def test_explicit_alternate_false_gives_same_result(name):
	path = _fixture_path(name)
	assert rhkpy.rhkdata(path).spectra.identical(rhkpy.rhkdata(path, alternate = False).spectra)


def test_spec(monkeypatch):
	"""No real file in test/ has this geometry: cut an alternating spectrum down
	to its first sweep."""
	path = _fixture_path(SPEC_FILE)
	dataset = rhkpy.core.load_spym(path)
	single = dataset.isel(Current_y = [0], LIA_Current_y = [0])
	for page in ('Current', 'LIA_Current'):
		for attr in ('RHK_SpecDrift_Xcoord', 'RHK_SpecDrift_Ycoord'):
			single[page].attrs[attr] = dataset[page].attrs[attr][:1]
	monkeypatch.setattr(rhkpy.core, 'load_spym', lambda filename: single)

	data = rhkpy.rhkdata(path)
	assert (data.datatype, data.spectype) == ('spec', 'iv')
	assert data.alternate is False
	assert dict(data.spectra.sizes) == {'bias': 481, 'repetitions': 1, 'biasscandir': 1}
	assert list(data.spectra.biasscandir.values) == ['left']
	assert data.qplot() is not None


def _sweeps_dataarray(nrepetitions, nsweeps):
	return xr.DataArray(
		np.arange(5 * nrepetitions * nsweeps, dtype = float).reshape(5, nrepetitions, nsweeps),
		dims = ('bias', 'repetitions', 'biasscandir'),
		coords = {'bias': np.linspace(0.5, -0.5, 5), 'repetitions': np.arange(nrepetitions)},
		name = 'lia',
	)


@pytest.mark.parametrize('nrepetitions, nelements', [(1, 1), (3, 4)])
def test_lineplot_single_sweep(nrepetitions, nelements):
	"""Only the forward sweep: one curve, or the repetitions and their average."""
	plot = _fwbw_lineplot(_sweeps_dataarray(nrepetitions, 1), 'bias', 'biasscandir', ('left', 'right'))
	assert len(plot.traverse(lambda element: element, [lambda e: type(e).__name__ == 'Curve'])) == nelements


@pytest.mark.parametrize('nrepetitions, nelements', [(1, 2), (3, 8)])
def test_lineplot_both_sweeps(nrepetitions, nelements):
	plot = _fwbw_lineplot(_sweeps_dataarray(nrepetitions, 2), 'bias', 'biasscandir', ('left', 'right'))
	assert len(plot.traverse(lambda element: element, [lambda e: type(e).__name__ == 'Curve'])) == nelements
