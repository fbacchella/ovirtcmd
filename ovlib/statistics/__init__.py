import time
import ovlib.verb

from ovirtsdk4 import List
from ovirtsdk4.types import Statistic, Value
from ovirtsdk4.services import StatisticService, StatisticsService
from ovirtsdk4.writers import StatisticWriter, ValueWriter

from ovlib import wrapper, ObjectWrapper, ListObjectWrapper

@wrapper(writer_class=StatisticWriter,
         type_class=Statistic,
         service_class=StatisticService,
         other_attributes=['values', 'kind'])
class StatisticWrapper(ObjectWrapper):
    def __init__(self, api,  service=None, type=None):
        super(StatisticWrapper, self).__init__(api, type=type, service=service)
        self.values = self.type.values


@wrapper(writer_class=ValueWriter,
         type_class=Value,
         other_attributes=['datum', 'detail'])
class ValueWrapper(ObjectWrapper):
    pass


@wrapper(service_class=StatisticsService)
class StatisticsWrapper(ListObjectWrapper):
    pass
