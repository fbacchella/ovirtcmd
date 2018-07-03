
from ovlib.verb import Create
from ovlib.hosts import HostDispatcher
from ovlib.dispatcher import command

from ovirtsdk4.types import SshAuthenticationMethod, PowerManagement, Agent

@command(HostDispatcher, verb='create')
class Create(Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="VM name", default=None)

    def execute(self, cluster, *args, **kwargs):
        self.api.generate_services()

        kwargs['cluster'] = self.api.clusters.get(name=cluster)
        kwargs['ssh'] = SshAuthenticationMethod.PUBLICKEY

        power_management_info = kwargs.pop('power_management', None)
        if power_management_info is not None:
            agent_info = power_management_info
            power_management_info = {}
            power_management_info['enabled'] = True
            power_management_info['kdump_detection'] = agent_info.pop('kdump_detection', True)
            if 'type' in agent_info:
                type = agent_info.pop('type')
                power_management_info['type_'] = type
                agent_info['type_'] = type
            power_management = PowerManagement(**power_management_info)
            power_management_info['agents'] = params.Agents()
            power_management_info['agents'].add_agent(PowerManagement(**agent_info))
            kwargs['power_management'] = power_management
        return self.contenaire.add(params.Host(**kwargs))

