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
    # temporary requirement to get urllib in a version compatible with requests
    # to be kept until requests update its requirements
    # (cf. https://github.com/psf/requests/issues/5654
    # and https://github.com/psf/requests/pull/5651)
    "urllib3<1.26",
    "eve>=1.1.2,<=2.1.0",
    "eve-elastic>=7.4.0,<7.5.0",
    "elasticsearch<7.14",  # we are using oss version on test server
    "flask>=1.1,<1.2",
    "flask-mail>=0.9,<0.10",
    "flask-script>=2.0.5,<3.0",
    "flask-babel>=1.0,<4.1",
    "pillow>=9.2,<9.3",
    "arrow>=0.4,<=0.13",
    "bcrypt>=3.1.1,<4.2",
    "blinker>=1.3,<1.8",
    "celery[redis]>=5.2.7,<5.3",
    "cerberus>=1.3.2,<1.4",
    "redis>=4.5.2,<5.1",
    "kombu>=5.2.4,<5.3",
    "feedparser>=6.0.8,<6.1",
    "hachoir<=3.0a3",
    "HermesCache>=0.10.0,<0.11.0",
    "python-magic>=0.4,<0.5",
    "ldap3>=2.2.4,<2.6",
    "pytz>=2021.3",
    "tzlocal>=2.1,<3.0",
    "raven[flask]>=5.10,<7.0",
    "requests>=2.7.0,<3.0",
    "boto3>=1.26,<2.0",
    "websockets==10.3",
    "mongolock>=1.3.4,<1.4",
    "PyYAML>=6.0.1",
    "lxml>=4,<4.7",
    "python-twitter==3.5",
    "chardet<6.0",
    "pymongo>=3.8,<3.12",
    "croniter<2.1",
    "python-dateutil<2.10",
    "unidecode>=0.04.21,<=1.3.8",
    "authlib>0.14,<0.15",
    "draftjs-exporter[lxml]<2.2",
    "regex==2020.7.14",
    "flask-oidc-ex==0.5.5",
    # to be replaced by stdlib version when we use Python 3.8+
    "typing_extensions>=3.7.4",
    "elastic-apm[flask]>=6.15.1,<7.0",
    # Fix an issue with MarkupSafe 2.1.0 not exporting `soft_unicode`
    "MarkupSafe<2.1",
    "reportlab>=3.6.11,<3.7",
    "pyjwt>=2.4.0,<2.5",
    "Werkzeug>=1.0,<1.1",
    "Jinja2>=2.11,<4.0",
    "Click>=8.0.3,<9.0",
    "itsdangerous>=1.1,<2.0",
    "pymemcache>=4.0,<4.1",
    "xmlsec==1.3.13",  # pin xmlsec due to https://github.com/xmlsec/python-xmlsec/issues/314
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
    version="2.7.0rc5",
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
