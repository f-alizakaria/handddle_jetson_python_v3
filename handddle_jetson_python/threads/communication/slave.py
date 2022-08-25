import threading
import time

from threads.communication.server import Server
from threads.communication.client import Client
from messages.tlv_message import TLVMessage

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/slave/slave.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('slave')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

class Slave(threading.Thread):

	def __init__(self, master, slave, transfer_queue):
		threading.Thread.__init__(self)
		self.master = master
		self.slave = slave
		self.transfer_queue = transfer_queue

		self.master_initialized = False
		self.connection_with_master_lost = False

		self.server = None
		self.client = None


	def run(self):
		# Slave = 1 server + 1 client

		# Init the server
		file_logger.info('[Slave] Initializing slave system.')

		file_logger.info('[Slave] Creating server...')
		self.server = Server(self.slave['ip'], self.slave['port'], self.sendCommandToTransferQueue).start()

		# A slave accepts only one connection (from the master)
		file_logger.info('[Slave] Waiting for the master client to connect...')

		# Init the client
		# Here, the master client should already be connected to the slave server
		file_logger.info('[Slave] Creating client...')
		while self.client is None:
			try:
				self.client = Client(self.master['ip'], self.master['port'], self.connection_with_master_lost)

			except ConnectionRefusedError as e:
				file_logger.error('[Slave] Cannot reach the master system. Retrying...')
				time.sleep(5)

		file_logger.info('[Slave] System fully connected to the master system.')

		self.master_initialized = True

		while True:
			if self.client.connection_with_server_lost:
				file_logger.error(f'[Slave] Connection with Master system lost. (Details: connection_with_master_lost = {self.client.connection_with_server_lost}).\nWaiting for the master client to connect...')
			time.sleep(2)

	def sendDataToMaster(self, data):
		self.client.sendData(data)
		file_logger.info(f'[Slave] Data sent to the master system : {data}')

	def sendCommandToTransferQueue(self, message):

		# Here, we convert string representation of dictionary into dictionary
		message = eval(message)

		# message = json.loads(re.search('({.+})', message).group(0).replace("'", '"'))
		command, hexa = TLVMessage.createTLVCommandFromJson(self.slave['system_codes'][message['system_code']], message['action'], int(message['data']))

		# Command is sent to Transfer Queue to be sent to the STM32 in sendCommandsThread
		self.transfer_queue.put(command)
		file_logger.info(f"[Slave] Command will be sent to STM. ({message['action']} : {message['data']})")