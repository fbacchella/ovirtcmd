import time
import ovlib.verb

from ovirtsdk4.types import Host, HostStatus, HostNic, NetworkAttachment, IpAddressAssignment
from ovirtsdk4.services import HostService, HostsService, NetworkAttachmentService, NetworkAttachmentsService, HostNicsService, HostNicService
from ovirtsdk4.writers import HostWriter, HostNicWriter, NetworkAttachmentWriter, IpAddressAssignmentWriter

from ovlib import wrapper, ObjectWrapper, ListObjectWrapper, Dispatcher, dispatcher, command


@wrapper(writer_class=IpAddressAssignmentWriter,
         type_class=IpAddressAssignment)
class IpAddressWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=HostNicWriter,
         service_class=HostNicService,
         type_class=HostNic)
class HostNicWrapper(ObjectWrapper):
    pass


@wrapper(service_class=HostNicsService)
class HostNicsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=NetworkAttachmentsService)
class NetworkAttachmentsWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=NetworkAttachmentWriter,
         type_class=NetworkAttachment,
         service_class=NetworkAttachmentService,
         other_attributes=['ip_address_assignments', 'in_sync', 'host_nic', 'network', 'dns_resolver_configuration'])
class NetworkAttachmentWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=HostWriter,
         type_class=Host,
         service_class=HostService,
         other_methods=['deactivate', 'activate', 'fence', 'upgrade', 'upgrade_check', 'unregistered_storage_domains_discover', 'setup_networks', 'commit_net_config'],
         other_attributes=['update_available', 'network_attachments'])
class HostWrapper(ObjectWrapper):
    pass

@wrapper(service_class=HostsService, service_root = "hosts")
class HostsWrapper(ListObjectWrapper):
    pass

@dispatcher(object_name = "host", wrapper=HostWrapper, list_wrapper=HostsWrapper)
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


@command(HostDispatcher, verb='upgradecheck')
class UpgradeCheck(ovlib.verb.Verb):

    def execute(self, reason=None, async=False, *args, **kwargs):
        return self.object.upgrade_check()


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
        return self.object.unregistered_storage_domains_discover()

    def to_str(self, value):
        for i in value:
            return i.export()

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

from datetime import datetime
@command(HostDispatcher, verb='upgrade')
class Upgrade(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for maintenance state", default=False, action='store_true')

    def execute(self, async=False):
        #self.object.upgrade_check()
        if self.object.update_available:
            if self.object.status != HostStatus.MAINTENANCE:
                print "%s maintenance state" % str(datetime.now())
                self.object.deactivate(reason='For upgrade', async=True)
                self.object.wait_for(HostStatus.MAINTENANCE)
            print "%s start upgrade" % str(datetime.now())
            self.object.upgrade(async=False)
            print "%s upgrade launched" % str(datetime.now())
            if not async:
                self.object.wait_for(HostStatus.INSTALLING)
                print "%s upgrade notified" % str(datetime.now())
                # Upgrade is always async, so needs to wait for a maintenance status.
                self.object.wait_for(HostStatus.MAINTENANCE)
                print "%s upgrade finished" % str(datetime.now())

            return True
        else:
            return None

        def to_str(self, value):
            print isinstance(value, bool)
            if isinstance(value, bool) and value:
                return "Upgraded succeeded"
            elif value is None:
                return "Upgraded not needed"
            else:
                return value





import create
import bond