import threading
import time

from threads.communication.server import Server
from threads.communication.client import Client

from lib.influxdb_service import InfluxdbService

from lib.logging_service import LoggingService


class Master(threading.Thread):

	def __init__(self, master, slaves, influxdb_config, debug):
		threading.Thread.__init__(self)
		self.master = master
		self.slaves = slaves

		self.influxdb_service = InfluxdbService(influxdb_config, debug)

		# Indexed by system code
		self.server = None
		self.clients = {}
		self.clients_list = []

		self.logger = LoggingService('master').getLogger()


	def run(self):
		# Master = 1 server + N clients

		self.logger.info('[Master] Initializing Master profile.')

		self.logger.info('[Master] Creating {} client(s)...'.format(len(self.slaves)))
		for slave in self.slaves:
			client = None

			while client is None:
				try:
					client = Client(slave['ip'], slave['port'], 'master')
					client.start()

					# Associate this client for each system code
					for system_code in slave['system_codes']:
						self.clients[system_code] = client

				except Exception as e:
					self.logger.critical(f"[Master] Cannot reach the slave system.\nRetrying... at {slave['ip']} : {slave['port']}")
					time.sleep(5)

		self.clients_list = list(dict.fromkeys([client for client in self.clients.values()])) # Save all clients and remove duplicates

		# Init the server
		self.logger.info('[Master] Creating server...')
		self.server = Server(self.master['ip'], self.master['port'], self.sendSlaveDataToCloud, 'master')
		self.server.start()

		while True:
			time.sleep(5)

	def sendCommandToSlave(self, command):
		system_code = command['system_code']

		if system_code in self.clients:
			self.clients[system_code].sio.emit('STM', command, namespace='/data')
			self.logger.info('[Master] Command sent to the slave.')
		else:
			self.logger.critical(f'[Master] Unknown system code. ({system_code})')

	def sendSlaveDataToCloud(self, data):

		# Here, we convert string representation of dictionary into dictionary
		data = eval(data)

		self.influxdb_service.writeDataBySystemCode(data_to_send=data)
		self.logger.info(f'[Master] Data sent to the cloud.\n{data}')
