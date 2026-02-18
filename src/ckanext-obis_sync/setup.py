# -*- coding: utf-8 -*-
from setuptools import setup, find_namespace_packages

setup(
    name="ckanext-obis_sync",
    version="0.1.0",
    description="OBIS data synchronization commands for CKAN",
    packages=find_namespace_packages(include=["ckanext.*"]),
    install_requires=["requests"],
    entry_points="""
    [ckan.plugins]
    obis_sync=ckanext.obis_sync.plugin:ObisSyncPlugin
    """,
)
