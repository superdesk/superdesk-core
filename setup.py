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
    'eve>=0.6,<=0.7.8',
    'eve-elastic==2.5.0',
    'flask>=0.10.1,<=0.12',
    'flask-oauthlib>=0.9.3,<0.10',
    'flask-mail>=0.9,<0.10',
    'flask-script>=2.0.5,<3.0',
    'flask_pymongo>=0.5.2,<1.0',
    'flask-babel==0.12.2',
    'pillow>=3.0,<=5.0',
    'arrow>=0.4,<=0.13',
    'asyncio>=3.4,<3.5',
    'bcrypt>=3.1.1,<3.2',
    'blinker>=1.3,<1.5',
    'celery[redis]>=4.3.0,<4.4',
    'redis>=3.2.0,<3.3',
    'kombu>=4.5,<4.6',
    'feedparser>=5.2,<5.3',
    'hachoir<=3.0a3',
    'HermesCache>=0.6.0,<0.8.0',
    'python-magic>=0.4,<0.5',
    'ldap3>=2.2.4,<2.6',
    'pytz>=2015.4',
    'tzlocal>=1.2.2,<2.0',
    'raven[flask]>=5.10,<7.0',
    'requests>=2.7.0,<3.0',
    'boto3>=1.1.4,<1.6',
    'websockets>=3.0,<7.0',
    'mongolock>=1.3.4,<1.4',
    'PyYAML>=4.2b1,<5.0',
    'lxml>=3.8,<4.2',
    'python-twitter==3.3',
    'chardet<4.0',
    'pymongo>=3.8,<3.9',
    'croniter<0.4',
    'python-dateutil<2.8',
    'unidecode==0.04.21',
    'authlib>0.12,<0.13',
    'draftjs-exporter[lxml]<2.2',
    'werkzeug<1.0',
]

package_data = {
    'superdesk': [
        'templates/*.txt',
        'templates/*.html',
        'locators/data/*.json',
        'io/data/*.json',
        'data_updates/*.py',
        'data_updates/*.js',
        'translations/*.po',
        'translations/*.mo',
    ],
    'apps': [
        'prepopulate/*.json',
        'prepopulate/data_init/*.json',
        'io/data/*.json',
    ],
}

setup(
    name='Superdesk-Core',
    version='1.33',
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
