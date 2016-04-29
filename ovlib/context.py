from ovirtsdk.api import API
import ConfigParser

# The api settings that store boolean values
booleans = frozenset(['debug', 'insecure', 'kerberos'])

class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = "missing configuration setting %s in api section" % value

    def __str__(self):
        return repr(self.value)

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

    def connect(self):
        self.api = API(**self.api_connect_settings)
        self.connected = True

    def disconnect(self):
        if self.connected:
            self.api.disconnect()
