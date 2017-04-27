import time

import ovlib.verb

class Create(ovlib.verb.Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="VM name", default=None)

    def execute(self, *args, **kwargs):
        kwargs['cluster'] = self.get('clusters', kwargs.pop('cluster', None))

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
        return self.contenaire.add(params.Host(**kwargs))

