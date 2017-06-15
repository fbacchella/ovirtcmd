#!/usr/bin/env python

import os
import sys
sys.version_info
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

install_requires = [
        # ovirt-engine-sdk-python 4.1.4 is badly broken
        ('ovirt-engine-sdk-python' '>4.1.4'), 'PyYaml', 'six'
    ]

if sys.version_info < (3,):
    install_requires += ['ipaddress', 'configparser']

setup(
    name = "oVirtCmd",
    version = "0.3",
    author = "Fabrice Bacchella",
    author_email = "fabrice.bacchella@3ds.com",
    description = "Command line tool to manage oVirt.",
    license = "Apache",
    keywords = "CLI oVirt virtualization",
    install_requires = install_requires,
    url = "https://github.com/fbacchella/ovirtcmd",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ovcmd=ovlib.ovcmd:main_wrap",
            "ovcmd%s=ovlib.ovcmd:main_wrap" % sys.version[:1],
            "ovcmd%s=ovlib.ovcmd:main_wrap" % sys.version[:3],
        ],
    },
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Classifier: Operating System :: OS Independent",
        "Environment :: Console",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
    platforms=["Posix", "MacOS X"],
)
