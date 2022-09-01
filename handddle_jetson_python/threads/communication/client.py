import socket

import logging
import time
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/client/client.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('client')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

class Client:

	def __init__(self, ip, port, connection_with_server_established=False):
		self.ip = ip
		self.port = port

		self.socket = None

		self.connection_with_server_established = connection_with_server_established

		file_logger.info('[Client] Creating client...')

		self.client_connection()

	def sendData(self, data):

		if not self.connection_with_server_established:
			file_logger.error('[Client] Connection with the server lost.')
			self.connection_with_server_established = False
			self.socket.close()
			self.client_connection()

		else:
			try:
				self.socket.send(str(data).encode('utf8'))

			except BrokenPipeError:
				file_logger.error('[Client] Connection with the server lost.')
				self.connection_with_server_established = False
				self.socket.close()
				self.client_connection()

			except Exception as e:
				file_logger.critical('[Client] Error while sending a message. (Details: {})'.format(e))

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
				file_logger.info('[Client] Done. Client connected to {} on port {}.'.format(self.ip, self.port))
			except Exception as e:
				file_logger.error(f'[Client] Cannot connect to the server with @IP {self.ip}. Retrying...\n(Details: {e}')
				time.sleep(5)