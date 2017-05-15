import ovirtsdk4
import ConfigParser
import ovlib

from urlparse import urljoin

# The api settings that store boolean values
booleans = frozenset(['debug', 'insecure', 'kerberos'])


class ConfigurationError(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = "missing configuration setting %s in api section" % value

    def __str__(self):
        return repr(self.value)


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

        if self.api_connect_settings['url'] == None:
            raise ConfigurationError('incomplete configuration, oVirt url not found')
        if self.api_connect_settings['username'] == None and self.api_connect_settings['kerberos'] == None:
            raise ConfigurationError('not enought authentication informations')

    def connect(self):
        self.api = ovirtsdk4.Connection(**self.api_connect_settings)
        self.follow_link = self.api.follow_link
        self.connected = True
        for (dispatcher_name, dispatcher_wrapper) in ovlib.dispatchers.items():
            if hasattr(dispatcher_wrapper, 'list_wrapper') and hasattr(dispatcher_wrapper.list_wrapper, 'service_root'):
                services_name = dispatcher_wrapper.list_wrapper.service_root
                if not hasattr(self, services_name):
                    setattr(self, services_name, dispatcher_wrapper.list_wrapper(self))

    def disconnect(self):
        if self.connected:
            self.api.close()

    def resolve_service_href(self, href):
        absolute_href = urljoin(self.api.url, href)
        # the second replace is to remove the first / in the path
        service_path = absolute_href.replace(self.api.url, "").replace("/", "", 1)
        new_service = self.api.service(service_path)
        return new_service

    def service(self, path):
        return self.api.service(path)

    def wrap(self, sdk_object):
        return ovlib.ObjectWrapper.make_wrapper(self, sdk_object)


