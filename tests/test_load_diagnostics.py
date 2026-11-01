"""Load-time diagnostics: rhkpy's warnings reach the user, and files with
spectroscopy types that aren't supported still load.
"""

import subprocess
import sys

import numpy as np
import pytest

import rhkpy
from conftest import REPO_ROOT, TESTDATA_DIR

LINE_FILE = 'line_9K_ABC6_2020_11_01_12_12_27_213.sm4'
OLD_REV_FILE = 'Iz_gold_9K_2019_12_18_13_49_32_752.sm4'
SINGLE_SWEEP_FILE = 'line_hopg_300k_2020_08_11_16_20_04_378.sm4'


def _fixture_path(name):
	path = TESTDATA_DIR / name
	if not path.is_file():
		pytest.skip(f'{name} not present in test/ (local-only, proprietary data)')
	return str(path)


def _stderr_of(code):
	"""stderr of `code` in a new interpreter: pytest's own logging handlers keep
	the root logger configuration from applying in this process."""
	result = subprocess.run([sys.executable, '-c', code], cwd = REPO_ROOT, capture_output = True, text = True)
	assert result.returncode == 0, result.stderr
	return result.stderr


def test_warnings_reach_stderr():
	stderr = _stderr_of("import logging, rhkpy; logging.getLogger('rhkpy').warning('probe message')")
	assert 'probe message' in stderr


def test_load_warnings_reach_stderr():
	old_rev, single_sweep = _fixture_path(OLD_REV_FILE), _fixture_path(SINGLE_SWEEP_FILE)
	stderr = _stderr_of(f'import rhkpy; rhkpy.rhkdata({old_rev!r}); rhkpy.rhkdata({single_sweep!r})')
	assert 'not tested for RHK Rev version < 6' in stderr
	assert 'one spectrum per tip position' in stderr


def test_bokeh_warnings_stay_suppressed():
	stderr = _stderr_of("import logging, rhkpy; logging.getLogger('bokeh').warning('probe message')")
	assert 'probe message' not in stderr


@pytest.mark.parametrize('kwargs, argument', [
	({'alternate': 'yes'}, 'alternate'),
	({'alternate': 1}, 'alternate'),
	({'alternate': None}, 'alternate'),
	({'repetitions': -2}, 'repetitions'),
	({'repetitions': 2.5}, 'repetitions'),
	({'repetitions': '2'}, 'repetitions'),
	({'repetitions': True}, 'repetitions'),
])
def test_invalid_arguments_raise(kwargs, argument):
	"""Raised before the file is read, so no data is needed."""
	with pytest.raises(ValueError, match = argument):
		rhkpy.rhkdata('not_read.sm4', **kwargs)


def test_numpy_arguments_are_valid():
	path = _fixture_path(LINE_FILE)
	data = rhkpy.rhkdata(path, repetitions = np.int64(1), alternate = np.bool_(True))
	assert data.spectra.identical(rhkpy.rhkdata(path, repetitions = 1, alternate = True).spectra)


@pytest.mark.parametrize('name, datatype, has_image', [
	('hopg_300k_2020_08_11_16_04_06_999.sm4', 'map', True),
	(LINE_FILE, 'line', True),
	('dI-dV_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_23_58_152.sm4', 'spec', False),
	(OLD_REV_FILE, 'spec', False),
])
def test_unsupported_line_type_loads_without_spectra(name, datatype, has_image, monkeypatch, caplog):
	path = _fixture_path(name)
	dataset = rhkpy.core.load_spym(path)
	dataset['Current'].attrs.update(RHK_LineType = 9, RHK_LineTypeName = 'RHK_LINE_TEST')
	monkeypatch.setattr(rhkpy.core, 'load_spym', lambda filename: dataset)

	data = rhkpy.rhkdata(path)
	assert (data.datatype, data.spectype) == (datatype, None)
	assert not hasattr(data, 'spectra')
	assert hasattr(data, 'image') == has_image
	assert 'RHK_LINE_TEST are not supported' in caplog.text
	with pytest.raises(ValueError, match = 'qplot does not support'):
		data.qplot()
