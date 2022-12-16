from data_persisters.data_persister import DataPersister

class PmDataPersister(DataPersister):

	def getValue(self):
		return float(self.value) / 10