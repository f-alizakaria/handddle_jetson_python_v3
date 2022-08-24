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

	def __init__(self, ip, port, connection_with_server_lost=False):
		self.ip = ip
		self.port = port

		self.connection_with_server_lost = connection_with_server_lost

		self.socket = None

		self.client_connection()

	def sendData(self, data):

		try:
			self.socket.send(str(data).encode('utf8'))

		except BrokenPipeError:
			file_logger.error('[Client] Connection with the server lost.')
			self.connection_with_server_lost = True

			while self.connection_with_server_lost:
				try:
					self.client_connection()
					self.connection_with_server_lost = False
				except ConnectionRefusedError:
					file_logger.error('[Client] Cannot connect to the server. Retrying...')
					time.sleep(5)

		except Exception as e:
			file_logger.critical('[Client] Error while sending a message. (Details: {})'.format(e))

	# time.sleep(1)

	def client_connection(self):
		file_logger.info('[Client] Creating client...')
		# Create socket to connect to the desired IP
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # to allow to recreate a socket without the address already use error
		self.socket.connect((self.ip, self.port))
		file_logger.info('[Client] Done. Client connected to {} on port {}.'.format(self.ip, self.port))

	def check_server_is_alive(self):
		self.sendData('check_message')