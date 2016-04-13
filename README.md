Howto install venv

    virtualenv-2.7 venv
    . ./venv/bin/activate
    pip install --upgrade pip
    pip uninstall pycurl
    PYCURL_SSL_LIBRARY=openssl easy_install pycurl
    easy_install ovirt-engine-sdk-python PyYaml
