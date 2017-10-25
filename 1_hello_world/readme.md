# Module 1 - Hello World
---

In this module, we will beginning to explore the peer to peer nature of the blockchain and bitcoin in general. While most online tutorials start off with the blockchain as the basis. I think it's best for beginner blockchain engineers to think in a distributed and decentralized manner first.


## Goal

The goal of this module is to have the students first install docker and PYTHON 3.6 locally. We will then proceed to create a little p2p hello world. The goal is make sure that the students have a very easy time understanding and implementing in a p2p environment. Along with that completed, we should have a very good idea of what the backbone of our networking structure should be.


## Infrastructure

The idea is that every single node in the network is able to listen and respond to messages from other nodes. First, each node will start up and register with the DNS service node, in which the DNS service node will reply with a list of peers that does not include the requesting node. If DNS node responds with an empty list, then the node should wait a bit and reissue the request. Once a list of peers are passed down to the node, the node itself should begin to "greet" other nodes by sending them a greeting type message. Once other nodes receive a greeting, it should NOT send any messages, but rather log that it was greeted.


## Additional readings

 - [DNS Seeding](https://bitcoin.org/en/glossary/dns-seed) - how bitcoin clients retrieve their peers (this is not the only mechanism more can be seen [here](https://bitcoin.stackexchange.com/questions/3536/how-do-bitcoin-clients-find-each-other))
 - [BTC Message Structure](https://en.bitcoin.it/wiki/Protocol_documentation#Message_structure) - we will not, for the sake of simplicity, use these protocols
 - [Python 3.6 socket](https://docs.python.org/3.6/library/socketserver.html) - good start to lower level socket manipulation in Python.