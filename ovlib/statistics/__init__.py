from ovirtsdk4.types import Statistic, Value
from ovirtsdk4.services import StatisticService, StatisticsService
from ovirtsdk4.writers import StatisticWriter, ValueWriter

from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

@wrapper(writer_class=StatisticWriter,
         type_class=Statistic,
         service_class=StatisticService,
         other_attributes=['values', 'kind', 'unit'])
class StatisticWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=ValueWriter,
         type_class=Value,
         other_attributes=['datum', 'detail'])
class ValueWrapper(ObjectWrapper):
    pass


@wrapper(service_class=StatisticsService)
class StatisticsWrapper(ListObjectWrapper):
    pass
