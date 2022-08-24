import threading
import time
import requests
import os
from messages.tlv_message import TLVMessage

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/commands/commands.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('commands')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

################################
# Read received commands files #
################################


class SendCommandsThread(threading.Thread):
	def __init__(self, thread, master, slaves, profile, se, api_server_config, transfer_queue, debug):
		threading.Thread.__init__(self)
		self.thread = thread
		self.master = master
		self.slaves = slaves
		self.se = se
		self.api_server_config = api_server_config
		self.transfer_queue = transfer_queue
		self.debug = debug
		self.messages_to_send = []

		self.last_check_date = int(time.time())
		self.is_connected = True

		self.profile = profile

	def run(self):

		file_logger.info('Started SendCommandsThread')

		while True:  # Infinite loop
			try:
				waiting_duration = 2 if self.is_connected else 8
				time.sleep(waiting_duration)

				# Messages ready to be sent to all STM32
				self.messages_to_send = []

				if self.profile == 'master':
					# Regular commands
					r = self.api_server_config['session'].get(
						url=self.api_server_config['protocol'] + '://' + self.api_server_config['host'] + '/public/api/farm_commands',
						params={
							'organization_group.code': self.api_server_config['licence_key'],
							'sent_date[gte]': self.last_check_date
						},
						timeout=10
					)
					commands_list = r.json()

					self.is_connected = True
					self.last_check_date = int(time.time())

					for command in commands_list:
						file_logger.info("[APP] Command : ", command)
						try:
							if command['system_code'] in self.master['system_codes']:
								# Check if door is opened
								if command['action'] == 'door_closed':
									self.door_opened(command)

								message, hexa = TLVMessage.createTLVCommandFromJson(self.master['system_codes'][command['system_code']],
																					command['action'],
																					int(command['data']))
								self.messages_to_send.append(message)

								# Test - Uncomment this line to check if the message is well formated
								# file_logger.info(TLVMessage(io.BytesIO(message)))

							else:

								[self.thread.sendCommandToSlave(command) for slave in self.slaves if command['system_code'] in slave['system_codes']]

						except Exception as e:
							file_logger.error('Error: ', e)

				# Add transfered commands
				while not self.transfer_queue.empty():
					self.messages_to_send.append(self.transfer_queue.get())

				# Actually send messages
				self.sendCommandToSTM()

			except requests.exceptions.ConnectionError as e:
				self.is_connected = False
				file_logger.error('The application is not connected to internet. Retrying...')

			except requests.exceptions.ReadTimeout as e:
				self.is_connected = False
				file_logger.error('The application could not reach the web server. Retrying...\nDetails:', e)

			except Exception as e:
				file_logger.critical(f'ERROR: An error occured while sending commands : {e}')

	def sendCommandToSTM(self):

		for message in self.messages_to_send:

			if not self.debug:

				file_logger.info('[ME] Command sent to the STM32.')
				# Send the message to all connected STM32
				try:
					for port_name in self.se:
						for i in range(len(message)):
							self.se[port_name].write(message[i:i + 1])
							time.sleep(0.001)
				except OSError:
					file_logger.critical('A STM32 was disconnected.\nThe program need to restart!')
					os._exit(0)
				except Exception as e:
					file_logger.error(e)

			file_logger.info('>>> Sent command: {:040x}'.format(int.from_bytes(message, byteorder='big')))


	def door_opened(self, command):

		uids = []
		for system_code in self.master['system_codes']:
			if 'R' not in system_code:
				uids.append(self.master['system_codes'][system_code])

		info = {
			'action': 'door_opened',
			'data': 1
		}

		for uid in uids:
			message, hexa = TLVMessage.createTLVInformationFromJson(uid, info['action'], int(info['data']))
			# self.messages_to_send.append(message)
