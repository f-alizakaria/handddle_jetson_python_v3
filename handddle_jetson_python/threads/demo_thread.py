import threading
import time

from messages.tlv_message import TLVMessage

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/demo/demo.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('demo')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

###################
# Smart Farm Demo #
###################


class DemoThread(threading.Thread):
	def __init__(self, master, slaves, profile, transfer_queue, debug):
		threading.Thread.__init__(self)
		self.transfer_queue = transfer_queue
		self.uids = master['system_codes'] if profile == 'master' else slaves[0]['system_codes']
		self.debug = debug

		self.broadcast_uid = 'CFFFFFFF'
		for uid, system_code in self.uids.items():
			if system_code == 'broadcast':
				self.broadcast_uid = uid

	def run(self):

		file_logger.info('Started DemoThread')

		while True:  # Infinite loop
			try:
				self.run_demo()

			except Exception as e:
				file_logger.critical('ERROR: An error occured while running the demo.')

	def run_demo(self):

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 7)
		self.transfer_queue.put(message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 2)
		self.transfer_queue.put(message)
		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'temperature', 40)
		self.transfer_queue.put(message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 4)
		self.transfer_queue.put(message)
		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'air_extraction', 100)
		self.transfer_queue.put(message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 3)
		self.transfer_queue.put(message)

		time.sleep(30)

		message, hexa = TLVMessage.createTLVCommandFromJson(self.broadcast_uid, 'led_color', 5)
		self.transfer_queue.put(message)

		time.sleep(60)
