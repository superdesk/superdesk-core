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
    'eve>=0.6,<=0.7.2',
    'eve-elastic==2.1',
    'flask>=0.10,<0.13',
    'flask-oauthlib>=0.9.3,<0.10',
    'flask-mail>=0.9,<0.10',
    'flask-script>=2.0.5,<3.0',
    'pillow>=3.0,<=4.0',
    'arrow>=0.4,<=0.10',
    'asyncio>=3.4,<3.5',
    'bcrypt>=3.1.1,<3.2',
    'blinker>=1.3,<1.5',
    'celery[redis]>=4.0.2,<4.1',
    'feedparser>=5.2,<5.3',
    'hachoir3>=3.0a1,<=3.0a2',
    'HermesCache>=0.6.0,<0.7.0',
    'python-magic>=0.4,<0.5',
    'python3-ldap>=0.9.8,<0.9.9',
    'pytz>=2015.4',
    'tzlocal>=1.2.2,<1.4',
    'raven[flask]>=5.10,<6.0',
    'requests>=2.7.0,<=2.13',
    'statsd>=3.1,<3.3',
    'httmock>=1.2.3,<1.3',
    'boto3>=1.1.4,<1.5',
    'websockets>=3.0,<3.3',
    'mongolock>=1.3.4,<1.4',
    'PyYAML>=3.11,<3.13',
    'lxml',
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
        'prepopulate/data_init/*.json',
        'io/data/*.json',
    ]
}

setup(
    name='Superdesk-Core',
    version='1.8.1',
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
