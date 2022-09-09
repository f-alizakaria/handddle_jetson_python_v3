import socket

import time

from lib.logging_service import LoggingService


class Client:

	def __init__(self, ip, port, connection_with_server_established=False):
		self.ip = ip
		self.port = port

		self.socket = None

		self.logger = LoggingService('client').getLogger()


		self.connection_with_server_established = connection_with_server_established

		self.logger.info('[Client] Creating client...')

		self.client_connection()

	def sendData(self, data):

		if not self.connection_with_server_established:
			self.logger.error('[Client] Connection with the server lost.')
			self.connection_with_server_established = False
			self.socket.close()
			self.client_connection()

		else:
			try:
				self.socket.send(str(data).encode('utf8'))

			except BrokenPipeError:
				self.logger.error('[Client] Connection with the server lost.')
				self.connection_with_server_established = False
				self.socket.close()
				self.client_connection()

			except Exception as e:
				self.logger.critical('[Client] Error while sending a message. (Details: {})'.format(e))

	def client_connection(self):
		while not self.connection_with_server_established:
			try:
				# Create socket to connect to the desired IP
				self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self.socket.settimeout(5)
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
									   1)  # to allow to recreate a socket without the address already use error
				self.socket.connect((self.ip, self.port))
				self.connection_with_server_established = True
				self.logger.info('[Client] Done. Client connected to {} on port {}.'.format(self.ip, self.port))
			except Exception as e:
				self.logger.error(f'[Client] Cannot connect to the server with @IP {self.ip}. Retrying...\n(Details: {e}')
				time.sleep(5)

	def send_check_message(self):
		self.sendData('check_message')