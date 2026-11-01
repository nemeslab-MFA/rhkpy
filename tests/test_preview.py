"""rhkdata.preview(): a static picture, with no browser or display. The plotted
arrays are checked against the data selected by dimension name, so that a
picture can't silently come out flipped.
"""

import numpy as np
import pytest

import rhkpy
from conftest import TESTDATA_DIR, sm4_fixture_names

PNG_SIGNATURE = b'\x89PNG'
IMAGE_FILE = 'topo_ABC_Graphite-Sample5_9K_2021_08_13_19_11_10_065.sm4'
MAP_IV_FILE = 'hopg_300k_2020_08_11_16_04_06_999.sm4'
MAP_IZ_FILE = 'Iz_map_Stripes-9K-HOPG-SPI2-3_2021_09_08_11_21_03_743.sm4'
LINE_FILE = 'line_9K_ABC6_2020_11_01_12_12_27_213.sm4'
SPEC_FILE = 'dI-dV_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_23_58_152.sm4'
SINGLE_SWEEP_MAP_FILE = 'dI-dV_9K_ABC6_2020_07_02_08_50_47_967.sm4'


def _load(name):
	path = TESTDATA_DIR / name
	if not path.is_file():
		pytest.skip(f'{name} not present in test/ (local-only, proprietary data)')
	return rhkpy.rhkdata(str(path))


def _plotted(figure):
	"""The plotted arrays and extents of a figure's density plots."""
	return [(np.asarray(ax.images[0].get_array()), ax.images[0].get_extent()) for ax in figure.axes if ax.images]


@pytest.mark.parametrize('sm4name', sm4_fixture_names())
def test_preview_writes_png(sm4name, tmp_path):
	path = tmp_path / 'out.png'
	_load(sm4name).preview(str(path), dpi = 40)
	assert path.read_bytes().startswith(PNG_SIGNATURE)


def test_no_path_saves_nothing(tmp_path, monkeypatch):
	monkeypatch.chdir(tmp_path)
	assert _load(SPEC_FILE).preview() is not None
	assert list(tmp_path.iterdir()) == []


def test_image_orientation():
	data = _load(IMAGE_FILE)
	(topography, extent), (lia, _) = _plotted(data.preview())
	backward = data.image.sel(scandir = 'backward')
	np.testing.assert_array_equal(topography, backward.topography.transpose('y', 'x').values)
	np.testing.assert_array_equal(lia, backward.lia.transpose('y', 'x').values)
	# origin at the first pixel, half a pixel beyond its center
	assert extent[0] < float(backward.x[0]) < extent[1]
	assert extent[2] < float(backward.y[0]) < extent[3]


@pytest.mark.parametrize('name, sweep_dim, scandir_dim, signal, value', [
	(MAP_IV_FILE, 'bias', 'biasscandir', 'lia', -0.3),
	# the (x, y) ordered dims of I(z) maps must give the same orientation
	(MAP_IZ_FILE, 'z', 'zscandir', 'current', 0.1),
])
def test_map_orientation(name, sweep_dim, scandir_dim, signal, value):
	data = _load(name)
	_, (plotted, extent) = _plotted(data.preview(at = value))
	mean = data.spectra[signal].mean(dim = ['repetitions', scandir_dim]).sel({sweep_dim: value}, method = 'nearest')
	np.testing.assert_array_equal(plotted, mean.transpose('specpos_y', 'specpos_x').values)
	assert extent[0] < extent[1]
	assert extent[2] < extent[3]


def test_map_at_default_is_middle_of_sweep():
	data = _load(MAP_IV_FILE)
	figure = data.preview()
	average = [ax for ax in figure.axes if ax.get_title() == 'average over the map'][0]
	marker = [line for line in average.get_lines() if line.get_label() == 'mapped value'][0]
	assert marker.get_xdata()[0] == data.spectra.bias.values[data.spectra.bias.size // 2]


def test_single_sweep_map():
	data = _load(SINGLE_SWEEP_MAP_FILE)
	_, (plotted, _) = _plotted(data.preview())
	assert plotted.shape == (32, 32)


def test_line_axes_ascend():
	"""This file's bias runs from high to low, and the plot must still ascend."""
	data = _load(LINE_FILE)
	assert data.spectra.bias.values[0] > data.spectra.bias.values[-1]
	(plotted, extent), = _plotted(data.preview())
	assert extent[0] < extent[1]
	mean = data.spectra.lia.mean(dim = ['repetitions', 'biasscandir']).transpose('dist', 'bias')
	np.testing.assert_array_equal(plotted, mean.sortby('bias').values)


def test_spec_shows_both_channels_and_directions():
	figure = _load(SPEC_FILE).preview()
	assert [ax.get_title() for ax in figure.axes] == ['dI/dV', 'current']
	assert [text.get_text() for text in figure.axes[0].get_legend().get_texts()] == ['left, average', 'right, average']


def test_title_has_conditions():
	title = _load(MAP_IV_FILE).preview()._suptitle.get_text()
	assert MAP_IV_FILE in title
	assert 'bias 0.4 V' in title
	assert 'setpoint 500 pA' in title


def test_unsupported_line_type_shows_the_image(monkeypatch, tmp_path):
	path = TESTDATA_DIR / LINE_FILE
	if not path.is_file():
		pytest.skip(f'{LINE_FILE} not present in test/ (local-only, proprietary data)')
	dataset = rhkpy.core.load_spym(str(path))
	dataset['Current'].attrs.update(RHK_LineType = 9, RHK_LineTypeName = 'RHK_LINE_TEST')
	monkeypatch.setattr(rhkpy.core, 'load_spym', lambda filename: dataset)
	output = tmp_path / 'out.png'
	rhkpy.rhkdata(str(path)).preview(str(output), dpi = 40)
	assert output.read_bytes().startswith(PNG_SIGNATURE)


def test_nothing_to_plot_raises(monkeypatch):
	path = TESTDATA_DIR / SPEC_FILE
	if not path.is_file():
		pytest.skip(f'{SPEC_FILE} not present in test/ (local-only, proprietary data)')
	dataset = rhkpy.core.load_spym(str(path))
	dataset['Current'].attrs.update(RHK_LineType = 9, RHK_LineTypeName = 'RHK_LINE_TEST')
	monkeypatch.setattr(rhkpy.core, 'load_spym', lambda filename: dataset)
	with pytest.raises(ValueError, match = 'neither an image nor spectra'):
		rhkpy.rhkdata(str(path)).preview()
