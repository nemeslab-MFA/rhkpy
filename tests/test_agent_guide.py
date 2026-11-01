"""The guide shipped for scripts and agents has to stay true: its Python examples
run against real files, and every name it mentions exists.
"""

import re
import shutil

import numpy as np
import pytest

import rhkpy
from conftest import TESTDATA_DIR

GUIDE = rhkpy.agent_guide()
PYTHON_BLOCKS = re.findall(r'```python\n(.*?)```', GUIDE, flags = re.DOTALL)
EXAMPLE_FILES = {
	'map.sm4': 'dI-dV_ABC_Graphite-Sample5_9K_2021_08_24_11_54_33_632.sm4',
	'spec.sm4': 'dI-dV_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_23_58_152.sm4',
	'image.sm4': 'topo_ABC_Graphite-Sample5_9K_2021_08_13_19_11_10_065.sm4',
}


def test_guide_has_examples():
	assert len(PYTHON_BLOCKS) >= 4


@pytest.mark.parametrize('index', range(len(PYTHON_BLOCKS)))
def test_python_examples_run(index, tmp_path, monkeypatch):
	for example, fixture in EXAMPLE_FILES.items():
		if not (TESTDATA_DIR / fixture).is_file():
			pytest.skip(f'{fixture} not present in test/ (local-only, proprietary data)')
		shutil.copy(TESTDATA_DIR / fixture, tmp_path / example)
	monkeypatch.chdir(tmp_path)
	exec(PYTHON_BLOCKS[index], {})


def test_mentioned_functions_exist():
	names = set(re.findall(r'rhkpy\.([a-z_]+)', GUIDE)) - {'py'}
	assert names
	for name in names:
		assert hasattr(rhkpy, name), name


def test_mentioned_methods_exist():
	for name in ('summary', 'preview', 'qplot', 'mrep', 'msw', 'coord_to_absolute'):
		assert f'{name}(' in GUIDE
		assert hasattr(rhkpy.rhkdata, name)


def test_help_points_to_the_guide():
	assert 'rhkpy.agent_guide()' in rhkpy.__doc__


@pytest.mark.parametrize('fixture', [
	'dI-dV_ABC_Graphite-Sample5_9K_2021_08_24_11_54_33_632.sm4',
	'Iz_map_Stripes-9K-HOPG-SPI2-3_2021_09_08_11_21_03_743.sm4',
])
def test_map_tip_position_flip(fixture):
	"""The relation the guide states: the spectrum at [i, j] was measured at
	[-1 - i, -1 - j] of x and y. Checked against the raw columns and coordinates."""
	if not (TESTDATA_DIR / fixture).is_file():
		pytest.skip(f'{fixture} not present in test/ (local-only, proprietary data)')
	data = rhkpy.rhkdata(str(TESTDATA_DIR / fixture))
	spectra = data.spectra
	scandir = 'biasscandir' if 'biasscandir' in spectra.dims else 'zscandir'
	sweep = 'bias' if scandir == 'biasscandir' else 'z'
	current = spectra.current.isel(repetitions = 0).isel({scandir: 0}).transpose(sweep, 'specpos_y', 'specpos_x').values
	x = spectra.x.transpose('specpos_y', 'specpos_x').values
	y = spectra.y.transpose('specpos_y', 'specpos_x').values
	raw = data.spymdata.Current
	raw_x = np.array(raw.attrs['RHK_SpecDrift_Xcoord']) * 10**9
	raw_y = np.array(raw.attrs['RHK_SpecDrift_Ycoord']) * 10**9
	# the same spectrum, found in the raw columns, tells where it was measured
	i, j = 3, 5
	matches = [k for k in range(raw.data.shape[1]) if np.allclose(raw.data[:, k] * 10**12, current[:, i, j])]
	assert len(matches) == 1
	np.testing.assert_allclose(x[-1 - i, -1 - j], raw_x[matches[0]], rtol = 1e-5)
	np.testing.assert_allclose(y[-1 - i, -1 - j], raw_y[matches[0]], rtol = 1e-5)
