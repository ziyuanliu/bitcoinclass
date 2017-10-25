import pytest

from utils import internal_order


def test_internal_order():
	# test value for conversion correctness
	assert internal_order(3) == b'\x03\x00\x00\x00'
	assert int.from_bytes(b'\x03\x00\x00\x00', 'little') == 3

	# test byte size
	assert len(internal_order(3)) == 4
