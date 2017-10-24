#!/usr/bin/env python3
"""
Networking component

will include a server to listen and socket send protocols
https://docs.python.org/3.6/library/socketserver.html
"""

import binascii
import logging
import os
import socket
import socketserver
import threading
import time


LISTENING_PORT = 8888
RETRY_TIMES = 3
RETRY_BASE_INTERVAL = 0.75
DNS_SEED_NODE = 'node1'
L_GREETING_FMT = 'Hello World {name}'
L_REGISTER_FMT = 'Seed Server Registering {name}'

# commands 
K_REGISTER = 'register'
K_PEERS = 'peers'
K_GREETING = 'greeting'


logging.basicConfig(
    level=getattr(logging, os.environ.get('TC_LOG_LEVEL', 'INFO')),
    format='[%(asctime)s][%(module)s:%(lineno)d] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

peers_set = set()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class HelloWorldServiceHandler(socketserver.BaseRequestHandler):
	def handle(self):
		global peers_set
		message_type, data = decode_from_request(self.request)

		if message_type == K_REGISTER:
			registering_peer = self.request.getpeername()[0]
			peers_set.add(registering_peer)
			logger.info(L_REGISTER_FMT.format(name=registering_peer))

			if len(peers_set) > 1:
				send_to_node(K_PEERS, '|'.join(peers_set - {registering_peer}), registering_peer)

		elif message_type == K_PEERS:
			# data here is delimited by |
			peers = data.split('|')
			if peers:
				for peer in peers:
					logger.info(L_GREETING_FMT.format(name=peer))
					send_to_node(K_GREETING, '', peer)
			else:
				# in the case that zero peer was returned, we should probably wait and then reissue the request
				logger.info('reissuing DNS registration')
				send_to_node(K_REGISTER, '', DNS_SEED_NODE)
		elif message_type == K_GREETING:
			peer = self.request.getpeername()[0]
			logger.info(L_GREETING_FMT.format(name=peer))


def _encode(message_type: str, data: str) -> bytes:
	"""
	this method will encode our data with a 4 bytes message size prefix.
	"""
	
	msg_data = f'{message_type}:{data}'
	byte_data = msg_data.encode()
	byte_date_size = len(byte_data)

	# https://docs.python.org/3.1/library/string.html#format-examples
	size_hex = f'{byte_date_size:0{8}x}'
	return binascii.unhexlify(size_hex) + byte_data


def send_to_node(message_type: str, data: str, node: str, retries=RETRY_TIMES):
	"""
	Send to node with linear backoff
	https://en.wikipedia.org/wiki/Exponential_backoff
	"""

	try:
		logger.info(f'sending this {message_type} to {node} {LISTENING_PORT}')
		with socket.create_connection((node, LISTENING_PORT), timeout=1) as s:
			s.sendall(_encode(message_type, data))
	except Exception as e:
		logger.error(str(e))
		if retries > 0:
			retries -= 1
			time.sleep(RETRY_BASE_INTERVAL*(RETRY_TIMES - retries))
			send_to_node(message_type, data, node, retries)


def decode_from_request(req) -> str:
	"""
	this method will decode our data by reading the size first (first 4 bytes)
	"""

	# grab the first four bytes, 0x00 if None
	first_four_bytes = req.recv(4) or b'\x00'

	# convert it into a data size
	data_size = int(binascii.hexlify(first_four_bytes), 16)	

	message = b''

	while data_size > 0:
		chunk = req.recv(512)
		message += chunk
		data_size -= len(chunk)

	message_type, data = message.decode().split(':', 1)
	return message_type, data


if __name__ == '__main__':
	server = ThreadedTCPServer(('0.0.0.0', LISTENING_PORT), HelloWorldServiceHandler)
	server_thread = threading.Thread(target=server.serve_forever, daemon=True)
	server_thread.start()
	logger.info(f'[p2p] listening on PORT {LISTENING_PORT}')
	
	if not os.environ.get('DNS_SEED', False):
		# https://bitcoin.org/en/glossary/dns-seed
		# if this node is not the seed server, let's register
		send_to_node(K_REGISTER, '', DNS_SEED_NODE)

	server_thread.join()
