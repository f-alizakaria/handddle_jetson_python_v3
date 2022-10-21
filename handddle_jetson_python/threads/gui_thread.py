import threading
import time
from os.path import dirname, abspath
from flask import Flask, render_template
from datetime import datetime

import socketio

from messages.tlv_message import TLVMessage
from waitress import serve

from lib.logging_service import LoggingService
from lib.utils import send_message


##################
# Smart Farm GUI #
##################


class GUIThread(threading.Thread):
    def __init__(self, se, master, slaves, profile, broadcast, socket_server_config, status_dict, last_data, display_data,
                 debug, gui_host, gui_port):
        threading.Thread.__init__(self)

        self.se = se
        self.broadcast_uid = broadcast['uid']
        self.uids = master['system_codes'] if profile == 'master' else slaves[0]['system_codes']
        self.socket_server_config = socket_server_config
        self.status_dict = status_dict
        self.last_data = last_data
        self.display_data = display_data
        self.debug = debug
        self.logger = LoggingService('gui').getLogger()
        self.gui_host = gui_host
        self.gui_port = gui_port
        self.profile = profile

        self.sio = socketio.Client()
        self.socket_server_config = socket_server_config
        self.event_header_for_app = self.socket_server_config['event']

    def run(self):

        self.logger.info('Started GUIThread')

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
                    'last_data': self.last_data[device['system_code']] if device[
                                                                              'system_code'] in self.last_data else {}
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
                auth = {
                    'client': 'python',
                    'token': self.socket_server_config['token']
                }

                self.sio.connect(self.socket_server_config['protocol'] + '://' + self.socket_server_config['host'],
                                 auth=auth,
                                 socketio_path=self.socket_server_config['path'],
                                 wait=True,
                                 wait_timeout=5)

            except socketio.exceptions.ConnectionError:
                self.logger.error('Unable to connect to socket server')
            except Exception as e:
                self.logger.error(e)

            return render_template(
                'index.html',
                check_date=start_date.strftime("%d/%m/%Y %H:%M:%S"),
                app_host=self.socket_server_config['host'],
                app_check_date=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                app_status='OK' if self.sio.connected else 'Error',
                devices=devices,
                display_data=self.display_data
            )

        @app.route('/open_doors')
        def open_doors():

            message, hexa = TLVMessage.createTLVCommandFromJson(
                self.broadcast_uid, 'door_closed', 0
            )
            send_message(se=self.se, message=message)

            return {'success': True}

        app.run(host=self.gui_host, port=self.gui_port)
    # serve(app, host=self.gui_host, port=self.gui_port)
