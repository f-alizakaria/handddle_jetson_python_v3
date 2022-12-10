import threading
from urllib3.exceptions import NewConnectionError

import socketio
import threading

import time

from lib.logging_service import LoggingService


class Client(threading.Thread):
	sio = socketio.Client()

	def __init__(self, ip, port, profile):
		super().__init__()
		self.ip = ip
		self.port = port
		self.profile = profile
		self.client_connected = False

		self.logger = LoggingService('client').getLogger()

		self.namespace_name = 'commands' if self.profile == 'master' else 'data'

	def run(self):
		while not self.client_connected:
			try:
				self.callbacks()
				Client.sio.connect(f'http://{self.ip}:{self.port}', namespaces=[f"/{self.namespace_name}"])
				Client.sio.wait()
				self.client_connected = True
			except socketio.exceptions.ConnectionError:
				self.logger.info(f'Cannot connect to server with ip {self.ip} and port {self.port}, retrying in 5 seconds')
				time.sleep(5)
			except Exception as e:
				self.logger.error(f'Cannot connect to the server. Retrying... (Details: {e})')
				time.sleep(5)

	def callbacks(self):
		@Client.sio.event(namespace=f"/{self.namespace_name}")
		def connect():
			self.logger.info('Connection established with server')

		@Client.sio.event(namespace=f"/{self.namespace_name}")
		def my_message(data):
			self.logger.info('message received with ', data)

		@Client.sio.event
		def disconnect():
			self.logger.info('disconnected from server')
