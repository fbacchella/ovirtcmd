import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, command, dispatcher, wrapper, ListObjectWrapper

from ovirtsdk4.types import Job, Step
from ovirtsdk4.writers import JobWriter, StepWriter
from ovirtsdk4.services import JobService, JobsService, StepService, StepsService


@wrapper(writer_class=StepWriter, type_class=Step, service_class=StepService)
class StepWrapper(ObjectWrapper):
    pass


@wrapper(service_class=StepsService)
class StepsWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=JobWriter, type_class=Job, service_class=JobService)
class JobWrapper(ObjectWrapper):
    pass


@wrapper(service_class=JobsService, service_root="jobs")
class JobsWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="job", wrapper=JobWrapper, list_wrapper=JobsWrapper)
class JobDispatcher(Dispatcher):
    pass


@command(JobDispatcher)
class JobList(ovlib.verb.List):
    template = "{id!s} {description!s}"
    pass


@command(JobDispatcher)
class JobExport(ovlib.verb.XmlExport):
    pass
