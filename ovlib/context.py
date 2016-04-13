from ovirtsdk.api import API
import ConfigParser

# The api settings that store boolean values
booleans = frozenset(['debug', 'insecure'])

class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = "missing configuration setting %s in api section" % value

    def __str__(self):
        return repr(self.value)

class Context(object):
    url = None
    username = None
    password = None
    debug = False
    ca_file = '/etc/pki/ovirt-engine/ca.pem'
    insecure = False

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

        for attr_name in ('url', 'username', 'password', 'debug', 'ca_file', 'insecure'):
            if attr_name in kwargs:
                # given in the command line
                setattr(self, attr_name, kwargs[attr_name])
            elif attr_name in config_api:
                # given in the config file
                value = config_api[attr_name]
                if attr_name in booleans:
                    value = config.getboolean('api', attr_name)
                setattr(self, attr_name, value)
            elif getattr(self, attr_name) is None:
                # was not given at all, and no default value
                raise ConfigurationError(attr_name)


    def connect(self):
        self.api = API(url=self.url, username = self.username, password=self.password,
                       debug=self.debug, ca_file=self.ca_file, insecure = self.insecure)
        self.connected = True

    def disconnect(self):
        if self.connected:
            self.api.disconnect()
