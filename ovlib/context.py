import ovirtsdk4
import ConfigParser
import ovlib
import types

from urlparse import urljoin

# The api settings that store boolean values
booleans = frozenset(['debug', 'insecure', 'kerberos'])


class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = "missing configuration setting %s in api section" % value

    def __str__(self):
        return repr(self.value)


class ObjectExecutor(object):

    def __init__(self, context, object_ctxt, object_options=None, broker=None):
        super(ObjectExecutor, self).__init__()
        self.object_ctxt = object_ctxt
        self.context = context
        self.object_options = object_options
        self.broker = broker
        if self.object_ctxt.api is None:
            self.object_ctxt.api = self.context.api

        if self.broker is None and len(object_options) > 0:
            self.broker = self.object_ctxt.get(**self.object_options)
            if self.broker is None:
                raise ovlib.OVLibErrorNotFound("object not found: %s %s" % (self.object_ctxt.api_attribute, self.object_options) )

        for (verb_name, verb_class) in self.object_ctxt.verbs.items():
            setattr(self, verb_name, self._do_runner(verb_class))

    def _do_runner(self, verb_class):
        def executor(*args, **kwargs):
            cmd = verb_class(self.context.api, self.broker)
            (cmd, executed) = self.object_ctxt.execute_phrase(cmd, object_options=self.object_options, verb_options=kwargs, verb_args=args)
            if type(executed) in ovlib.dispatchers_by_class:
                return ObjectExecutor(self.context,
                                      ovlib.dispatchers_by_class[type(executed)],
                                      None,
                                      executed)
            elif isinstance(executed, types.GeneratorType):
                def iterate():
                    for i in executed:
                        if type(i) in ovlib.dispatchers_by_class:
                            yield ObjectExecutor(self.context,
                                                 ovlib.dispatchers_by_class[type(i)],
                                                 None,
                                                 i)
                        else:
                            yield i
                return iterate()
            else:
                return executed
        return executor

    def get(self, source, name=None, id=None):
        if isinstance(source, str) or isinstance(source, unicode):
            source = getattr(self.broker, source)
        if isinstance(name, ObjectExecutor):
            found = name.broker
        #elif isinstance(name, Base):
        #    found = name
        #elif isinstance(id, ObjectExecutor):
        #    found = id.broker
        #elif isinstance(id, Base):
        #    found = id
        else:
            found = source.get(name=name, id=id)
        if found is None:
            return None
        else:
            if type(found) in ovlib.dispatchers_by_class:
                return ObjectExecutor(self.context, ovlib.dispatchers_by_class[type(found)], broker=found)
            else:
                raise ovlib.OVLibError("unsupported ressource: %s" % found.__class__)

import logging
logging.basicConfig(level=logging.DEBUG, filename='example.log')

class Context(object):
    api_connect_settings = {
        'url': None,
        'username': None,
        'password': None,
        'ca_file': '/etc/pki/ovirt-engine/ca.pem',
        'insecure': False,
        'kerberos': False,
        #'debug': True,
        #'log': logging.getLogger(),
    }

    connected = False
    api = None

    def __init__(self, config_file=None, **kwargs):
        super(Context, self).__init__()
        config = ConfigParser.SafeConfigParser()
        if config_file is not None:
            config.readfp(open(config_file))

        config_api = {}
        if len(config.sections()) != 0:
            for (k, v) in config.items("api"):
                config_api[k] = v

        for attr_name in self.api_connect_settings.keys():
            if attr_name in kwargs:
                self.api_connect_settings[attr_name] = kwargs.pop(attr_name)
                # given in the command line
            elif attr_name in config_api:
                # given in the config file
                self.api_connect_settings[attr_name] = config_api[attr_name]
                if attr_name in booleans:
                    self.api_connect_settings[attr_name] = config.getboolean('api', attr_name)

        for (object_name, object_context) in ovlib.dispatchers.items():
            setattr(self, object_name, self._do_getter(object_context))

        if self.api_connect_settings['url'] == None:
            raise ConfigurationError('incomplete configuration, oVirt url not found')
        if self.api_connect_settings['username'] == None and self.api_connect_settings['kerberos'] == None:
            raise ConfigurationError('not enought authentication informations')


    def connect(self):
        self.api = ovirtsdk4.Connection(**self.api_connect_settings)
        self.connected = True

    def disconnect(self):
        if self.connected:
            self.api.close()

    def _do_getter(self, object_context):
        def getter(**kwargs):
            try:
                return ObjectExecutor(self, object_context, object_options=kwargs)
            except ovlib.OVLibErrorNotFound:
                return None
        return getter

    def resolve_service_href(self, href):
        absolute_href = urljoin(self.api.url, href)
        # the second replace is to remove the first / in the path
        service_path = absolute_href.replace(self.api.url, "").replace("/", "", 1)
        new_service = self.api.service(service_path)

        return new_service


