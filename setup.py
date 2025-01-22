#!/usr/bin/env python3
#
# This file is part of Superdesk.
#
# Copyright 2013-2020 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from setuptools import setup, find_packages

LONG_DESCRIPTION = "Superdesk Server Core"

install_requires = [
    "urllib3>=1.26,<3",
    "elasticsearch[async]<7.18",  # we are using oss version on test server
    "flask-mail>=0.9,<0.11",
    "arrow>=0.4,<=1.3.0",
    "pillow>=9.2,<11.2",
    "bcrypt>=3.1.1,<4.3",
    "blinker>=1.3,<1.10",
    "celery[redis]>=5.2.7,<5.5",
    "cerberus>=1.3.2,<1.4",
    "redis>=4.5.2,<5.3",
    "kombu>=5.2.4,<5.5",
    "feedparser>=6.0.8,<6.1",
    "hachoir<=3.3.0",
    "HermesCache>=0.10.0,<1.1.0",
    "python-magic>=0.4,<0.5",
    "ldap3>=2.2.4,<2.10",
    "pytz>=2021.3",
    "tzlocal>=5.2",
    "sentry-sdk[quart]>=1.5.7,<2.0",
    "requests>=2.7.0,<3.0",
    "boto3>=1.26,<2.0",
    "websockets>=12.0,<13.2",
    "PyYAML>=6.0.1",
    "lxml>=5.2.2,<5.4",
    "lxml_html_clean>=0.1.1,<0.5",
    "python-twitter>=3.5,<3.6",
    "chardet<6.0",
    "pymongo>=4.9.1,<4.10",
    "croniter<6.1",
    "python-dateutil<2.10",
    "unidecode>=0.04.21,<=1.3.8",
    "authlib>0.14,<1.5",
    "draftjs-exporter[lxml]<5.1",
    "regex>=2020.7.14,<=2024.11.6",
    "flask-oidc-ex>=0.5.5,<0.7",
    "elastic-apm[flask]>=6.15.1,<7.0",
    # Fix an issue with MarkupSafe 2.1.0 not exporting `soft_unicode`
    "MarkupSafe>2.1",
    "reportlab<5,>=4.0.4",
    "pyjwt>=2.4.0,<2.11",
    "pymemcache>=4.0,<4.1",
    "xmlsec>=1.3.13,<1.3.15",
    # Async libraries
    "motor>=3.4.0,<4.0",
    "pydantic>=2.7.4,<3.0",
    # Custom repos, with patches applied
    "eve @ git+https://github.com/MarkLark86/eve@use-quart",
    "eve-elastic @ git+https://github.com/MarkLark86/eve-elastic@use-quart",
    "quart @ git+https://github.com/MarkLark86/quart@fix-test-client-with-utf8-url",
    "quart_babel>=1.0.7,<1.1",
    "asgiref>=3.8.1",
    # Patch Quart, Asyncio to work with Flask extensions
    # TODO-ASYNC: Remove this with our own flask patch (as quart-flask-patch also patches asyncio)
    "quart-flask-patch>=0.3.0,<0.4",
]

package_data = {
    "superdesk": [
        "templates/*.txt",
        "templates/*.html",
        "locators/data/*.json",
        "io/data/*.json",
        "data_updates/*.py",
        "data_updates/*.js",
        "translations/*.po",
        "translations/*.mo",
    ],
    "apps": [
        "prepopulate/*.json",
        "prepopulate/data_init/*.json",
        "io/data/*.json",
    ],
}

setup(
    name="Superdesk-Core",
    version="3.0.0.dev0",
    description="Superdesk Core library",
    long_description=LONG_DESCRIPTION,
    author="petr jasek",
    author_email="petr.jasek@sourcefabric.org",
    url="https://github.com/superdesk/superdesk-core",
    license="GPLv3",
    platforms=["any"],
    packages=find_packages(exclude=["tests*", "features*"]),
    package_data=package_data,
    include_package_data=True,
    # setup_requires=["setuptools_scm"],
    install_requires=install_requires,
    extras_require={
        "exiv2": ["pyexiv2>=2.12.0,<2.16"],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
)
