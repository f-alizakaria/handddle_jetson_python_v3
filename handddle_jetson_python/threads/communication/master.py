import threading
import time

from threads.communication.server import Server
from threads.communication.client import Client

from lib.influxdb_service import InfluxdbService

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/master/master.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('master')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

class Master(threading.Thread):

	def __init__(self, master, slaves, influxdb_config, debug):
		threading.Thread.__init__(self)
		self.master = master
		self.slaves = slaves

		self.influxdb_service = InfluxdbService(influxdb_config, debug)

		# Indexed by system code
		self.server = None
		self.clients = {}


	def run(self):
		# Master = 1 server + N clients

		file_logger.info('[Master] Initializing Master profile.')

		file_logger.info('[Master] Creating {} client(s)...'.format(len(self.slaves)))
		for slave in self.slaves:
			client = None

			while client is None:
				try:
					client = Client(slave['ip'], slave['port'])

					# Associate this client for each system code
					for system_code in slave['system_codes']:
						self.clients[system_code] = client

				except ConnectionRefusedError as e:
					file_logger.critical(f"[Master] Cannot reach the slave system.\nRetrying... at {slave['ip']} : {slave['port']}")
					time.sleep(5)


		# Init the server
		file_logger.info('[Master] Creating server...')
		self.server = Server(self.master['ip'], self.master['port'], self.sendSlaveDataToCloud).start()

		# Accept all slaves connections
		while True:
			for system_code in self.clients:
				self.clients[system_code].check_server_is_alive()
				time.sleep(.01)
			time.sleep(5)

	def sendCommandToSlave(self, command):

		system_code = command['system_code']

		if system_code in self.clients:

			self.clients[system_code].sendData(command)
			# self.clients[system_code].sendData(str(command).encode('utf8'))
			file_logger.info('[Master] Command sent to the slave.')

		else:
			file_logger.critical(f'[Master] Unknown system code. ({system_code})')

	def sendSlaveDataToCloud(self, data):

		# Here, we convert string representation of dictionary into dictionary
		data = eval(data)

		self.influxdb_service.writeDataBySystemCode(data_to_send=data)
		file_logger.info('[Master] Data sent to the cloud.')
