"""The guide shipped for scripts and agents has to stay true: its Python examples
run against real files, and every name it mentions exists.
"""

import re
import shutil

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
