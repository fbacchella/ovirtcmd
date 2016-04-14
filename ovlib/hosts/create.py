import time

import ovlib.verb
from ovirtsdk.xml import params

class Create(ovlib.verb.Verb):
    verb = "create"

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="VM name", default=None)

    def validate(self):
        return True

    def execute(self, *args, **kwargs):
        kwargs['cluster'] = self.api.clusters.get(name=kwargs.pop('cluster', 'Default'))

        kwargs['ssh'] = params.SSH(authentication_method='publickey')

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
            power_management_info['agents'] = params.Agents()
            power_management_info['agents'].add_agent(params.Agent(**agent_info))
            kwargs['power_management'] = params.PowerManagement(**power_management_info)
        self.broker = self.contenaire.add(params.Host(**kwargs))

