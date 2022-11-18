import threading
import time
import requests
import os
from messages.tlv_message import TLVMessage

from lib.logging_service import LoggingService
from lib.utils import send_message


import socketio


################################
# Read received commands files #
################################


class SendCommandsThread(threading.Thread):
    def __init__(self, thread, master, slaves, profile, se, socket_server_config, debug, broadcast):
        threading.Thread.__init__(self)
        self.thread = thread
        self.master = master
        self.slaves = slaves
        self.se = se
        self.socket_server_config = socket_server_config
        self.debug = debug
        self.messages_to_send = []

        self.last_check_date = int(time.time())

        self.logger = LoggingService('commands').getLogger()

        self.profile = profile

        self.broadcast_uid = broadcast['uid']

        if self.profile == "master":
            self.socket_server = SocketServerCommands(socket_server_config=self.socket_server_config,
                                                  reception_callback=self.handleCommand, logger=self.logger)

    def run(self):

        self.logger.info('Started SendCommandsThread')

        if self.profile == "master":
            self.socket_server.server_socket_callbacks()
            self.socket_server.init_socket_server_connection()
        else:
            while True:
                time.sleep(5)

    def handleCommand(self, command):
        try:
            self.last_check_date = int(time.time())

            # Messages ready to be sent to all STM32
            self.messages_to_send = []

            if self.profile == 'master':
                # Regular command
                if command['system_code'] in self.master['system_codes'] or command['system_code'] == 'broadcast':

                    if command['system_code'] == 'broadcast':
                        message, hexa = TLVMessage.createTLVCommandFromJson(
                            self.broadcast_uid, command['action'], 0
                        )

                        # Here, we send stop buzzer command to all STM with 'T' in their system_code
                        for slave in self.slaves:
                            for system_code in list(slave['system_codes'].keys()):
                                command['system_code'] = system_code
                                self.thread.sendCommandToSlave(command)
                    else:
                        message, hexa = TLVMessage.createTLVCommandFromJson(self.master['system_codes'][command['system_code']],
                                                                            command['action'],
                                                                            int(command['data']))
                    send_message(se=self.se, message=message)
                    self.logger.info('>>> Sent command: {:040x}'.format(int.from_bytes(message, byteorder='big')))

                    # Test - Uncomment this line to check if the message is well formated
                    # self.logger.info(TLVMessage(io.BytesIO(message)))

                else:

                    [self.thread.sendCommandToSlave(command) for slave in self.slaves
                        if command['system_code'] in slave['system_codes']]

        except requests.exceptions.ConnectionError as e:
            self.logger.error('The application is not connected to internet. Retrying...')

        except requests.exceptions.ReadTimeout as e:
            self.logger.error(f'The application could not reach the web server. Retrying...\nDetails: {e}')

        except Exception as e:
            self.logger.critical(f'ERROR: An error occured while sending commands : {e}')


class SocketServerCommands:
    sio = socketio.Client()

    def __init__(self, socket_server_config, reception_callback, logger):

        # Socket
        self.socket_server_config = socket_server_config
        self.reception_callback = reception_callback
        self.logger = logger

        self.event_header_for_app = self.socket_server_config['event']

        self.sio = socketio.Client()

    def init_socket_server_connection(self):
        while not self.sio.connected:
            try:
                auth = {
                    'client': 'python',
                    'token': self.socket_server_config['token']
                }

                self.sio.connect(self._get_socket_server_url(),
                                 auth=auth,
                                 socketio_path=self.socket_server_config['path'],
                                 wait=True,
                                 wait_timeout=5)

                # Allows to not closed the connection and wait until the connection with the server ends
                self.sio.wait()

            except socketio.exceptions.ConnectionError:
                self.logger.error('Unable to connect to socket server')
                time.sleep(5)

    def server_socket_callbacks(self):
        # Function invoked automatically when the connection with the server is established
        @self.sio.event
        def connect():
            self.logger.info('[SOCKET] Socket connected')

        # Handling connection message event
        @self.sio.on('connection')
        def reveived_connection_message():
            self.logger.info('[SOCKET] Socket connected [ACK]')

        # Handling other connection message event
        @self.sio.on('other connection')
        def reveived_connection_message():
            self.logger.info('[SOCKET] New connection')

        # Handling receiving command event
        @self.sio.on(self.socket_server_config['event'])
        def received_command(data):
            self.logger.info(f'[SOCKET] Command: {data}')
            self.reception_callback(data)

        # Handling disconnection event
        @self.sio.event
        def disconnect():
            self.logger.info('[SOCKET] Socket disconnected from socket server')

    def _get_socket_server_url(self):
        return self.socket_server_config['protocol'] + '://' + self.socket_server_config['host']
