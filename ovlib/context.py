import pycurl
from configparser import ConfigParser
from enum import IntEnum

import ovirtsdk4

import ovlib
from ovlib.system import SystemWrapper

from six.moves.urllib.parse import urljoin


class CurlDebugType(IntEnum):
    TEXT = 1
    HEADER = 2
    DATA = 4
    SSL = 8


class ConfigurationError(Exception):
    def __init__(self, value):
        super(Exception, self).__init__(value)
        self.error_message = value

    def __str__(self):
        return self.value.__str__


class Context(object):
    # The api settings that store boolean values
    booleans = frozenset(['debug', 'insecure', 'kerberos'])

    api_connect_settings = {
        'url': None,
        'username': None,
        'password': None,
        'ca_file': '/etc/pki/ovirt-engine/ca.pem',
        'insecure': False,
        'kerberos': None,
        'debug': False,
        'log': None,
    }

    def __init__(self, config_file=None, **kwargs):
        super(Context, self).__init__()
        self.connected = False
        self.api = None

        config = ConfigParser()
        if config_file is not None:
            config.read(config_file, encoding='utf-8')

        config_api = {}
        config_logging = {}
        config_kerberos = {}

        if len(config.sections()) != 0:
            for (k, v) in config.items("api"):
                config_api[k] = v

            if config.has_section('logging'):
                config_logging = {k: v for k, v in config.items('logging')}

            if config.has_section('kerberos'):
                config_kerberos = {k: v for k,v in config.items('kerberos')}

        for attr_name in list(Context.api_connect_settings.keys()):
            if attr_name in kwargs:
                self.api_connect_settings[attr_name] = kwargs.pop(attr_name)
                # given in the command line
            elif attr_name in config_api:
                # given in the config file
                self.api_connect_settings[attr_name] = config_api[attr_name]
                if attr_name in Context.booleans:
                    self.api_connect_settings[attr_name] = config.getboolean('api', attr_name)

        if config_kerberos.get('keytab', None) is not None:
            import gssapi
            import os

            ccache = config_kerberos.get('ccache', None)
            keytab = config_kerberos.get('keytab', None)
            kname = config_kerberos.get('principal', None)
            if kname is not None:
                kname = gssapi.Name(kname)

            gssapi.creds.Credentials(name=kname, usage='initiate', store={'ccache': ccache, 'client_keytab': keytab})
            os.environ['KRB5CCNAME'] = ccache
            if self.api_connect_settings['kerberos'] is None:
                self.api_connect_settings['kerberos'] = True

        if self.api_connect_settings['url'] == None:
            raise ConfigurationError('incomplete configuration, oVirt url not found')
        if self.api_connect_settings['username'] is None and self.api_connect_settings['kerberos'] is None:
            raise ConfigurationError('not enought authentication informations')

        if config_logging.get('filters', None) is not None:
            self.filter = 0
            filters = [x.strip() for x in config_logging['filters'].split(',')]
            for f in filters:
                self.filter |= CurlDebugType[f.upper()]

        # ovirt-sdk4 want's a logger, we don't care
        if self.api_connect_settings['debug']:
            self.api_connect_settings['log'] = True


    def connect(self):
        self.api = ovirtsdk4.Connection(**self.api_connect_settings)
        # Try to ensure that connexion is good
        self.api.authenticate()
        if self.api_connect_settings['debug'] and self.api_connect_settings['log'] is True:
            self.api._curl_debug = self._curl_debug

        self.follow_link = self.api.follow_link
        self.connected = True

        # Generated all the needed accessors for root services, as defined using dispatchers
        for (dispatcher_name, dispatcher_wrapper) in list(ovlib.dispatchers.items()):
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

        # The first replace remove the root of ovirt location
        # The second replace is to remove the first / in the path
        # The str ensure that service_path is a str, not a unicode in python 2
        service_path = str(absolute_href.replace(self.api.url, "").replace("/", "", 1))

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
        text = data.decode('utf_8', errors='replace') if type(data) == bytes else str(data)

        # raw binary, ensure they are restricted to ascii subset, and don't split on lf or cr
        if debug_type == pycurl.INFOTYPE_SSL_DATA_IN or debug_type == pycurl.INFOTYPE_SSL_DATA_OUT:
            lines = [text.encode('ascii', errors='replace')]
        else:
            lines = [x for x in text.replace('\r\n', '\n').split('\n') if len(x) > 0]

        #print(type(data), type(text))
        # Split the debug data into lines and send a debug message for
        # each line:

        for line in lines:
            print("%s%s" % (prefix,line))

