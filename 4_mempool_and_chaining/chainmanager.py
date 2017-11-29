import logging 

from typing import Iterable, Union
from threading import RLock, Event
from utils import Singleton, with_lock
from transaction import UTXOManager
from blockchain import Block
from mempool import Mempool

logger = logging.getLogger(__name__)


class ChainManager(metaclass=Singleton):
    """
    Responsible for chain managing, every aspect of the chain will be defined here
    """
    
    chain_lock = RLock()
    mine_interrupt = Event()
    ACTIVE_CHAIN_IDX = 0

    def __init__(self):
        self.active_chain: Iterable[Block] = []
        self.side_branches: Iterable[Iterable[Block]] = []
        self.orphan_blocks: Iterable[Block] = []


    def find_by_id(self, hash_id, chain=None):
        chain = chain or self.active_chain
        result = [block for block in chain[::-1] if block.id == hash_id]
        return result[0] if result else None

    @with_lock(chain_lock)
    def add_block_to_chain(self, block: Block, doing_reorg=False) -> Union[None, Block]:
        """
        Accept a block and return the chain index we append it to.
        """

        search_chain = self.active_chain if doing_reorg else None
        utxo_manager = UTXOManager()

        if self.locate_block(block.id, chain=search_chain)[0]:
            logger.debug(f'ignore block already seen: {block.id}')
            return None

        chain_idx = self.ACTIVE_CHAIN_IDX

        if block.previous_block_hash or self.active_chain:
            prev_block, _, chain_idx = self.locate_block(block.previous_block_hash)

            # if prev_block isn't the latest block, it's a new block
            if prev_block != self.active_chain[-1]:
                chain_idx += 1

        # If validate_block returned a non-existent chain index, we're creating
        # a new side branch
        if chain_idx != self.ACTIVE_CHAIN_IDX and len(self.side_branches) < chain_idx:
            logger.info(
                f'creating a new side branch (idx {chain_idx}) '
                f'for block {block.id}')
            self.side_branches.append([])

        logger.info(f'connecting block {block.id} to chain {chain_idx}')
        chain = (self.active_chain if chain_idx ==
                 self.ACTIVE_CHAIN_IDX else self.side_branches[chain_idx-1])
        chain.append(block)

        # If we added to the active chain, perform upkeep on utxo_set and mempool
        if chain_idx == self.ACTIVE_CHAIN_IDX:
            outpoints_to_remove = set()
            for txn in block.txns:
                # let's clear the mempool, as this transaction has been accepted and mined
                Mempool().mempool_dict.pop(txn.id, None)

                # let's also add the utxo to the current set
                for i, txout in enumerate(txn.txouts):
                    utxo_manager.add_to_utxo(txout, txn, i, txn.is_coinbase, len(chain))

                # if the txn isn't coinbase let's remove the spent utxos
                if not txn.is_coinbase:
                    for txin in txn.txins:
                        outpoints_to_remove.add(txin.outpoint)

            for outpoint in outpoints_to_remove:                
                utxo_manager.rm_from_utxo(*outpoint)
                
        if (not doing_reorg and self.reorg_if_necessary()) or chain_idx == self.ACTIVE_CHAIN_IDX:
            ChainManager.mine_interrupt.set()
            logger.info(
                f'block accepted '
                f'height={len(self.active_chain) - 1} txns={len(block.txns)}'
            )

        return chain_idx

    def get_current_height(self):
        return len(self.active_chain)

    def locate_block(self, block_hash: str, chain=None) -> (Block, int, int):
        """
        returns a tuple of block obj, height, chain id
        """
        chains = [chain] if chain else [self.active_chain, *self.side_branches]
        for chain_idx, chain in enumerate(chains):
            for height, block in enumerate(chain):
                if block.id == block_hash:
                    return (block, height, chain_idx)
        return (None, None, None)

    @with_lock(chain_lock)
    def remove_block_from_chain(self, block, chain=None):
        """
        removes block from the chain
        """
        chain = chain or self.active_chain
        assert block == chain[-1]

        utxo_manager = UTXOManager()
        for txn in block.txns:
            # let's re-add the transaction into the mempool
            Mempool().add_txn_to_mempool(txn, force=True)

            for txin in txn.txins:
                # if it isn't a coinbase
                if txin.outpoint:
                    utxo_manager.add_to_utxo(*find_txout_for_txin(txin, chain))
            for i in range(len(txn.txouts)):
                utxo_manager.rm_from_utxo(txn.id, i)

        logger.info(f'block {block.id} disconnected')
        return chain.pop()

    @with_lock(chain_lock)
    def reorg_if_necessary(self):
        """
        Reorganization happens when the current active chain has diverged from the best longest chain.
        This occurs when the side branch height is greater than the active chain

        There are many ways to compare, including chainwork
        https://bitcoin.stackexchange.com/questions/5540/what-does-the-term-longest-chain-mean
        """

        # create a frozen, shallow copy of side_branches
        reorged = False
        frozen_side_branch = list(self.side_branches)

        for chain_idx, chain in enumerate(frozen_side_branch, 1):
            fork_block, fork_idx, _ = self.locate_block(chain[0].previous_block_hash, self.active_chain)
            
            active_height = len(self.active_chain)
            branch_height = len(chain) + fork_idx

            if branch_height > active_height:
                logger.info(
                    f'Attempting reorg of idx {branch_idx} to active_chain'
                    f"new height of {branch_height} (vs. {active_height})"
                )
                reorged |= self.try_reorg(chain, branch_idx, fork_idx)

        return reorged

    @with_lock(chain_lock)
    def try_reorg(self, chain, branch_idx, fork_idx) -> bool:
        """
        tries to organize the active branch
        """
        fork_block = self.active_chain[fork_idx]

        def disconnect_to_fork():
            """
            while the latest block on the active chain does not equal to the fork block remove
            """
            while self.active_chain[-1].id != fork_block.id:
                yield self.remove_block_from_chain(self.active_chain[-1])

        removed_from_active = list(disconnect_to_fork())[::-1]
        assert chain[-1].previous_block_hash == self.active_chain[-1].id

        def rollback_reorg():
            logger.info(f'reorg of idx {branch_idx} to active_chain failed, rolling back')
            list(disconnect_to_fork()) # clear the self.active_chain

            for block in old_active:
                assert self.add_block_to_chain(block, doing_reorg=True) == self.ACTIVE_CHAIN_IDX

        for block in branch:
            connected_idx = self.add_block_to_chain(block, doing_reorg=True)

            # if we aren't adding to the active chain, then we need to abort
            if connected_idx != self.ACTIVE_CHAIN_IDX:
                rollback_reorg()
                return False

        # now that branch_idx has been incorporated into the active_chain
        # we can delete reference to branch_idx and put removed_from_active into sidechain
        self.side_branches.pop(branch_idx - 1)
        self.side_branches.append(old_active)

        logger.info(f'chain reorg! New height: {len(self.active_chain)}, tip: {self.active_chain[-1].id}')
        return True

    @staticmethod
    def txn_iterator(chain):
        return (
            (txn, block, height)
            for height, block in enumerate(chain) for txn in block.txns
        )

    @staticmethod
    def find_txout_for_txin(txin, chain):
        txid, txout_idx = txin.outpoint

        for txn, block, height in txn_iterator(chain):
            if txn.id == txid:
                txout = txn.txouts[txout_idx]
                return (txout, txn, txout_idx, txn.is_coinbase, height)



