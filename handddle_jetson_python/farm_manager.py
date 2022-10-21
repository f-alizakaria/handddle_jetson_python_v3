import os

import requests
import serial
import serial.tools.list_ports as port_list
import yaml
import time
from queue import Queue

from threads.read_data_thread import ReadDataThread
from threads.send_commands_thread import SendCommandsThread
from threads.watchdog_thread import WatchdogThread
from threads.scanner_thread import ScannerThread
from threads.gui_thread import GUIThread
from threads.demo_thread import DemoThread
from messages.tlv_message import TLVMessage

from threads.communication.master import Master
from threads.communication.slave import Slave

from lib.logging_service import LoggingService



class FarmManager:

	def __init__(self, config_filepath):

		# Configuration
		self.config_filepath = config_filepath

		self.api_server_config = None
		self.influxdb_config = None

		self.serial_baudrate = None
		self.serial_ports_prefix = None

		self.scanner_config = None
		self.watchdog_interval = None

		self.debug = False
		self.demo = False
		self.display_data = False

		self.master, self.slaves = None, None
		self.profile = None
		self.broadcast = None

		self.socket_server_config = None

		self.serverClientThread = None

		self.gui_host = None
		self.gui_port = None

		self.config = self.readConfigFile(config_path=self.config_filepath)
		self.loadConfiguration()

		LoggingService.config = self.config['logging']

		# Logging
		self.logger = LoggingService('main').getLogger()

		TLVMessage.LOGGER = LoggingService('tlv_message').getLogger()

		# Start desired system
		self.startMasterOrSlave()

		# Serial
		self.se = {}
		self.loadUSBPorts()

		# Status & last data
		self.status_dict = {}
		self.last_data = {}

		# Multithreading
		self.readDataThread = ReadDataThread(self.serverClientThread, self.master, self.slaves, self.profile, self.se, self.influxdb_config, self.status_dict, self.last_data, self.debug)
		self.sendCommandsThread = SendCommandsThread(self.serverClientThread, self.master, self.slaves, self.profile, self.se, self.socket_server_config, self.debug, self.broadcast)
		self.watchdogThread = WatchdogThread(self.watchdog_interval, self.broadcast, self.debug, self.se)
		self.scannerThread = ScannerThread(self.scanner_config, self.api_server_config, self.debug)
		self.guiThread = GUIThread(self.se, self.master, self.slaves, self.profile, self.broadcast, self.socket_server_config, self.status_dict, self.last_data, self.display_data, self.debug, self.gui_host, self.gui_port)

		self.threads = [
			self.readDataThread,
			self.sendCommandsThread,
			self.watchdogThread,
			self.scannerThread,
			self.guiThread
		]

		if self.demo:
			self.demoThread = DemoThread(self.master, self.slaves, self.profile, self.se)
			self.threads.append(self.demoThread)

	def readConfigFile(self, config_path):
		with open(config_path, 'r') as config_file:
			return yaml.load(config_file, Loader=yaml.FullLoader)

	def loadConfiguration(self):

		# Load GUI parameters
		self.gui_host = self.config['gui']['host']
		self.gui_port = self.config['gui']['port']

		self.debug = self.config['debug']
		self.demo = self.config['demo']
		self.display_data = self.config['display_data']

		# Socket configuration
		self.socket_server_config = self.config['socket_server']

		self.api_server_config = self.config['api_server']
		# Create a unique server session for the whole app
		self.api_server_config['session'] = requests.Session()

		self.influxdb_config = self.config['influxdb']

		# STM communication
		self.serial_baudrate = self.config['serial']['baudrate']
		self.serial_ports_prefix = self.config['serial']['ports_prefix']

		self.scanner_config = self.config['scanner']

		self.watchdog_interval = self.config['watchdog_interval']

	def loadUSBPorts(self):
		self.logger.info('------------------------------')
		self.logger.info('Ports initilization:')

		if not self.debug:

			ports = list(port_list.comports())

			self.se = {}
			for port_full_name, description, hwid in ports:
				# Do not use the scanner
				hwid = hwid.split()

				if len(hwid) > 2 and hwid[2].startswith('SER='):
					usb_serial_number = int(hwid[2].strip('SER='), 16)

					if usb_serial_number == self.scanner_config['serial_base']:
						continue

				if port_full_name.startswith(self.serial_ports_prefix):
					self.se[port_full_name] = serial.Serial()
					self.se[port_full_name].baudrate = self.serial_baudrate
					self.se[port_full_name].port = port_full_name
					self.se[port_full_name].open()

					time.sleep(0.1)
					self.se[port_full_name].flushInput()
					self.se[port_full_name].flushOutput()

					self.logger.info('\t- Port {} initialized.'.format(port_full_name))

		else:
			self.se['P0'] = None
			self.logger.debug('\t- Port P0 initialized [DEBUG].')

		self.logger.info('{} port(s) initialized.'.format(len(self.se)))
		self.logger.info('------------------------------')

	def closePorts(self):
		if not self.debug:
			for port_name in self.se:
				try:
					self.se[port_name].close()
				except Exception as e:
					self.logger.critical('Cannot close port {}: {}'.format(port_name, e))

	def startProcesses(self):

		self.serverClientThread.start()

		if self.profile == 'slave':
			while not self.serverClientThread.master_initialized:
				time.sleep(1)

		for thread in self.threads:
			thread.start()

		for thread in self.threads:
			thread.join()

	def getMasterAndSlaves(self, config):

		if 'systems' not in config:
			self.logger.critical('No systems defined.')

		master = None
		slaves = []

		for system in config['systems']:

			if 'ip' not in system or 'port' not in system:
				self.logger.critical('Bad systems configuration.')

			if system['profile'] == 'master':
				if master is not None:
					self.logger.error('Only one system can be a master system.')

				master = system

			elif system['profile'] == 'slave':
				slaves.append(system)

			else:
				self.logger.error("Only 'master' and 'slave' system can be defined."
								"\nPlease check the YAML configuration file")

		if master is None:
			self.logger.critical('A master system must be defined.')

		return master, slaves

	def startMasterOrSlave(self):
		# Get master and slaves configurations
		self.master, self.slaves = self.getMasterAndSlaves(self.config)

		# Start desired systems
		for system in [self.master] + self.slaves:

			if 'start' not in system or not system['start']:
				continue

			if system['profile'] == 'master':
				self.serverClientThread = Master(self.master, self.slaves, self.influxdb_config, self.debug)
			else:
				self.serverClientThread = Slave(self.master, system, self.se)

			self.profile = system['profile']
			self.broadcast = self.config['broadcast']


if __name__ == '__main__':

	farmManager = None

	try:
		config_filepath = os.environ['CONF_FILE'] if 'CONF_FILE' in os.environ else './config.yaml'
		farmManager = FarmManager(config_filepath)
		farmManager.startProcesses()

	except Exception as e:
		raise AttributeError(f'Error: {e}')

	finally:
		if farmManager is not None:
			farmManager.closePorts()
