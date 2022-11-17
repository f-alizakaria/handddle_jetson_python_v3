import socket
import socketio
import threading
import eventlet

from lib.logging_service import LoggingService


class Server:
	sio = socketio.Server()
	app = socketio.WSGIApp(sio)

	def __init__(self, ip, port, reception_callback):
		self.ip = ip
		self.port = port
		self.client_threads = []
		self.profile = 'master' # profile

		self.logger = LoggingService('server').getLogger()
		self.reception_callback = reception_callback
		self.callbacks()
		self.init_socket_server_connection()

	def init_socket_server_connection(self):
		eventlet.wsgi.server(eventlet.listen((self.ip, self.port)), Server.app)

	def callbacks(self):
		@Server.sio.event(namespace="/data")
		def connect(sid, environ):
			self.client_threads.append(environ["REMOTE_ADDR"]) # Client IP addr
			# self.client_threads[-1].start()

			self.logger.info('[Server] New client connected (Total: {})'.format(len(self.client_threads)))

		def handle_client(reception_callback, remote_addr):
			self.logger.info()

		@Server.sio.on('STM', namespace='/data')
		def message(sid, data):
			self.logger.info(f"message: {data}")

			if self.profile == 'master':
				self.logger.info("Slave's data will be sent to the Cloud")
			else:
				self.logger.info("Command will be sent to the STM")

		@Server.sio.event(namespace="/data")
		def disconnect(sid):
			self.logger.info(f"disconnect {sid}")

		@Server.sio.event(namespace="/data")
		def connect_error(sid):
			self.logger.info('The connection failed ', sid)


