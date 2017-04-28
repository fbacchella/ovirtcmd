import time
import ovlib.verb
from ovlib import Dispatcher, command
from ovirtsdk4.types import Host, GraphicsType, HostStatus
from ovirtsdk4.services import HostService, HostsService
from ovlib import wrapper, ObjectWrapper, Dispatcher, dispatcher
from ovirtsdk4.writers import HostWriter

@wrapper(writer_class=HostWriter, type_class=Host, service_class=HostService, other_methods=['deactivate', 'activate', 'fence'])
class HostWrapper(ObjectWrapper):
    pass

@wrapper(service_class=HostsService)
class HostsWrapper(ObjectWrapper):
    pass

@dispatcher(service_root = "hosts", object_name = "host", wrapper=HostWrapper)
class HostDispatcher(Dispatcher):
    pass

@command(HostDispatcher)
class Statistics(ovlib.verb.Statistics):
    pass


@command(HostDispatcher)
class List(ovlib.verb.List):
    pass


@command(HostDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(HostDispatcher)
class Delete(ovlib.verb.Delete):

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        self.broker.delete()


@command(HostDispatcher, verb='maintenance')
class Maintenance(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-r", "--reason", dest="reason", help="Reason for maintenance", default=None)
        parser.add_option("-a", "--async", dest="async", help="Don't wait for maintenance state", default=False, action='store_true')

    def execute(self, reason=None, async=False, *args, **kwargs):
        if self.object.status != HostStatus.MAINTENANCE:
            self.object.deactivate(reason=reason, async=async)
            if not async:
                self.object.wait_for(HostStatus.MAINTENANCE)
        return True


@command(HostDispatcher, verb='activate')
class Activate(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for maintenance state", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        if self.object.status == HostStatus.MAINTENANCE:
            self.object.activate()
            self.object.wait_for(HostStatus.UP)
        return True


@command(HostDispatcher, verb='discoverdomain')
class DiscoverDomain(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        return self.broker.unregisteredstoragedomainsdiscover()

    def to_str(self, value):
        return self._export(value.storage_domains)

def get_uptime(host):
    uptime_stat = host.statistics.get(name="boot.time")
    return uptime_stat.values.get_value()[0].get_datum()


@command(HostDispatcher, verb='reinstall')
class ReInstall(ovlib.verb.Verb):
    """Broken, do not use"""

    def fill_parser(self, parser):
        parser.add_option("-i", "--dont_override_iptables", dest="override_iptables", help="Automatically configure host firewall", default=True, action="store_false")

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        ssh_old_params = vars(self.broker.ssh)
        ssh_new_params = {}
        ssh_new_params['authentication_method'] = 'publickey'
        for p in ('authentication_method', 'port', 'fingerprint', 'user'):
            if p in ssh_old_params and ssh_old_params[p] is not None:
                ssh_new_params[p] = ssh_old_params[p]

        print ssh_new_params
        action = params.Action(ssh=params.SSH(**ssh_new_params),
                               host=params.Host(override_iptables=kwargs.pop('override_iptables', True)))
        self.broker.install(action)


@command(HostDispatcher, verb='reboot')
class Reboot(ovlib.verb.Verb):
    """Broken, do not use"""
    verb = ""

    def execute(self, *args, **kwargs):
        last_boot = get_uptime(self.broker)

        if self.object.status != HostStatus.MAINTENANCE:
            self.object.deactivate(reason='For reboot', async=False)
            self.object.wait_for(HostStatus.MAINTENANCE)
        self.object.fence(params.Action(fence_type='restart'))
        # needs to be activated before checking for up, otherwise it will return maintenance forever
        doactivate=True
        while doactivate:
            try:
                self.broker = self.contenaire.get(id=self.broker.id)
                current_last_boot = get_uptime(self.broker)
                print "%s %s" % (last_boot, current_last_boot)
                #self.broker.activate()
            except RequestError as e:
                print e.detail
                time.sleep(5)
        self.wait_for("up")
        return True


@command(HostDispatcher, verb='upgrade')
class Upgrade(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-i", "--image", dest="image", help="Not documented")

    def execute(self, image=None):
        action = params.Action(image=image)
        try:
            self.broker.upgrade(action)
            self.wait_finished("installing")
            return True
        except RequestError as e:
            if e.detail == 'Cannot upgrade Host. There are no available updates for the host.':
                return "upgrade not needed"
            else:
                raise e

import create
import bond