import socketio

import time

from lib.logging_service import LoggingService


class Client:
	sio = socketio.Client()

	def __init__(self, ip, port):
		self.ip = ip
		self.port = port

		self.callbacks()
		Client.sio.connect(f'http://{self.ip}:{self.port}', namespaces=['/data'])
		Client.sio.wait()

	def callbacks(self):
		@Client.sio.event(namespace="/data")
		def connect():
			print('connection established')
			Client.sio.emit('STM', {'response': 'my response to data namespace'}, namespace='/data')
			print('my response sent')


		@Client.sio.event(namespace="/data")
		def my_message(data):
			print('message received with ', data)
			Client.sio.emit('', {'response': 'my response 2'})


		@Client.sio.on('commands')
		def message(data):
			print(f"commands: {data}")


		@Client.sio.event
		def disconnect():
			print('disconnected from server')