import hashlib
import binascii

from typing import Union
from functools import wraps


def sha256d_hexdigest(data: Union[str, bytes]) -> bytes:
    """
    A double sha256: sha256(sha256(data)) will add additional rounds to the encryption
    """
    if not isinstance(data, bytes):
        data = data.encode()

    round_one = hashlib.sha256(data).digest()
    return hashlib.sha256(round_one).hexdigest()


def sha256d(data: Union[str, bytes]) -> bytes:
    """
    A double sha256: sha256(sha256(data)) will add additional rounds to the encryption
    """
    return binascii.unhexlify(sha256d_hexdigest(data))


def internal_order(data: Union[int, bytes], byte_size=4) -> bytes:
    """
    https://bitcoin.org/en/glossary/internal-byte-order
    converts either a str or int to its hexidecimal little endian representation
    """
    return (data or 0).to_bytes(byte_size, byteorder='little')


def uint256_from_compact(c):
    """
    Convert compact encoding to uint256
    Used for the nbits compact encoding of the target in the block header.

    source: https://github.com/petertodd/python-bitcoinlib/blob/master/bitcoin/core/serialize.py#L318
    https://dev.visucore.com/bitcoin/doxygen/classarith__uint256.html#a06c0f1937edece69b8d33f88e8d35bc8
    https://github.com/bitcoin/bitcoin/blob/master/src/arith_uint256.cpp#L206
    """
    nbytes = (c >> 24) & 0xFF
    if nbytes <= 3:
        v = (c & 0xFFFFFF) >> 8 * (3 - nbytes)
    else:
        v = (c & 0xFFFFFF) << (8 * (nbytes - 3))
    return v


def compact_from_uint256(v):
    """
    Convert uint256 to compact encoding

    source: https://github.com/petertodd/python-bitcoinlib/blob/master/bitcoin/core/serialize.py#L318
    """
    nbytes = (v.bit_length() + 7) >> 3
    compact = 0
    if nbytes <= 3:
        compact = (v & 0xFFFFFF) << 8 * (3 - nbytes)
    else:
        compact = v >> 8 * (nbytes - 3)
        compact = compact & 0xFFFFFF

    # If the sign bit (0x00800000) is set, divide the mantissa by 256 and
    # increase the exponent to get an encoding without it set.
    if compact & 0x00800000:
        compact >>= 8
        nbytes += 1

    return compact | nbytes << 24


class Singleton(type):
    """
    https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def with_lock(lock):
    """
    thread lock decorator
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorate

