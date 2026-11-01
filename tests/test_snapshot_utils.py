"""The snapshot helpers themselves: a change in the data must change the snapshot,
and a snapshot must not depend on the machine.
"""

import os

from conftest import TESTDATA_DIR, normalize_path
from snapshot_utils import MAX_INLINE_SEQ, jsonify

LENGTH = MAX_INLINE_SEQ + 1


def test_long_numeric_strings_differ_from_floats():
	floats = [float(i) for i in range(LENGTH)]
	strings = [str(v) for v in floats]
	assert jsonify(floats) != jsonify(strings)
	assert jsonify(strings) == strings


def test_long_numbers_are_hashed():
	assert list(jsonify([float(i) for i in range(LENGTH)])) == ['__seq__']
	assert list(jsonify(list(range(LENGTH)))) == ['__seq__']
	assert list(jsonify([i % 2 == 0 for i in range(LENGTH)])) == ['__seq__']


def test_inhomogeneous_sequence_stays_inline():
	value = [[1.0, 2.0]] + [[1.0]] * MAX_INLINE_SEQ
	assert jsonify(value) == value


def test_normalize_path_posix():
	assert normalize_path(f'{TESTDATA_DIR}{os.sep}file.sm4') == '<TESTDATA>/file.sm4'


def test_normalize_path_windows_separator(monkeypatch):
	monkeypatch.setattr(os, 'sep', '\\')
	assert normalize_path(f'{TESTDATA_DIR}\\file.sm4') == '<TESTDATA>/file.sm4'
