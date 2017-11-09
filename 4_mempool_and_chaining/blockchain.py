#!/usr/bin/env python3
"""
Blockchain component

Will include data structures to allow for the addition or creation of blocks in the chain
"""

import time
import logging
import binascii

from typing import NamedTuple, Iterable
from utils import (
    sha256d, sha256d_hexdigest, internal_order, uint256_from_compact,
    compact_from_uint256
)
from transaction import Transaction, MerkleNode, utxo_set, add_to_utxo
from serialization import register_namedtuple
from chainmanager import ChainManager

logging.basicConfig(
    level=getattr(logging, 'INFO'),
    format='[%(asctime)s][%(module)s:%(lineno)d] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


@register_namedtuple
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
    txns: Iterable[Transaction]

    @property
    def transaction_fees(self):
        """
        returns a dict mapping the transaction id to transaction fee
        """
        fees_dict = {}

        def utxo_from_block(txin):
            tx = [t.txouts for t in self.txns if t.id == txin.outpoint.txid]
            return tx[0][txin.outpoint.txout_idx] if tx else None

        def find_utxo(txin):
            return utxo_set.get(txin.outpoint) or utxo_from_block(txin)

        for txn in self.txns:
            if txn.is_coinbase:
                continue
            spent = sum(find_utxo(i).value for i in txn.txins)
            sent = sum(o.value for o in txn.txouts)
            fees_dict[txn.id] = (spent - sent)

        return fees_dict

    @property
    def fees(self):
        """
        miner's fees are the total amount of coin outputs subtracted from coin inputs.
        Instread of making the transactions carry a fee property function, we have an edge case
        where the utxo is created in the SAME block #DIAGRAM
        """
        return sum(self.transaction_fees.values())

    @property
    def _base_hash(self) -> bytes:
        field_bytes = []
        fields = list(self._fields)

        # we do not need to byte order nonce or txns
        fields.remove('nonce')
        fields.remove('txns')

        for field in fields:
            raw_attr = getattr(self, field)
            cleaned_attr = (isinstance(raw_attr, bytes) and raw_attr or internal_order(raw_attr)) if raw_attr != None else b'\00'*32
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

        # clears the mine_interrupt Event, sets it
        ChainManager.mine_interrupt.clear()

        start = time.time()
        nonce = 0
        target = self.target 

        # if we've explored all possible uint32, we can change either timestamp or transactions (merkle hash)
        template = self._base_hash
        while int(sha256d_hexdigest(template+internal_order(nonce)), 16) >= target:
            nonce += 1
            if nonce % 1000000 == 0 and ChainManager.mine_interrupt.is_set():
                logger.info(f'sanity check: {nonce}')

        new_block = self._replace(nonce=nonce)

        # In case we find the nonce right away
        duration = int(time.time() - start) or 0.001
        khs = (new_block.nonce // duration) // 1000
        logger.info(f'[mining] block found! {duration} s - {khs} KH/s - {new_block.id}')

        return new_block

    @classmethod
    def assemble_and_solve_block(cls, prev_block_hash, pay_coinbase_to_addr, txns=[]):
        """
        Construct a Block by pulling transactions from the mempool, the mine it
        """
        block = cls(
            version=0,
            previous_block_hash=prev_block_hash,
            merkle_tree_hash='',
            timestamp=int(time.time()),
            nbits=504382016,
            nonce=0,
            txns=txns
        )
        logger.info(f'mine {utxo_set}')
        fees = block.fees
        logger.info(f'transaction fee is {fees}')
        coinbase_txn = Transaction.create_coinbase(pay_coinbase_to_addr, 500000 + fees)

        block = block._replace(txns=[coinbase_txn, *block.txns])
        block = block._replace(
            merkle_tree_hash=MerkleNode.generate_root_from_transaction(block.txns).value)

        return block.mine()

