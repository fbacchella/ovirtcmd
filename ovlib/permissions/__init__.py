import ovlib.verb
from ovlib import Dispatcher, command
from ovirtsdk.infrastructure.brokers import User, Group
from ovirtsdk.xml import params


class_ref_users = []


@command(class_ref_users)
class List(ovlib.verb.List):
    template = "'%(name)s %(last_name)s' %(id)s"


@command(class_ref_users)
class XmlExport(ovlib.verb.XmlExport):
    pass


oc_user = Dispatcher(api_attribute="users", object_name="user", commands=class_ref_users, broker_class=User)


class_ref_domain = []


@command(class_ref_domain)
class List(ovlib.verb.List):
    pass


@command(class_ref_domain)
class XmlExport(ovlib.verb.XmlExport):
    pass


oc_domain = Dispatcher(api_attribute="domains", object_name="domain", commands=class_ref_domain, broker_class=User)


class_ref_groups = []


@command(class_ref_groups)
class List(ovlib.verb.List):
    pass


@command(class_ref_groups)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(class_ref_groups)
class Create(ovlib.verb.Create):
    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name")
        parser.add_option("-N", "--namespace", dest="namespace")
        parser.add_option("-d", "--domain", dest="domain")
        parser.add_option("-p", "--principal", dest="principal")
        parser.add_option("-r", "--role", dest="roles", default=[], action="append")

    def execute(self, *args, **kwargs):
        domain_info = kwargs.pop("domain", None)
        if domain_info is not None:
            kwargs['domain'] = self.get("domains", domain_info)
        group_params = params.Group(**kwargs)
        return self.contenaire.add(group_params)


oc_group = Dispatcher(api_attribute="groups", object_name="group", commands=class_ref_groups, broker_class=User)

