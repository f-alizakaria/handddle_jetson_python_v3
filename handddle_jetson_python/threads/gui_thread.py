import threading
import time
from os.path import dirname, abspath
from flask import Flask, render_template
from datetime import datetime

from messages.tlv_message import TLVMessage
from waitress import serve

import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILE = "/var/log/handddle_jetson_python/gui/gui.log"
FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")

file_logger = logging.getLogger('gui')
file_logger.setLevel(logging.DEBUG)

file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
file_handler.setFormatter(FORMATTER)

file_logger.addHandler(file_handler)
file_logger.propagate = False

##################
# Smart Farm GUI #
##################


class GUIThread(threading.Thread):
	def __init__(self, master, slaves, profile, broadcast, api_server_config, status_dict, last_data, display_data, transfer_queue, debug):
		threading.Thread.__init__(self)

		self.broadcast_uid = broadcast['uid']
		self.uids = master['system_codes'] if profile == 'master' else slaves[0]['system_codes']
		self.api_server_config = api_server_config
		self.status_dict = status_dict
		self.last_data = last_data
		self.display_data = display_data
		self.transfer_queue = transfer_queue
		self.debug = debug

		self.profile = profile

	def run(self):

		file_logger.info('Started GUIThread')

		template_folder = dirname(dirname(abspath(__file__))) + '/templates/'
		app = Flask(__name__, template_folder=template_folder)
		app.debug = False
		app.use_reloader = False

		@app.route('/')
		def index():
			api_server_status = ''
			start_date = datetime.now()
			devices = []

			for uid, device in self.status_dict.items():
				devices.append({
					'uid': uid,
					'system_code': device['system_code'],
					'port': device['port'],
					'check_date': device['check_date'].strftime("%d/%m/%Y %H:%M:%S"),
					'status': 'OK' if time.time() - device['check_date'].timestamp() < 30 else 'Error',
					'last_data': self.last_data[device['system_code']] if device['system_code'] in self.last_data else {}
				})

			for uid, system_code in self.uids.items():
				if uid not in self.status_dict and system_code != 'broadcast':
					devices.append({
						'uid': uid,
						'system_code': system_code,
						'port': 'Not detected',
						'check_date': '-',
						'status': 'Error',
						'last_data': {}
					})

			try:
				r = self.api_server_config['session'].get(
					url=self.api_server_config['protocol'] + '://' + self.api_server_config[
						'host'] + '/public/api/farm_commands',
					params={
						'organization_group.code': self.api_server_config['licence_key'],
						'sent_date[gte]': int(datetime.now().timestamp())
					},
					timeout=10
				)
				api_server_status = 'OK'
			except Exception as e:
				file_logger.error(e)
				api_server_status = 'Error'

			return render_template(
				'index.html',
				check_date=start_date.strftime("%d/%m/%Y %H:%M:%S"),
				app_host=self.api_server_config['host'],
				app_check_date=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
				app_status=api_server_status,
				devices=devices,
				display_data=self.display_data
			)

		@app.route('/open_doors')
		def open_doors():

			message, hexa = TLVMessage.createTLVCommandFromJson(
				self.broadcast_uid, 'door_closed', 0
			)
			self.transfer_queue.put(message)

			return {'success': True}

		app.run(host='127.0.0.1', port=8080)
		# serve(app, host='127.0.0.1', port=8080)
