import pytest

from blockchain import Block, chain
from transaction import *
from wallet import build_transaction, pubkey_to_address, signing_key_from_bytes, TRANSACTION_FEE

# here's a sample pub/private key generated from wallet.py
# wallet 1
# address (pubkey): 1MfsCiTUcbQiCR2UGFxL9GgzSmwQBZJWqV
address_1 = '1MfsCiTUcbQiCR2UGFxL9GgzSmwQBZJWqV'
address_pk_1 = b'\x9d\x95N\xc4%\xf6W\xa0\x98\xd6X\xf2\x881w\xd6\x11y\xf2\xe7^[\xf2e\x80\xb6\xe1\xdcC\xe7;t'
# wallet 2
# address (pubkey): 1Q3DzrqjyK54rGxqan9aiEWgRN5RrQ4Whb
address_2 = '1Q3DzrqjyK54rGxqan9aiEWgRN5RrQ4Whb'
address_pk_2 = b' O\x98\xe2\xac\xf0\n1\xc5\xc0\x99\xc8\xbf\xccC1\x96\xc2\xe3\x91*#\xb9&\xbd\xc5\xd6\xbas\xafF\n'


genesis_transactions = [Transaction(txins=[
    TxIn(outpoint=None, signature=SignatureScript(
            unlock_sig=b'0', unlock_pk=None), sequence=0)
    ],
    txouts=[
        TxOut(value=5000000, pubkey=address_1)
    ]
)]

genesis_block = Block(**{
	'version': 0,
	'previous_block_hash': None,
	'merkle_tree_hash': b'\x18\xff\x02\xdd\xbe\x1c5\xef\xc7M\xc4J\xa8G\xcf\r&\t\xf1\xde/\x05\xfd\xed\xeb\xc4\xcf\xb7k\x1e\xbd\xb6',
	'timestamp': 1507593600,
	'nbits': 504382016,
	'nonce': 0,
	'txns': genesis_transactions
})


def test_serialization():
	from serialization import namedtuple_cls_registry
	assert len(namedtuple_cls_registry) > 0

	json_str = genesis_block.serialize()
	deserialized_block = Block.deserialize(json_str)

	assert hasattr(deserialized_block, 'mine')
	assert deserialized_block.version == 0


def test_merkle_tree():
	# let's generate a merkle tree hash from a list of transactions
	merkle_root = MerkleNode.generate_root_from_transaction(genesis_transactions)
	assert merkle_root.value == b'u\x95\x8b\xab\x83?\xf7\x04!\xecc\x9d\xc6R$TF9I\x1b\xe0`\x85\xa8R4\xb3\xfa\x8f\xb8\xd0W'


def test_block():
	utxo_set.clear()
	block_with_nonce = genesis_block.mine()
	block_with_nonce.add_to_chain()

	assert len(chain) == 1
	assert block_with_nonce.nonce != genesis_block.nonce
	assert block_with_nonce._base_hash == b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x18\xff\x02\xdd\xbe\x1c5\xef\xc7M\xc4J\xa8G\xcf\r&\t\xf1\xde/\x05\xfd\xed\xeb\xc4\xcf\xb7k\x1e\xbd\xb6\x80\r\xdcY@B\x10\x1e'
	assert block_with_nonce.nonce == 161201

	assert get_current_balance_for_addr(address_1) == 5000000

	# let's add some additional spending here
	# let's send some money from wallet 1 (address_1) to 2 (1Q3DzrqjyK54rGxqan9aiEWgRN5RrQ4Whb)
	signing_key = signing_key_from_bytes(address_pk_1)
	txn1 = build_transaction(address_2, 50000, address_1, signing_key)
	txn2 = build_transaction(address_2, 50000, address_1, signing_key)
	txns = [txn1, txn2]

	second_block = Block.assemble_and_solve_block(block_with_nonce.id, address_1, [txn1, txn2])
	assert second_block.transaction_fees[txn1.id] == TRANSACTION_FEE
	assert second_block.transaction_fees[txn2.id] == TRANSACTION_FEE

	assert second_block.fees == len(txns) * TRANSACTION_FEE


