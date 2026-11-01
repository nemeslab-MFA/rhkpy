"""rhkdata.summary(), rhkpy.scan() and repr(): what a script or agent reads
instead of looking at a plot.
"""

import json
import shutil

import pytest

import rhkpy
from conftest import TESTDATA_DIR, sm4_fixture_names


def _load(name, **kwargs):
	path = TESTDATA_DIR / name
	if not path.is_file():
		pytest.skip(f'{name} not present in test/ (local-only, proprietary data)')
	return rhkpy.rhkdata(str(path), **kwargs)


@pytest.mark.parametrize('sm4name', sm4_fixture_names())
def test_summary_is_json_ready(sm4name):
	summary = _load(sm4name).summary()
	assert json.loads(json.dumps(summary)) == summary
	assert summary['filename'] == sm4name
	assert isinstance(summary['notes'], list)


def test_image():
	summary = _load('topo_ABC_Graphite-Sample5_9K_2021_08_13_19_11_10_065.sm4').summary()
	assert (summary['datatype'], summary['spectype']) == ('image', None)
	assert summary['spectra'] is None
	assert summary['measurement_date'] == '2021-08-13'
	assert summary['measurement_time'] == '19:08:26'
	image = summary['image']
	assert image['pixels'] == {'x': 128, 'y': 128}
	assert image['size_nm'] == {'x': 75.0, 'y': 75.0}
	assert image['flattened'] is True
	assert image['channels'] == {'topography': 'nm', 'current': 'pA', 'lia': 'pA'}


def test_loadraw_is_reported():
	summary = _load('topo_ABC_Graphite-Sample5_9K_2021_08_13_19_11_10_065.sm4', loadraw = True).summary()
	assert summary['image']['flattened'] is False


def test_map_iv():
	summary = _load('hopg_300k_2020_08_11_16_04_06_999.sm4').summary()
	assert (summary['datatype'], summary['spectype']) == ('map', 'iv')
	assert summary['bias_V'] == pytest.approx(0.4)
	assert summary['setpoint_pA'] == pytest.approx(500)
	spectra = summary['spectra']
	assert spectra['sizes'] == {'bias': 241, 'specpos_y': 4, 'specpos_x': 4, 'repetitions': 1, 'biasscandir': 2}
	assert spectra['sweep'] == {'name': 'bias', 'start': 0.6, 'stop': -0.6, 'points': 241, 'units': 'V'}
	assert spectra['channels'] == {'lia': 'pA', 'current': 'pA'}
	assert spectra['lock_in']['frequency_Hz'] > 0
	assert summary['notes'] == []


def test_line_iv():
	summary = _load('line_9K_ABC6_2020_11_01_12_12_27_213.sm4').summary()
	assert (summary['datatype'], summary['spectype']) == ('line', 'iv')
	assert summary['spectra']['sizes']['dist'] == 64
	assert summary['image']['size_nm'] == {'x': None, 'y': None}


def test_spec_iz():
	summary = _load('Iz_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_15_28_529.sm4').summary()
	assert (summary['datatype'], summary['spectype']) == ('spec', 'iz')
	assert summary['image'] is None
	assert summary['repetitions'] == 10
	spectra = summary['spectra']
	assert spectra['sweep']['name'] == 'z'
	assert spectra['sweep']['units'] == 'nm'
	assert spectra['channels'] == {'current': 'pA'}


def test_notes():
	old = _load('Iz_gold_9K_2019_12_18_13_49_32_752.sm4').summary()
	assert old['rhk_minor_version'] == 5
	assert any('before 6' in note for note in old['notes'])
	single = _load('line_hopg_300k_2020_08_11_16_20_04_378.sm4').summary()
	assert any('not a measured direction' in note for note in single['notes'])
	mixed = _load('line_9K_ABC6_2020_11_01_12_12_27_213.sm4', alternate = False).summary()
	assert any('mixed in the repetitions' in note for note in mixed['notes'])


def test_unsupported_line_type(monkeypatch):
	path = TESTDATA_DIR / 'line_9K_ABC6_2020_11_01_12_12_27_213.sm4'
	if not path.is_file():
		pytest.skip(f'{path.name} not present in test/ (local-only, proprietary data)')
	dataset = rhkpy.core.load_spym(str(path))
	dataset['Current'].attrs.update(RHK_LineType = 9, RHK_LineTypeName = 'RHK_LINE_TEST')
	monkeypatch.setattr(rhkpy.core, 'load_spym', lambda filename: dataset)
	summary = rhkpy.rhkdata(str(path)).summary()
	assert summary['spectra'] is None
	assert summary['image'] is not None
	assert any('RHK_LINE_TEST' in note for note in summary['notes'])
	json.dumps(summary)


def test_repr():
	text = repr(_load('hopg_300k_2020_08_11_16_04_06_999.sm4'))
	assert "datatype='map'" in text
	assert "spectype='iv'" in text
	assert "'bias': 241" in text


def test_scan_continues_past_a_bad_file(tmp_path):
	source = TESTDATA_DIR / 'Iz_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_15_28_529.sm4'
	if not source.is_file():
		pytest.skip(f'{source.name} not present in test/ (local-only, proprietary data)')
	shutil.copy(source, tmp_path / 'good.sm4')
	(tmp_path / 'corrupt.sm4').write_bytes(b'not an sm4 file' * 20)
	(tmp_path / 'notes.txt').write_text('not data')
	(tmp_path / 'sub').mkdir()
	shutil.copy(source, tmp_path / 'sub' / 'nested.SM4')

	result = rhkpy.scan(str(tmp_path))
	assert [entry['filename'] for entry in result] == ['corrupt.sm4', 'good.sm4']
	assert 'ValueError' in result[0]['error']
	assert result[1]['datatype'] == 'spec'
	json.dumps(result)

	recursive = rhkpy.scan(str(tmp_path), recursive = True)
	assert 'nested.SM4' in [entry['filename'] for entry in recursive]


def test_scan_missing_folder():
	with pytest.raises(FileNotFoundError, match = 'nope'):
		rhkpy.scan('nope')
