from ovirtsdk.api import API
import ConfigParser
import ovlib
import types

# The api settings that store boolean values
booleans = frozenset(['debug', 'insecure', 'kerberos'])

class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = "missing configuration setting %s in api section" % value

    def __str__(self):
        return repr(self.value)

class Object_Executor(object):

    def __init__(self, context, object_ctxt, object_options=None, broker=None):
        super(Object_Executor, self).__init__()
        self.object_ctxt = object_ctxt
        self.context = context
        self.object_options = object_options
        self.broker = broker
        if self.object_ctxt.api is None:
            self.object_ctxt.api = self.context.api

        #print self.broker
        #print self.object_options
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
            if type(executed) in ovlib.objects_by_class:
                return Object_Executor(self.context,
                                       ovlib.objects_by_class[type(executed)],
                                       None,
                                       executed)
            elif isinstance(executed, types.GeneratorType):
                def iterate():
                    for i in executed:
                        if type(i) in ovlib.objects_by_class:
                            yield Object_Executor(self.context,
                                                  ovlib.objects_by_class[type(i)],
                                                  None,
                                                  i)
                        else:
                            yield i
                return iterate()
            else:
                return executed
        return executor

class Context(object):
    api_connect_settings = {
        'url': None,
        'username': None,
        'password': None,
        'debug': False,
        'ca_file': '/etc/pki/ovirt-engine/ca.pem',
        'insecure': False,
        'kerberos': False,
    }

    connected = False
    api = None

    def __init__(self, **kwargs):
        super(Context, self).__init__()

        config = ConfigParser.SafeConfigParser()
        config_path = kwargs.pop("config_file", None)
        if config_path is not None:
            config.readfp(open(config_path))

        config_api = {}
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

        for (object_name, object_context) in ovlib.objects.items():
            setattr(self, object_name, self._do_getter(object_context))

    def connect(self):
        self.api = API(**self.api_connect_settings)
        self.connected = True

    def disconnect(self):
        if self.connected:
            self.api.disconnect()

    def _do_getter(self, object_context):
        def getter(**kwargs):
            try:
                return Object_Executor(self, object_context, object_options=kwargs)
            except ovlib.OVLibErrorNotFound:
                return None
        return getter

