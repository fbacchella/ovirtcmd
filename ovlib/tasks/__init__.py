import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import JobStatus, Job
from ovirtsdk4.writers import JobWriter
from ovirtsdk4.services import JobsService, JobService


@wrapper(service_class=JobsService, service_root="jobs")
class JobsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=JobService, type_class=Job, writer_class=JobWriter, other_attributes=[])
class JobWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="task", wrapper=JobWrapper, list_wrapper=JobsWrapper)
class JobDispatcher(Dispatcher):
    pass

@command(JobDispatcher)
class JobList(ovlib.verb.List):
    pass


@command(JobDispatcher)
class JobExport(ovlib.verb.XmlExport):
    pass

