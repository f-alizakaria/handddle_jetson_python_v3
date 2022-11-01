import logging
from logging.handlers import TimedRotatingFileHandler
from os import path as osp
from pathlib import Path


class LoggingService:
    config = None

    def __init__(self, name):

        if LoggingService.config is None:
            raise Exception('Logging configuration not loaded.')

        Path(LoggingService.config['directory']).mkdir(parents=True, exist_ok=True)

        # Used to write logs to different files
        self.filename = osp.join(LoggingService.config['directory'], name + '.log')

        # Define file and console handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
        self.file_handler = TimedRotatingFileHandler(self.filename, when='midnight', interval=1, backupCount=7)
        self.file_handler.setFormatter(formatter)

        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(formatter)

        # Create the logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(eval('logging.' + LoggingService.config['level']))
        self.logger.addHandler(self.file_handler)
        if LoggingService.config['console']:
            self.logger.addHandler(self.console_handler)
        self.logger.propagate = False

    def getLogger(self):
        return self.logger
