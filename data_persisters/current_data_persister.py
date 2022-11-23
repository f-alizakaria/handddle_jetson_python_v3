from data_persisters.data_persister import DataPersister


class CurrentDataPersister(DataPersister):

	def getValue(self):
		return float(self.value) / 100