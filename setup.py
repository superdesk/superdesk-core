#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from setuptools import setup, find_packages

LONG_DESCRIPTION = "Superdesk Server Core"

install_requires = [
    'eve>=0.6,<0.7',
    'eve-elastic>=0.3.8,<0.4',
    'elasticsearch==1.9.0',
    'flask>=0.10,<0.11',
    'flask-mail>=0.9',
    'flask-script>=2.0.5',
    'pillow>=3.0',
    'arrow>=0.4',
    'asyncio>=3.4',
    'bcrypt>=1.1,<1.2',
    'beautifulsoup4>=4.4',
    'blinker>=1.3',
    'celery[redis]>=3.1.18',
    'feedparser>=5.2',
    'hachoir3-superdesk>=3.0a1',
    'HermesCache>=0.6.0,<0.7.0',
    'python-magic>=0.4',
    'python3-ldap>=0.9.8',
    'pytz>=2015.4',
    'tzlocal>=1.2.2',
    'raven[flask]>=5.10.0,<5.11',
    'requests>=2.7.0',
    'statsd>=3.1',
    'httmock>=1.2.3',
    'boto3>=1.1.4',
    'websockets>=2.6',
    'mongolock>=1.3.4',
    'PyYAML>=3.11',
]

package_data = {
    'superdesk': [
        'templates/*.txt',
        'templates/*.html',
        'locators/data/*.json',
        'io/data/*.json',
    ],
    'apps': [
        'prepopulate/*.json',
        'prepopulate/data_initialization/*.json',
        'io/data/*.json',
    ]
}

setup(
    name='Superdesk-Core',
    version='1.3rc3',
    description='Superdesk Core library',
    long_description=LONG_DESCRIPTION,
    author='petr jasek',
    author_email='petr.jasek@sourcefabric.org',
    url='https://github.com/superdesk/superdesk-core',
    license='GPLv3',
    platforms=['any'],
    packages=find_packages(exclude=['tests', 'features']),
    package_data=package_data,
    include_package_data=True,
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)
