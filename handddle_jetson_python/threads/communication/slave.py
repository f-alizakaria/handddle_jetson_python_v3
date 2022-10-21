import threading
import time

from threads.communication.server import Server
from threads.communication.client import Client
from messages.tlv_message import TLVMessage

from lib.logging_service import LoggingService
from lib.utils import send_message



class Slave(threading.Thread):

	def __init__(self, master, slave, se):
		threading.Thread.__init__(self)
		self.master = master
		self.slave = slave
		self.se = se

		self.master_initialized = False
		self.connection_with_master_lost = False

		self.server = None
		self.client = None

		self.logger = LoggingService('slave').getLogger()

	def run(self):
		# Slave = 1 server + 1 client

		# Init the server
		self.logger.info('[Slave] Initializing slave system.')

		self.logger.info('[Slave] Creating server...')
		self.server = Server(self.slave['ip'], self.slave['port'], self.sendCommand)
		self.server.start()

		# A slave accepts only one connection (from the master)
		self.logger.info('[Slave] Waiting for the master client to connect...')

		# Init the client
		# Here, the master client should already be connected to the slave server
		self.logger.info('[Slave] Creating client...')
		while self.client is None:
			try:
				self.client = Client(self.master['ip'], self.master['port'], self.connection_with_master_lost)

			except ConnectionRefusedError:
				self.logger.error('[Slave] Cannot reach the master system. Retrying...')
				time.sleep(5)

		self.logger.info('[Slave] System fully connected to the master system.')

		self.master_initialized = True

		while True:

			# remove dead thread from client_threads list
			for thread in self.server.client_threads:
				if not thread.is_alive():
					self.server.client_threads.remove(thread)
				else:
					self.logger.error(f'[Slave] Connection with Master system lost. (Details: connection_with_server_established = {self.client.connection_with_server_established}).\nRetrying to established the connection...')

			time.sleep(5)

	def sendDataToMaster(self, data):
		self.client.sendData(data)
		if self.client.connection_with_server_established:
			self.logger.info(f'[Slave] Data sent to the master system : {data}')
		else:
			self.logger.info(f'[Slave] Data not sent to the master system : {data}')

	def sendCommand(self, message):

		# Here, we convert string representation of dictionary into dictionary
		message = eval(message)

		command, hexa = TLVMessage.createTLVCommandFromJson(self.slave['system_codes'][message['system_code']], message['action'], int(message['data']))

		# Command is sent to the STM32
		send_message(se=self.se, message=command)
		self.logger.info(f"[Slave] Command be sent to the STM. ({message['action']} : {message['data']})")
