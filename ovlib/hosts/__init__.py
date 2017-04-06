import time
import ovlib.verb
from ovlib import ObjectContext, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.errors import RequestError
from ovirtsdk.infrastructure.brokers import Host

import create
import bond

class_ref = []

@add_command(class_ref)
class Statistics(ovlib.verb.Statistics):
    pass


@add_command(class_ref)
class List(ovlib.verb.List):
    pass


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass


@add_command(class_ref)
class Delete(ovlib.verb.Delete):

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        self.broker.delete()


@add_command(class_ref)
class Maintenance(ovlib.verb.Verb):
    verb = "maintenance"

    def fill_parser(self, parser):
        parser.add_option("-r", "--reason", dest="reason", help="Reason for maintenance", default=None)

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            action = params.Action()
            if kwargs.get('reason', None) is not None:
                action.reason = kwargs.pop('reason')
            self.broker.deactivate(action)
            self.wait_for("maintenance")
        return True


@add_command(class_ref)
class Activate(ovlib.verb.Verb):
    verb = "activate"

    def execute(self, *args, **kwargs):
        if self.broker.status.state == "maintenance":
            self.broker.activate()
            self.wait_for("up")
        return True


@add_command(class_ref)
class DiscoverDomain(ovlib.verb.Verb):
    verb = "discoverdomain"

    def execute(self, *args, **kwargs):
        return self.broker.unregisteredstoragedomainsdiscover()

    def to_str(self, value):
        return self._export(value.storage_domains)

def get_uptime(host):
    uptime_stat = host.statistics.get(name="boot.time")
    return uptime_stat.values.get_value()[0].get_datum()


@add_command(class_ref)
class ReInstall(ovlib.verb.Verb):
    """Broken, do not use"""
    verb = "reinstall"

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


@add_command(class_ref)
class Reboot(ovlib.verb.Verb):
    """Broken, do not use"""
    verb = "reboot"

    def execute(self, *args, **kwargs):
        last_boot = get_uptime(self.broker)

        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        self.broker.fence(params.Action(fence_type='restart'))
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


@add_command(class_ref)
class Upgrade(ovlib.verb.Delete):
    verb = "upgrade"

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


class_ref.append(create.Create)
class_ref.append(bond.Bond)

oc = ObjectContext(api_attribute ="hosts", object_name ="host", commands = class_ref, broker_class=Host)
