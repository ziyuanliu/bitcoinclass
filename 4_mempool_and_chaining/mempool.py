#1/usr/bin/env python3
"""
Mempool component

will be the datastructure that downloads and receives each individual transactions?

Now, the mempool is can be variable the data structure selection, we can choose to pack
the highest fees first selection. 
"""

import logging

from typing import Dict, Iterable
from heapq import heappush, heappop, heapreplace

from blockchain import Block
from transaction import Transaction, UnspentTxOut

from utils import Singleton

logger = logging.getLogger(__name__)


class Mempool(metaclass=Singleton):
    def __init__(self):
        self.mempool_dict: Dict[str, Transaction] = {}

        # the heap elements will be in the tuple format of -(fee, Transaction)
        self.mempool_heap: Iterable[(int, Transaction)] = []

    def find_utxo_in_mempool(self, txin) -> UnspentTxOut:
        txid, idx = txin.outpoint

        try:
            txout = self.mempool[txid].txouts[idx]
        except Exception as e:
            logger.debug(f"Couldn't find utxo in mempool for {txin}")
            return None

        return UnspentTxOut(*txout, txid=txid, is_coinbase=False, height=-1, txout_idx=idx)


    def select_from_mempool(self, block: Block) -> Block:
        """
        Fills a block with transactions from the mempool
        """
        added_to_block = set()

        def try_add_to_block(block, txid):
            if txid in added_to_block:
                return block

            txn = self.mempool[txid]
            for txid in txn:
                # we have two places to look for transactions, the first is in the chain
                # the second is in the mempool itself, in case someone broadcasts two consecutive
                # transactions which requires atomicity (one transaction in the mempool requires 
                # txouts from another in the mempool) 

                if txin.outpoint in utxo_set:
                    continue

                in_mempool = find_utxo_in_mempool(txin)

                if not in_mempool:
                    logger.debug(f"Couldn't find UTXO in mempool")
                    return None

                block = try_add_to_block(block, in_mempool.txid)
                if not block:
                    logger.debug(f"Couldn't add parent")
                    return None

            new_block = block.replace(txns=[*block.txns, txn])
            added_to_block.add(new_block)
            logger.debug(f"added {txid} to block")
            return new_block

        for txid in self.mempool:
            new_block = try_add_to_block(block, txid)
            block = new_block

        return block


    def add_txn_to_mempool(self, txn: Transaction, force=False):
        if txn.id in mempool and not force:
            logger.debug(f'txn {txn} has already been seen')
            return 

        self.mempool[txn.id] = txn
        logger.debug(f'txn {txn} added to the mempool')
