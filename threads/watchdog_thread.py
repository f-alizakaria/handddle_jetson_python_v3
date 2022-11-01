import threading
import time

from messages.tlv_message import TLVMessage

from lib.logging_service import LoggingService
from lib.utils import send_message


#######################
# Smart Farm Watchdog #
#######################


class WatchdogThread(threading.Thread):
	def __init__(self, interval, broadcast, debug, se):
		threading.Thread.__init__(self)
		self.debug = debug

		self.interval = interval
		self.count = 0

		self.logger = LoggingService('watchdog').getLogger()

		self.broadcast_uid = broadcast['uid']

		self.se = se

	def run(self):

		self.logger.info('Started WatchdogThread')

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
					send_message(se=self.se, message=message)
					self.logger.info('>>> Sent command: {:040x}'.format(int.from_bytes(message, byteorder='big')))


			except Exception as e:
				self.logger.critical(f'ERROR: An error occured while sending the watchdog command. (Details: {e})')
