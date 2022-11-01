import threading
import time

from messages.tlv_message import TLVMessage

from lib.logging_service import LoggingService

from lib.utils import send_message



###################
# Smart Farm Demo #
###################


class DemoThread(threading.Thread):
	def __init__(self, master, slaves, profile, se):
		threading.Thread.__init__(self)
		self.uids = master['system_codes'] if profile == 'master' else slaves[0]['system_codes']

		self.logger = LoggingService('demo').getLogger()

		self.broadcast_uid = 'CFFFFFFF'
		for uid, system_code in self.uids.items():
			if system_code == 'broadcast':
				self.broadcast_uid = uid

		self.se = se

	def run(self):

		self.logger.info('Started DemoThread')

		while True:  # Infinite loop
			try:
				self.run_demo()

			except Exception as e:
				self.logger.critical('ERROR: An error occured while running the demo.')

	def run_demo(self):

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 7)
		send_message(se=self.se, message=message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 2)
		send_message(se=self.se, message=message)
		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'temperature', 40)
		send_message(se=self.se, message=message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 4)
		send_message(se=self.se, message=message)
		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'air_extraction', 100)
		send_message(se=self.se, message=message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 3)
		send_message(se=self.se, message=message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 5)
		send_message(se=self.se, message=message)

		time.sleep(60)
