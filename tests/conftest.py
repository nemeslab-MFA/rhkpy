"""Shared fixtures for the rhkpy characterization test suite.

Test data: the .sm4 files in the (gitignored) ``test/`` directory at the repo
root. The suite is meant to be run locally, where that data is present.
"""

import os
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTDATA_DIR = REPO_ROOT / 'test'
GOLDEN_DIR = pathlib.Path(__file__).resolve().parent / 'golden'

# make sure the local rhkpy (repo checkout) is imported, not an installed copy
sys.path.insert(0, str(REPO_ROOT))


def normalize_path(s):
	"""Replace the machine-specific test data path with a stable placeholder,
	so snapshots are comparable across machines/checkouts."""
	return s.replace(str(TESTDATA_DIR) + os.sep, '<TESTDATA>/').replace(str(TESTDATA_DIR), '<TESTDATA>')


def sm4_fixture_paths():
	if not TESTDATA_DIR.is_dir():
		return []
	return sorted(TESTDATA_DIR.glob('*.sm4'))


def sm4_fixture_names():
	return [p.name for p in sm4_fixture_paths()]


#: Non-default rhkdata() argument combinations to characterize, per fixture.
#: These pin the loadraw / alternate / repetitions code paths, which the
#: default-argument goldens do not exercise.
VARIANT_CASES = [
	# loadraw=True skips the automatic polyflatten of the topography
	('topo_ABC_Graphite-Sample5_9K_2021_08_12_15_11_14_726.sm4', {'loadraw': True}),
	('dI-dV_ABC_Graphite-Sample5_9K_2021_08_24_11_54_33_632.sm4', {'loadraw': True}),
	# alternate=False changes the forward/backward sweep rearrangement
	('dI-dV_ABC_Graphite-Sample5_9K_2021_08_24_11_54_33_632.sm4', {'alternate': False}),
	('Iz_Stripes-9K-HOPG-SPI2-3_2021_09_07_10_15_28_529.sm4', {'alternate': False}),
	('Iz_line_Stripes-9K-HOPG-SPI2-3_2021_09_02_15_15_35_930.sm4', {'alternate': False}),
	# explicit repetitions overrides the inference from tip coordinates
	('dI-dV_ABC_Graphite-Sample5_9K_2021_08_24_11_54_33_632.sm4', {'repetitions': 2}),
	('line_9K_ABC6_2020_11_01_12_12_27_213.sm4', {'repetitions': 1}),
]


def variant_id(sm4name, kwargs):
	"""Stable identifier (and golden file stem) for a variant case."""
	args = ','.join(f'{k}={v}' for k, v in sorted(kwargs.items()))
	return f'{sm4name.rsplit(".", 1)[0]}__{args}'


@pytest.fixture(scope='session')
def loaded_fixtures():
	"""Load every .sm4 fixture once per test session.

	Returns a dict: filename -> ('ok', rhkdata instance) or ('error', exception).
	Load failures are themselves characterized behavior, not test errors.
	"""
	import rhkpy
	result = {}
	for path in sm4_fixture_paths():
		try:
			result[path.name] = ('ok', rhkpy.rhkdata(str(path)))
		except Exception as exc:  # noqa: BLE001 - failures are recorded as behavior
			result[path.name] = ('error', exc)
	return result
