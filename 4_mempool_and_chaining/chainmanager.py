
from typing import Iterable

from threading import RLock, Event
from utils import Singleton, with_lock


class ChainManager(metaclass=Singleton):
    """
    Responsible for chain managing, every aspect of the chain will be defined here
    """
    
    chain_lock = RLock()
    mine_interrupt = Event()

    def __init__(self):
        self.active_chain: Iterable[Block] = []
        self.side_branches: Iterable[Iterable[Block]] = []
        self.orphan_blocks: Iterable[Block] = []
        self.active_chain_idx: int = 0
        

    def add_block_to_chain(self, block: Block):
        self.active_chain.append(block)

        for txn in block.txns:
            for i, txout in enumerate(txn.txouts):
                add_to_utxo(txout, txn, i, txn.is_coinbase, len(chain))

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
    def connect_block(block: Block, doing_reorg=False) -> Union[None, Block]:
        """
        Accept a block and return the chain index we append it to.
        """

        search_chain = active_chain if doing_reorg else None

        if locate_block(block.id, chain=search_chain)[0]:
            logger.debug(f'ignore block already seen: {block.id}')
            return None

        chain_idx = self.active_chain_idx

        if block.prev_block_hash or self.active_chain:
            prev_block, _, chain_idx = self.locate_block(block.prev_block_hash)

            # if prev_block isn't the latest block, it's a new block
            if prev_block != self.active_chain[-1]:
                chain_idx += 1

        # If validate_block returned a non-existent chain index, we're creating
        # a new side branch
        if chain_idx != self.active_chain_idx and len(self.side_branches) < chain_idx:
            logger.info(
                f'creating a new side branch (idx {chain_idx}) '
                f'for block {block.id}')
            self.side_branches.append([])

        logger.info(f'connecting block {block.id} to chain {chain_idx}')
        chain = (self.active_chain if chain_idx ==
                 self.active_chain_idx else self.side_branches[chain_idx-1])
        chain.append(block)

        # If we added to the active chain, perform upkeep on utxo_set and mempool
        if chain_idx == self.active_chain_idx:
            for txn in block.txns:
                mempool.pop(txn.id, None)

                if not txn.is_coinbase:
                    for txin in txn.txins:
                        rm_from_utxo(*txin.outpoint)
                for i, txout in enumerate(txn.txouts):
                    add_to_utxo(txout, txn, i, txn.is_coinbase, len(chain))

        if (not doing_reorg and reorg_if_necessary()) or chain_idx == self.active_chain_idx:
            ChainManager.mine_interrupt.set()
            logger.info(
                f'block accepted '
                f'height={len(self.active_chain) - 1} txns={len(block.txns)}'
            )

        return chain_idx

    @with_lock(chain_lock)
    def disconnect_block(self, block, chain=None):
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



