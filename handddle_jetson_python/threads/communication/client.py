import socket

import logging
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

	def __init__(self, ip, port):
		self.ip = ip
		self.port = port

		file_logger.info('[Client] Creating client...')
		# Create socket to connect to the desired IP
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.connect((self.ip, self.port))
		file_logger.info('[Client] Done. Client connected to {} on port {}.'.format(self.ip, self.port))

	def sendData(self, data):

		try:
			self.socket.send(str(data).encode('utf8'))

		except Exception as e:
			file_logger.critical('[Client] Error while sending a message. (Details: {})'.format(e))

	# time.sleep(1)