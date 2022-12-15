import io
from importlib import import_module

class Message:

	def __init__(self, subtype, content):

		self.subtype = subtype
		self.stream = io.BytesIO(content)


class InternalMessage(Message):

	INTERNAL_TYPES = {
		0: 'ack_general',
		1: 'ack_command',
		5: 'ack_information'
	}

	def __init__(self, subtype, content):
		super().__init__(subtype, content)

		if self.subtype not in InternalMessage.INTERNAL_TYPES.keys():
			raise Exception('Invalid internal message type: {}'.format(self.subtype))

		self.information_type = InternalMessage.INTERNAL_TYPES[self.subtype]
		self.infomation_value = int.from_bytes(self.stream.read(), byteorder='big')

	def __repr__(self):
		return '[Internal message | Information type: {} | Information value: {}]'.format(
			self.information_type, self.infomation_value
		)


class CommandMessage(Message):

	COMMAND_TYPES = {
		0: {'name': 'ack', 'values': [0, 1]},
		1: {'name': 'update_watchdog', 'values': [1]},
		2: {'name': 'force_reset', 'values': [1]},
		3: {'name': 'air_extraction', 'values': [e for e in range(100+1)]},
		4: {'name': 'temperature', 'values': [t for t in range(100+1)]},
		5: {'name': 'led_color', 'values': [l for l in range(17+1)]},
		6: {'name': 'on_off', 'values': [0, 1]},
		7: {'name': 'door_closed', 'values': [0, 1]},
		10: {'name': 'relay_off', 'values': [0, 1]},
		11: {'name': 'tare', 'values': [1]},
		12: {'name': 'get_weight', 'values': [1]},
		14: {'name': 'dehumidifier_on', 'values': [0,1]},
		15: {'name': 'sm_volume', 'values': [volume for volume in range(30+1)]},
		16: {'name': 'sm_eq', 'values': [eq for eq in range(5+1)]},
		17: {'name': 'sm_track', 'values': [track for track in range(5+1)]},
		18: {'name': 'sm_repeat', 'values': [0,1]},
		19: {'name': 'sm_simple_cmd', 'values': [1,2,3,4,5]}
	}

	def __init__(self, subtype, content):
		super().__init__(subtype, content)

		if self.subtype not in CommandMessage.COMMAND_TYPES.keys():
			raise Exception('Invalid command message type: {}'.format(self.subtype))

		self.command_name = CommandMessage.COMMAND_TYPES[self.subtype]['name']
		self.command_value = int.from_bytes(self.stream.read(), byteorder='big')

		if self.command_value not in CommandMessage.COMMAND_TYPES[self.subtype]['values']:
			raise Exception('Invalid command message "{}" with value "{}"'.format(
				self.command_name, self.command_value
			))


	def __repr__(self):
		return '[Command message | Command name: {} | Command value: {}]'.format(self.command_name, self.command_value)



class MainMessage(Message):

	DATA_TYPES = {
		0: {'name': 'led_color', 'class': 'default_data_persister'},
		1: {'name': 'relay_on', 'class': 'default_data_persister'},
		2: {'name': 'humidity', 'class': 'default_data_persister'},
		3: {'name': 'temperature', 'class': 'temperature_data_persister'},
		4: {'name': 'humidity_ext', 'class': 'default_data_persister'},
		5: {'name': 'temperature_ext', 'class': 'temperature_data_persister'},
		6: {'name': 'pm1', 'class': 'default_data_persister'},
		7: {'name': 'pm2_5', 'class': 'default_data_persister'},
		8: {'name': 'pm4', 'class': 'default_data_persister'},
		9: {'name': 'pm10', 'class': 'default_data_persister'},
		10: {'name': 'voc_index', 'class': 'default_data_persister'},
		11: {'name': 'nox_index', 'class': 'default_data_persister'},
		12: {'name': 'pm1_ext', 'class': 'default_data_persister'},
		13: {'name': 'pm2_5_ext', 'class': 'default_data_persister'},
		14: {'name': 'pm4_ext', 'class': 'default_data_persister'},
		15: {'name': 'pm10_ext', 'class': 'default_data_persister'},
		16: {'name': 'voc_index_ext', 'class': 'default_data_persister'},
		17: {'name': 'nox_index_ext', 'class': 'default_data_persister'},
		18: {'name': 'weight', 'class': 'default_data_persister'},
		19: {'name': 'pressure', 'class': 'default_data_persister'},
		20: {'name': 'door_closed', 'class': 'door_closed_data_persister'},
		21: {'name': 'embedded_electronics_current', 'class': 'current_data_persister'},
		22: {'name': 'electric_plug_current', 'class': 'current_data_persister'},
	}

	def __init__(self, subtype, content):
		super().__init__(subtype, content)

		if self.subtype not in MainMessage.DATA_TYPES.keys():
			raise Exception('Invalid main message type: {}'.format(self.subtype))

		data_class = getattr(import_module('data_persisters.' + MainMessage.DATA_TYPES[self.subtype]['class']),
			''.join(x for x in MainMessage.DATA_TYPES[self.subtype]['class'].title() if x.isalnum())
		)
		self.data = data_class(
			MainMessage.DATA_TYPES[self.subtype]['name'],
			int.from_bytes(self.stream.read(), byteorder='big')
		)

	def __repr__(self):
		return '[Main message | Data name: {} | Data value: {}]'.format(self.data.getKey(), self.data.getValue())


class SecondaryMessage(Message):

	DATA_TYPES = {
		0: 'tachy_extraction',
		1: 'ee_temperature',
	}

	def __init__(self, subtype, content):
		super().__init__(subtype, content)

		if self.subtype not in SecondaryMessage.DATA_TYPES.keys():
			raise Exception('Invalid secondary message type: {}'.format(self.subtype))

		self.data_name = SecondaryMessage.DATA_TYPES[self.subtype]
		self.data_value = int.from_bytes(self.stream.read(), byteorder='big')

	def __repr__(self):
		return '[Secondary message | Data name: {} | Data value: {}]'.format(self.data_name, self.data_value)


class ErrorMessage(Message):

	DATA_TYPES = {
		0: 'left_latch',
		1: 'right_latch',
		2: 'i2c_smart_power',
		3: 'i2c_smart_sensor_1',
		4: 'i2c_smart_sensor_2'
	}

	def __init__(self, subtype, content):
		super().__init__(subtype, content)

		if self.subtype not in ErrorMessage.DATA_TYPES.keys():
			raise Exception('Invalid error message type: {}'.format(self.subtype))

		self.data_name = ErrorMessage.DATA_TYPES[self.subtype]

	def __repr__(self):
		return '[Error message | Data name: {}]'.format(self.data_name)



class InformationMessage(Message):

	DATA_TYPES = {
		0: 'ack',
	}

	def __init__(self, subtype, content):
		super().__init__(subtype, content)

		if self.subtype not in InformationMessage.DATA_TYPES.keys():
			raise Exception('Invalid information message type: {}'.format(self.subtype))

		self.data_name = InformationMessage.DATA_TYPES[self.subtype]
		self.data_value = int.from_bytes(self.stream.read(), byteorder='big')

	def __repr__(self):
		return '[Information message | Data name: {} | Data value: {}]'.format(self.data_name, self.data_value)

