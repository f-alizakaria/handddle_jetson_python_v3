import threading
import time
import requests
from datetime import datetime
from lib.influxdb_service import InfluxdbService

from messages.tlv_message import TLVMessage
from messages.message import *

from lib.logging_service import LoggingService

from lib.utils import send_message


######################
# Read received data #
######################


class ReadDataThread(threading.Thread):
	def __init__(self, slave_thread, master, slaves, profile, se, influxdb_config, status_dict, last_data, debug):
		threading.Thread.__init__(self)
		self.slave_thread = slave_thread
		self.master = master
		self.slaves = slaves
		self.profile = profile
		self.se = se
		self.influxdb_config = influxdb_config
		self.status_dict = status_dict
		self.last_data = last_data
		self.debug = debug
		self.influxdb_service = InfluxdbService(influxdb_config, debug)
		self.logger = LoggingService('data').getLogger()

		self.namespace_name = 'data'

		self.slaves_uid = [uid for slave in self.slaves for system_code, uid in slave['system_codes'].items()]
		self.master_system_codes = [system_code for system_code, uid in self.master['system_codes'].items()]

	def run(self):

		self.logger.info('Started ReadDataThread')
		time.sleep(0.5)

		while True:  # Infinite loop

			try:
				time.sleep(2)
				has_data_to_send = False
				data_to_send = {}

				for port_name in self.se:

					has_data = False
					raw_received_data = None

					# if there is a port and there are bytes to read
					if self.se[port_name] and self.se[port_name].in_waiting:

						raw_received_data = b''
						while self.se[port_name].in_waiting:
							# read is the method used to get X bytes from the serial communication
							raw_received_data += self.se[port_name].read(1)
							time.sleep(0.001)

						has_data = True

					if self.debug:
						raw_received_data = input('Enter a valid hex message received from the STM32: ')

						# Example test messages
						# raw_received_data = ''
						# raw_received_data = '01010010C0C0C0C002010001AA00000000000000FF' # Main / Temp
						# raw_received_data = '01010010C0C0C0C002010001AA00000000000000FF' # Main / Hum
						# raw_received_data = '01010010C0C0C0C002010001AA02020002FEFE00FF' # Main / Temp + Hum
						# raw_received_data = '01010010C0C0C0C0020C000200FF000000000000FF' # Weight
						# raw_received_data = '01010010C0C0C0C0000500010102020002FEFE00FF' # Internal
						# raw_received_data = '01010010C0C0C0C0010400010400000000000000FF' # Command
						# raw_received_data = '01010010C0C0C0C0030300021001050200010000FF' # Other
						# raw_received_data = '01010010C0C0C0C0040100010100000000000000FF' # Error

						if raw_received_data != '':
							raw_received_data = bytes.fromhex(raw_received_data)
							has_data = True

					if has_data:
						system_code = ''

						# N strings/objets bytes de 20 octets
						raw_received_data_chunks = [raw_received_data[i:i+21] for i in range(0, len(raw_received_data), 21)]

						for chunk in raw_received_data_chunks:
							chunk = chunk[:-1]
							if len(chunk) == 0:
								continue

							try:
								# TODO Check if the following line gets binary data from the STM32 correctly
								tlv_message = TLVMessage(chunk)

								# Here (= no error), we have a valid message from the STM32
								if self.profile == 'master' and tlv_message.uid in self.master['system_codes'].values():
									# We get the system code of the frame
									system_code = [key for key, value in self.master['system_codes'].items() if value == tlv_message.uid][0]
								elif self.profile == 'slave' and tlv_message.uid in self.slaves_uid:
									system_code = [system_code for slave in self.slaves
												   for system_code, uid in slave['system_codes'].items()
												   if tlv_message.uid == uid][0]
								else:
									self.logger.critical('Unknown UID ({}).'.format(tlv_message.uid))

								# Manage received data
								for tlv_data in tlv_message.payload:
									message = tlv_data.payload

									if type(message) is MainMessage:
										has_data_to_send = True

										# Shift system code if needed
										if 'shift' in MainMessage.DATA_TYPES[message.subtype]:
											shift = MainMessage.DATA_TYPES[message.subtype]['shift']

											if shift == 1:
												system_code = system_code.replace('R', 'B').replace('T', 'R')
											elif shift == -1:
												system_code = system_code.replace('R', 'T').replace('B', 'R')

										if system_code not in data_to_send:
											data_to_send[system_code] = {}
										else:
											data_to_send[system_code][message.data.getKey()] = message.data.getValue()

										self.logger.info('<<< Message received on port ' + port_name + ': ' + str(message))

										self.status_dict[tlv_message.uid] = {
											'system_code': system_code, 'check_date': datetime.now(), 'port': port_name
										}

										# Save last data
										if system_code not in self.last_data:
											self.last_data[system_code] = {}
										self.last_data[system_code][message.data.getKey()] = message.data.getValue()
									elif type(message) is CommandMessage:
										self.logger.info('<<< Command message received on port ' + port_name + ': ' + str(message))

										for system_code in self.master_system_codes:
											# Because only roof environment send commands to other environment for now
											if 'T' not in system_code:
												uid = self.master['system_codes'][system_code]
												command, hexa = TLVMessage.createTLVCommandFromJson(
													uid, message.command_name, message.command_value
												)
												send_message(se=self.se, message=command)
												self.logger.info('>>> Command message forwarded	 to ' + system_code + ': ' + str(message))

							except requests.exceptions.ConnectionError as e:
								self.logger.error('The application is not connected to internet. No data sent.')

							except requests.exceptions.ReadTimeout as e:
								self.logger.error('The application could not reach the web server. No data sent.\nDetails:', e)

							except Exception as e:
								self.logger.error('Error with a message received on port {}: {} (Raw message: {})'.format(port_name, e, chunk.hex()))

				if data_to_send:
					self.logger.info(data_to_send)

				if self.profile == 'master' and has_data_to_send:
					# Send all data to influxdb
					# self.influxdb_service.writeDataBySystemCode(data_to_send=data_to_send)
					self.logger.info(f'[Master][DataThread] Datas sent to the cloud. (Details : {data_to_send})')

				elif self.profile == 'slave' and has_data_to_send:
					# send data to the master's server
					self.slave_thread.client.sio.emit('STM', data_to_send, namespace=f'/{self.namespace_name}')
					self.logger.info('[Slave][DataThread] Datas sent to the master system.')

			except Exception as e:
				self.logger.critical(f'ERROR: An error occured while dealing with received data : {e}')
