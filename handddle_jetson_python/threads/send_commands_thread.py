import threading
import time
import requests
import os
from messages.tlv_message import TLVMessage

from lib.logging_service import LoggingService


################################
# Read received commands files #
################################


class SendCommandsThread(threading.Thread):
	def __init__(self, thread, master, slaves, profile, se, api_server_config, transfer_queue, debug, broadcast):
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

		self.logger = LoggingService('commands').getLogger()


		self.profile = profile

		self.broadcast_uid = broadcast['uid']

	def run(self):

		self.logger.info('Started SendCommandsThread')

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
						self.logger.info(f"[APP] Command : {command}")
						try:
							if command['system_code'] in self.master['system_codes'] or command['system_code'] == 'broadcast':

								if command['system_code'] == 'broadcast':
									message, hexa = TLVMessage.createTLVCommandFromJson(
										self.broadcast_uid, 'buzzer', 0
									)
								else:
									message, hexa = TLVMessage.createTLVCommandFromJson(self.master['system_codes'][command['system_code']],
																						command['action'],
																						int(command['data']))
								self.messages_to_send.append(message)

								# Test - Uncomment this line to check if the message is well formated
								# self.logger.info(TLVMessage(io.BytesIO(message)))

							else:

								[self.thread.sendCommandToSlave(command) for slave in self.slaves if command['system_code'] in slave['system_codes']]

						except Exception as e:
							self.logger.error(f'Error: {e}')

			except requests.exceptions.ConnectionError as e:
				self.is_connected = False
				self.logger.error('The application is not connected to internet. Retrying...')

			except requests.exceptions.ReadTimeout as e:
				self.is_connected = False
				self.logger.error(f'The application could not reach the web server. Retrying...\nDetails: {e}')

			except Exception as e:
				self.logger.critical(f'ERROR: An error occured while sending commands : {e}')

			finally:
				# Add transfered commands
				while not self.transfer_queue.empty():
					self.messages_to_send.append(self.transfer_queue.get())

				# Actually send messages
				self.sendCommandToSTM()
				self.transfer_queue.queue.clear()

	def sendCommandToSTM(self):

		for message in self.messages_to_send:

			if not self.debug:

				self.logger.info('[ME] Command sent to the STM32.')
				# Send the message to all connected STM32
				try:
					for port_name in self.se:
						for i in range(len(message)):
							self.se[port_name].write(message[i:i + 1])
							time.sleep(0.001)
				except OSError:
					self.logger.critical('A STM32 was disconnected.\nThe program need to restart!')
					os._exit(0)
				except Exception as e:
					self.logger.error(e)

			self.logger.info('>>> Sent command: {:040x}'.format(int.from_bytes(message, byteorder='big')))
