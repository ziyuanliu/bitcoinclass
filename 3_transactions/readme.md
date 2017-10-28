# Module 3 - Transactions
---

In this module, we will need implement the transactions, the core component to the bitcoin economy. In a transaction, we will introduce the idea of inputs and outputs, which each transfer (save for the coinbase transaction) will have. In addition to introducing the inputs and outputs, we will also need to introduce fees, which can be implemented in any way we should choose to! 

When talking about fees, there exists two different types: Mining reward (which isn't really a fee) and network fee. The mining reward exists as a general consensus between miners that for each block mined, the miner or pool gets x amount of coins as reward. The networking fee on the other hand is a fee required by many modern day mining nodes (in order to deter spam or attackers) as a incentive to include such transactions in the mined blocked.


## Goal

The goal of this module is to first implement all the necessary data structures that is a part of the simple Bitcoin transaction protocol and including such transactions in a block to be mined. In a limited coin supply economy, we must also consider how a network fee is determined since the Mining reward will not last forever.


## Infrastructure

In order to create a successful change output inside a transaction, we need to consider both the value to send and the fee. The change output is simply the total of input values minus the sum of value and fee.

## Additional readings
