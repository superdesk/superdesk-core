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
from pip.req import parse_requirements
from pip.download import PipSession

LONG_DESCRIPTION = "Superdesk Server Core"

parsed_requirements = parse_requirements(
    'requirements.txt', session=PipSession()
)
install_requires = [
    str(ir.req) for ir in parsed_requirements
    if not (getattr(ir, 'link', False) or getattr(ir, 'url', False))
]
dependency_links = [
    str(ir.link) for ir in parsed_requirements
    if getattr(ir, 'link', False)
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
    version='1.0b1',
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
    dependency_links=dependency_links,
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
