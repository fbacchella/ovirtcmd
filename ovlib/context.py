import pycurl
import ConfigParser
from enum import IntEnum

import ovirtsdk4

import ovlib
from ovlib.system import SystemWrapper

from urlparse import urljoin

# The api settings that store boolean values
booleans = frozenset(['debug', 'insecure', 'kerberos'])


class CurlDebugType(IntEnum):
    TEXT = 1
    HEADER = 2
    DATA = 4
    SSL = 8


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
        'ca_file': '/etc/pki/ovirt-engine/ca.pem',
        'insecure': False,
        'kerberos': False,
        'debug': False,
        'log': None,
    }

    def __init__(self, config_file=None, **kwargs):
        super(Context, self).__init__()
        self.connected = False
        self.api = None

        config = ConfigParser.SafeConfigParser()
        if config_file is not None:
            config.readfp(open(config_file))

        config_api = {}
        config_logging = {}
        if len(config.sections()) != 0:
            for (k, v) in config.items("api"):
                config_api[k] = v

            for (k, v) in config.items("logging"):
                config_logging[k] = v

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

        if config_logging.get('filters', None) is not None:
            self.filter = 0
            filters = map(lambda x: x.strip(), config_logging['filters'].split(','))
            for f in filters:
                self.filter |= CurlDebugType[f.upper()]


    def connect(self):
        self.api = ovirtsdk4.Connection(**self.api_connect_settings)
        if self.api_connect_settings['debug'] and self.api_connect_settings['log'] is None:
            self.api._curl.setopt(pycurl.VERBOSE, 1)
            self.api._curl.setopt(pycurl.DEBUGFUNCTION, self._curl_debug)

        self.follow_link = self.api.follow_link
        self.connected = True

        # Generated all the needed accessors for root services, as defined using dispatchers
        for (dispatcher_name, dispatcher_wrapper) in ovlib.dispatchers.items():
            if hasattr(dispatcher_wrapper, 'list_wrapper') and hasattr(dispatcher_wrapper.list_wrapper, 'service_root'):
                services_name = dispatcher_wrapper.list_wrapper.service_root
                if not hasattr(self, services_name):
                    setattr(self, services_name, dispatcher_wrapper.list_wrapper(self))
        # needed because there is no list generator for system
        setattr(self, 'system', SystemWrapper(self))

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

    def _curl_debug(self, debug_type, data):
        """
        This is the implementation of the cURL debug callback.
        """

        prefix = {pycurl.INFOTYPE_TEXT: '   ' if CurlDebugType.TEXT & self.filter else False,
                  pycurl.INFOTYPE_HEADER_IN: '<  ' if CurlDebugType.HEADER & self.filter else False,
                  pycurl.INFOTYPE_HEADER_OUT: '>  ' if CurlDebugType.HEADER & self.filter else False,
                  pycurl.INFOTYPE_DATA_IN: '<< ' if CurlDebugType.DATA & self.filter else False,
                  pycurl.INFOTYPE_DATA_OUT: '>> ' if CurlDebugType.DATA & self.filter else False,
                  pycurl.INFOTYPE_SSL_DATA_IN: '<S ' if CurlDebugType.SSL & self.filter else False,
                  pycurl.INFOTYPE_SSL_DATA_OUT: '>S ' if CurlDebugType.SSL & self.filter else False
                  }[debug_type]
        if prefix is False:
            return

        # Some versions of PycURL provide the debug data as strings, and
        # some as arrays of bytes, so we need to check the type of the
        # provided data and convert it to strings before trying to
        # manipulate it with the "replace", "strip" and "split" methods:
        if not debug_type == pycurl.INFOTYPE_SSL_DATA_IN and not pycurl.INFOTYPE_SSL_DATA_OUT:
            text = data.decode('utf-8') if type(data) == bytes else data
        else:
            text = data.decode('string_escape') if type(data) == bytes else data

        # Split the debug data into lines and send a debug message for
        # each line:
        lines = filter (lambda x: len(x) > 0, text.replace('\r\n', '\n').split('\n'))
        for line in lines:
            print "%s%s" % (prefix,line)

