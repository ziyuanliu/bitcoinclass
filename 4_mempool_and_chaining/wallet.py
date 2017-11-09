import ecdsa
import hashlib
import binascii

from base58 import b58encode_check
from functools import lru_cache
from transaction import get_utxos_for_addr, OutPoint, TxOut, TxIn, Transaction, SignatureScript
from utils import sha256d_hexdigest
from serialization import serialize
from typing import Iterable

TRANSACTION_FEE = 1000


def signing_key_from_bytes(signing_key: bytes):
    return ecdsa.SigningKey.from_string(signing_key, curve=ecdsa.SECP256k1)


def pubkey_to_address(pubkey: bytes) -> str:
    sha = hashlib.sha256(pubkey).digest()
    ripe = hashlib.new('ripemd160', sha).digest()
    return b58encode_check(b'\x00'+ripe)


def create_address():
    """
    Creates a signing key, then generates an address from it
    """
    signing_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    verifying_key = signing_key.get_verifying_key()
    addr = pubkey_to_address(verifying_key.to_string())
    return addr, signing_key


def build_spend_message(outpoint: OutPoint, pk: str, sequence: int, txouts: TxOut):
    """
    https://bitcoin.org/en/developer-guide#term-sighash-all
    similar to: SIGHASH_ALL
    """
    return sha256d_hexdigest(
        outpoint.serialize() + str(sequence) +
        binascii.hexlify(pk).decode() + serialize(txouts)
    ).encode()


def make_txin(signing_key, outpoint: OutPoint, txout: TxOut) -> TxIn:
    """
    Make Transaction Input
    """

    # https://en.bitcoin.it/wiki/Transaction#general_format_.28inside_a_block.29_of_each_input_of_a_transaction_-_Txin
    # currently we do not need to worry about sequence unless there exists a locktime, BIP125
    sequence = 0
    pubkey = signing_key.verifying_key.to_string()
    spend_message = build_spend_message(outpoint, pubkey, sequence, [txout])
    return TxIn(signature=SignatureScript(unlock_sig=signing_key.sign(spend_message), unlock_pk=pubkey), outpoint=outpoint, sequence=sequence)


def build_transaction(to_pubkey, value_to_send, my_pubkey, signing_key, fee=TRANSACTION_FEE):
    """
    This will create a pay-to-public-key transaction, for this function we will assume a constant transaction fee,
    our protocol will assume no minimum fees. We will create a change output to the sender.
    """

    # first grab all the utxo belonging to my_pubkey, sort utxo ascendingly by value and height
    utxos = set(sorted(get_utxos_for_addr(my_pubkey), key=lambda utxo: (utxo.value, utxo.height)))

    total_to_send = value_to_send + fee
    to_be_spent = []
    current_value = 0

    for utxo in utxos:
        to_be_spent.append(utxo)
        current_value += utxo.value
        if current_value > total_to_send:
            # we have all we need to send
            break

    txout = TxOut(value=value_to_send, pubkey=to_pubkey)

    change_amt = sum(utxo.value for utxo in to_be_spent) - total_to_send
    txout_change = TxOut(value=change_amt, pubkey=my_pubkey)

    # we need to make txin now based on where we want to send the outputs
    txins = []
    current_value = 0
    for utxo in to_be_spent:
        current_value += utxo.value
        if current_value > total_to_send:
            txn = make_txin(signing_key, utxo.outpoint, txout_change)
        else:
            txn = make_txin(signing_key, utxo.outpoint, txout)
        txins.append(txn)

    if change_amt < 0:
        raise ValueError(f'insufficient funds {current_value}')

    return Transaction(txins=txins, txouts=[txout, txout_change])

