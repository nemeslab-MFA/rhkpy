"""rhkpy.fixzero and rhkpy.destripe: ports of the spym functions, cross-validated
against the legacy vendored copy (repo root, not packaged).
"""

import numpy as np
import pytest

import rhkpy


def _striped_image():
	"""Noisy flat image with one bright stripe along a scan line."""
	rng = np.random.default_rng(0)
	image = rng.normal(0, 0.01, (64, 64))
	image[20, 5:60] += 1
	return image


@pytest.mark.parametrize('to_mean', [False, True])
def test_fixzero_matches_spym(to_mean):
	from spym.process.level import fixzero
	image = _striped_image()
	np.testing.assert_array_equal(rhkpy.fixzero(image, to_mean = to_mean), fixzero(image, to_mean = to_mean))


def test_fixzero_moves_zero():
	image = _striped_image()
	assert rhkpy.fixzero(image).min() == 0
	assert rhkpy.fixzero(image, to_mean = True).mean() == pytest.approx(0)


@pytest.mark.parametrize('kwargs', [
	{},
	{'sign': 'negative'},
	{'sign': 'both', 'min_length': 10},
	{'rel_threshold': 0.2},
])
def test_destripe_matches_spym(kwargs, monkeypatch):
	from spym.process.filters import destripe
	# the vendored code uses np.NaN, which NumPy 2 removed
	monkeypatch.setattr(np, 'NaN', np.nan, raising = False)
	image = _striped_image()
	filtered, mask = rhkpy.destripe(image, **kwargs)
	spym_filtered, spym_mask = destripe(image, **kwargs)
	np.testing.assert_array_equal(filtered, spym_filtered)
	np.testing.assert_array_equal(mask, spym_mask)


def test_destripe_removes_stripe():
	image = _striped_image()
	filtered, mask = rhkpy.destripe(image)
	assert mask[20, 10:55].all()
	assert not np.delete(mask, 20, axis = 0).any()
	assert filtered[20, 10:55].mean() < 0.5
	# everything outside the mask is untouched
	np.testing.assert_array_equal(filtered[~mask], image[~mask])
