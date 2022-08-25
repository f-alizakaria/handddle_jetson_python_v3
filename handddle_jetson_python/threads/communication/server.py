import socket
import threading

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/server/server.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('server')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

class Server(threading.Thread):

	def __init__(self, ip, port, reception_callback):
		threading.Thread.__init__(self)
		self.ip = ip
		self.port = port
		self.reception_callback = reception_callback

		self.client_threads = []

		# Create socket to the desired IP
		file_logger.info('[Server] Creating server...')
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		file_logger.info(f"Port : {self.port} and IP addr : {self.ip}")
		self.socket.bind((self.ip, self.port))
		self.socket.listen()
		file_logger.info('[Server] Done. Server running on port {} (Host: {}).'.format(self.port, self.ip))

	def acceptClient(self, reception_callback):
		conn, addr = self.socket.accept()

		self.client_threads.append(HandleClientThread(conn, addr, reception_callback))
		self.client_threads[-1].start()

		file_logger.info('[Server] New client connected (Total: {})'.format(len(self.client_threads)))

	def run(self):
		while True:
			self.acceptClient(self.reception_callback)


class HandleClientThread(threading.Thread):

	def __init__(self, conn, addr, reception_callback):
		threading.Thread.__init__(self)
		self.conn = conn
		self.addr = addr
		self.reception_callback = reception_callback

	def run(self):
		while True:
			try:
				message = self.conn.recv(1024).decode('utf8')

				if message:
					file_logger.info('[Server] New message from [{}]: {}'.format(self.addr, message))

					# Execute callback function
					if message == 'check_message':
						file_logger.info(f'check_message with {self.addr} received!')
					elif self.reception_callback is not None:
						self.reception_callback(message)

				else:
					break

			except ConnectionResetError as e:
				file_logger.critical('[Server] Connection lost. (Details: {})'.format(e))
				break

			except Exception as e:
				file_logger.critical('[Server] Error while dealing with a reveiced message. (Details: {})'.format(e))

		self.conn.close()