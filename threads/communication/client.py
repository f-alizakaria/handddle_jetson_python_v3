import threading

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
			except Exception as e:
				self.logger.error(f'Cannot connect to the server. Retrying... (Details: {e})')
				time.sleep(1)

	def callbacks(self):
		@Client.sio.event(namespace=f"/{self.namespace_name}")
		def connect():
			self.logger.info('connection established')
			Client.sio.emit('STM', {'response': 'my response to data namespace'}, namespace=f"/{self.namespace_name}")
			self.logger.info('my response sent')

		@Client.sio.event(namespace=f"/{self.namespace_name}")
		def my_message(data):
			self.logger.info('message received with ', data)

		@Client.sio.event
		def disconnect():
			self.logger.info('disconnected from server')
