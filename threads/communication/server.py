import socket
import threading

from lib.logging_service import LoggingService


class Server(threading.Thread):

	def __init__(self, ip, port, reception_callback):
		threading.Thread.__init__(self)
		self.ip = ip
		self.port = port
		self.reception_callback = reception_callback

		self.logger = LoggingService('server').getLogger()

		self.client_threads = []

		# Create socket to the desired IP
		self.logger.info('[Server] Creating server...')
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.logger.info(f"Port : {self.port} and IP addr : {self.ip}")
		self.socket.bind((self.ip, self.port))
		self.socket.listen()
		self.logger.info('[Server] Done. Server running on port {} (Host: {}).'.format(self.port, self.ip))

	def acceptClient(self, reception_callback):
		conn, addr = self.socket.accept()

		self.client_threads.append(HandleClientThread(conn, addr, reception_callback, self.logger))
		self.client_threads[-1].start()

		self.logger.info('[Server] New client connected (Total: {})'.format(len(self.client_threads)))

	def run(self):
		while True:
			# Accept all client connections
			self.acceptClient(self.reception_callback)


class HandleClientThread(threading.Thread):

	def __init__(self, conn, addr, reception_callback, logger):
		threading.Thread.__init__(self)
		self.conn = conn
		self.conn.settimeout(15)
		self.addr = addr
		self.reception_callback = reception_callback
		self.logger = logger

	def run(self):
		while True:
			try:
				message = self.conn.recv(1024).decode('utf8')

				if message:
					if message == 'check_message':
						self.logger.info('Check message received.')
						continue

					self.logger.info('[Server] New message from [{}]: {}'.format(self.addr, message))

					# Execute callback function
					if self.reception_callback is not None:
						self.reception_callback(message)
				else:
					self.logger.critical('[Server] Connection lost.')
					break

			except ConnectionResetError as e:
				self.logger.critical('[Server] Connection lost. (Details: {})'.format(e))

			except socket.timeout:
				self.logger.critical("[Server] Timeout raised and caught. Please verify the Ethernet cables.")

			except Exception as e:
				self.logger.critical('[Server] Error while dealing with a reveiced message. (Details: {})'.format(e))

		self.conn.close()
