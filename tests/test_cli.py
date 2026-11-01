"""The command line interface, through a real subprocess: agents rely on stdout
holding only the results, and on the exit codes.
"""

import json
import shutil
import subprocess
import sys

import pytest

from conftest import REPO_ROOT, TESTDATA_DIR

MAP_FILE = TESTDATA_DIR / 'hopg_300k_2020_08_11_16_04_06_999.sm4'
SPEC_FILE = TESTDATA_DIR / 'Iz_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_15_28_529.sm4'
OLD_FILE = TESTDATA_DIR / 'Iz_gold_9K_2019_12_18_13_49_32_752.sm4'


def _run(*args, cwd = REPO_ROOT):
	code = f'import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); import runpy; sys.argv = ["rhkpy"] + {list(map(str, args))!r}; runpy.run_module("rhkpy", run_name = "__main__")'
	return subprocess.run([sys.executable, "-c", code], cwd = cwd, capture_output = True, text = True)


def _need(path):
	if not path.is_file():
		pytest.skip(f'{path.name} not present in test/ (local-only, proprietary data)')


def test_help_lists_the_commands():
	result = _run('--help')
	assert result.returncode == 0
	for command in ('info', 'scan', 'preview', 'guide'):
		assert command in result.stdout


def test_no_command_is_an_error():
	assert _run().returncode == 2


def test_guide():
	result = _run('guide')
	assert result.returncode == 0
	assert result.stdout.startswith('# Using rhkpy')


def test_info_json():
	_need(MAP_FILE)
	result = _run('info', MAP_FILE, '--json')
	assert result.returncode == 0
	summary = json.loads(result.stdout)
	assert (summary['datatype'], summary['spectype']) == ('map', 'iv')


def test_info_text():
	_need(MAP_FILE)
	result = _run('info', MAP_FILE)
	assert result.returncode == 0
	assert 'type: map, iv' in result.stdout
	assert 'sweep: bias 0.6 to -0.6 V, 241 points' in result.stdout


def test_warnings_stay_out_of_json():
	_need(OLD_FILE)
	result = _run('info', OLD_FILE, '--json')
	assert result.returncode == 0
	assert 'not tested for RHK Rev version' in result.stderr
	assert json.loads(result.stdout)['rhk_minor_version'] == 5


def test_missing_file():
	result = _run('info', 'nope.sm4', '--json')
	assert result.returncode == 1
	assert result.stdout == ''
	assert 'FileNotFoundError' in result.stderr


def test_corrupt_file_keeps_stdout_clean(tmp_path):
	path = tmp_path / 'corrupt.sm4'
	path.write_bytes(b'not an sm4 file' * 20)
	result = _run('info', path, '--json')
	assert result.returncode == 1
	assert result.stdout == ''
	assert 'does not appear to be' in result.stderr


def test_scan_reports_bad_files_and_exits_zero(tmp_path):
	_need(SPEC_FILE)
	shutil.copy(SPEC_FILE, tmp_path / 'good.sm4')
	(tmp_path / 'corrupt.sm4').write_bytes(b'not an sm4 file' * 20)
	result = _run('scan', tmp_path, '--json')
	assert result.returncode == 0
	corrupt, good = json.loads(result.stdout)
	assert 'error' in corrupt
	assert good['datatype'] == 'spec'
	text = _run('scan', tmp_path)
	assert text.returncode == 0
	assert 'good.sm4: spec, iz' in text.stdout
	assert 'corrupt.sm4: ValueError' in text.stdout


def test_scan_missing_folder():
	assert _run('scan', 'nope').returncode == 1


def test_preview_output_file(tmp_path):
	_need(MAP_FILE)
	output = tmp_path / 'out.png'
	result = _run('preview', MAP_FILE, '-o', output, '--at', '0.1', '--dpi', '40')
	assert result.returncode == 0
	assert result.stdout.strip() == str(output)
	assert output.read_bytes().startswith(b'\x89PNG')


def test_preview_default_name_is_in_the_current_folder(tmp_path):
	_need(MAP_FILE)
	result = _run('preview', MAP_FILE, '--dpi', '40', cwd = tmp_path)
	assert result.returncode == 0
	assert (tmp_path / (MAP_FILE.stem + '.png')).is_file()


def test_preview_bad_output_folder(tmp_path):
	_need(MAP_FILE)
	assert _run('preview', MAP_FILE, '-o', tmp_path / 'no' / 'out.png').returncode == 1
