# Module 2 - The Block
---

In this module, since we now understand how nodes will communicate with each other, we can ignore it and come to it later. This module highlights the crux of the cryptocurrency: Proof of Work. This famous phrase is more than buzzword, it's what keeps the entire blockchain until now, free from corruption and tempering. We will explore why mining is so important and central to the whole blockchain. This module will standalone from the networking module we have created in module 1. We will test this module by writing tests.


## Goal

The goal of this module is to have students implement a blockchain with bare minimal capability. This blockchain should be only useful for mining and nothing else. It should also be apparent to the student on why shad256 is an important function to deter attacks and how double sha256 adds additional rounds.


## Infrastructure

First, we need to add the additional blockchain datastructures. We should not need networking for this module; we will add networking by after implementing transactions. We will start by adding the necessary utility cryptography functions.


## Additional readings

 - [HashCash](https://en.bitcoin.it/wiki/Hashcash) - Bitcoin protocol actually uses the hashcash proof of work
 - [BTC datastructures](https://en.bitcoin.it/wiki/Protocol_rules#Data_structures) - There here list the three main types of blocks in the blockchain.
 - [NamedTuples](https://docs.python.org/3.6/library/collections.html#collections.namedtuple) - Python documentation the basis of our class
 - [Bitcoin Protocol: Block](https://bitcoin.org/en/glossary/block) - What a block is comprised of. In this module, we left out a lot of features.
 - [Bitcoin Development: Block Header](https://bitcoin.org/en/developer-reference#block-headers) - What we store in our blocks
 - [Bitcoin compact python bits](https://github.com/petertodd/python-bitcoinlib/blob/master/bitcoin/core/serialize.py#L318) & [Bitcoin compact bits](https://github.com/bitcoin/bitcoin/blob/master/src/arith_uint256.cpp#L206): both are implementations of converting a target to a compact bits, vice versa.