import threading
import time

from messages.tlv_message import TLVMessage

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/watchdog/watchdog.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('watchdog')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

#######################
# Smart Farm Watchdog #
#######################


class WatchdogThread(threading.Thread):
	def __init__(self, interval, transfer_queue, broadcast, debug):
		threading.Thread.__init__(self)
		self.transfer_queue = transfer_queue
		self.debug = debug

		self.interval = interval
		self.count = 0

		self.broadcast_uid = broadcast['uid']

	def run(self):

		file_logger.info('Started WatchdogThread')

		while True:  # Infinite loop
			try:
				self.count += 1
				time.sleep(1)

				# Watchdog update
				if self.count >= self.interval:
					message, hexa = TLVMessage.createTLVCommandFromJson(
						self.broadcast_uid, 'update_watchdog', 1
					)

					self.count = 0
					self.transfer_queue.put(message)

			except Exception as e:
				file_logger.critical(f'ERROR: An error occured while sending the watchdog command. (Details: {e})')
