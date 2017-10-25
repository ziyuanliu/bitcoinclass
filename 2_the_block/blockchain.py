#!/usr/bin/env python3
"""
Blockchain component

Will include data structures to allow for the addition or creation of blocks in the chain
"""

import time
import logging
import binascii

from typing import NamedTuple, Iterable
from utils import sha256d, sha256d_hexdigest, internal_order, uint256_from_compact, compact_from_uint256

logging.basicConfig(
    level=getattr(logging, 'INFO'),
    format='[%(asctime)s][%(module)s:%(lineno)d] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class Block(NamedTuple):
	"""
	https://bitcoin.org/en/developer-reference#block-headers
	https://bitcoin.org/en/glossary/block
	https://docs.python.org/3.6/library/collections.html#collections.namedtuple
	"""

	version: int
	previous_block_hash: bytes
	merkle_tree_hash: bytes
	timestamp: int
	nbits: int
	nonce: int

	@property
	def _base_hash(self) -> bytes:
		field_bytes = []
		fields = list(self._fields)
		fields.remove('nonce')

		for field in fields:
			raw_attr = getattr(self, field)
			cleaned_attr = internal_order(raw_attr) if raw_attr != None else b'\00'*32
			field_bytes.append(cleaned_attr)
		return b''.join(field_bytes)

	@property
	def header_hash(self) -> bytes:
		return self._base_hash+internal_order(self.nonce)

	@property
	def id(self):
		return sha256d(self.header_hash)

	@property
	def target(self):
		return uint256_from_compact(self.nbits)

	def mine(self):
		"""
		Since NamedTuples are immutable, we need to return a new block as _replace really returns a new version of 
		the object
		"""

		start = time.time()
		nonce = 0
		target = self.target 

		# if we've explored all possible uint32, we can change either timestamp or transactions (merkle hash)
		template = self._base_hash
		while int(sha256d_hexdigest(template+internal_order(nonce)), 16) >= target:
			nonce += 1
			if nonce % 1000000 == 0:
				logger.info(f'sanity check: {nonce}')

		new_block = self._replace(nonce=nonce)

		# In case we find the nonce right away
		duration = int(time.time() - start) or 0.001
		khs = (new_block.nonce // duration) // 1000
		logger.info(f'[mining] block found! {duration} s - {khs} KH/s - {new_block.id}')

		return new_block


if __name__ == '__main__':
	genesis_block = Block(**{
		'version': 0,
		'previous_block_hash': None,
		'merkle_tree_hash': None,
		'timestamp': int(time.time()),
		'nbits': 504382016,
		'nonce': 0
	})
	genesis_block = genesis_block.mine()
	
	logger.info(f'Genesis block mined: Nonce: {genesis_block.nonce} Block Hash: {genesis_block.id}')

	second_block = Block(
		**{
			'version': 0,
			'previous_block_hash': genesis_block.id.encode(),
			'merkle_tree_hash': None,
			'timestamp': int(time.time()),
			'nbits': 504382016,
			'nonce': 0
		}
	)
	second_block = second_block.mine()

	logger.info(f'Second block mined: Nonce: {second_block.nonce} Block Hash: {genesis_block.id}')

