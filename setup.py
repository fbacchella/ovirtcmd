#!/usr/bin/env python

import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "oVirtCmd",
    version = "0.0.2",
    author = "Fabrice Bacchella",
    author_email = "fabrice.bacchella@3ds.com",
    description = "Command line tool to manage oVirt.",
    license = "Apache",
    keywords = "CLI oVirt virtualization",
    install_requires=[
        # ovirt-engine-sdk-python 4.1.4 is badly broken
        ('ovirt-engine-sdk-python' '==4.1.3'), 'PyYaml', 'ipaddress', 'six', 'configparser'
    ],
    url = "https://github.com/fbacchella/ovirtcmd",
    packages=find_packages(),
    scripts=['ovcmd'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Classifier: Operating System :: OS Independent",
        "Environment :: Console",
        "Programming Language :: Python :: 2",
    ],
    platforms=["Posix", "MacOS X"],
)
