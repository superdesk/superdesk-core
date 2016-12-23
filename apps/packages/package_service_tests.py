# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.tests import TestCase
from superdesk.metadata.packages import ASSOCIATED_TAKE_SEQUENCE
from .package_service import PackageService
from .takes_package_service import TakesPackageService


class PackageServiceTestCase(TestCase):

    def setUp(self):
        self.package1 = {"groups": [{"id": "root",
                                     "refs": [
                                         {
                                             "idRef": "main"
                                         },
                                         {
                                             "idRef": "sidebars"
                                         }
                                     ],
                                     "role": "grpRole:NEP"
                                     },
                                    {
                                    "id": "main",
                                    "refs": [
                                        {
                                            "renditions": {},
                                            "slugline": "Take-1 slugline",
                                            "guid": "123",
                                            "headline": "Take-1 soccer headline",
                                            "location": "archive",
                                            "type": "text",
                                            "itemClass": "icls:text",
                                            "residRef": "123"
                                        },
                                        {
                                            "renditions": {},
                                            "slugline": "Take-3 slugline",
                                            "guid": "789",
                                            "headline": "Take-3 soccer headline",
                                            "location": "archive",
                                            "type": "text",
                                            "itemClass": "icls:text",
                                            "residRef": "789"
                                        }
                                    ],
                                    "role": "grpRole:main"
                                    },
                                    {
                                    "id": "sidebars",
                                    "refs": [
                                        {
                                            "renditions": {},
                                            "slugline": "Take-2 slugline",
                                            "guid": "456",
                                            "headline": "Take-2 soccer headline",
                                            "location": "archive",
                                            "type": "text",
                                            "itemClass": "icls:text",
                                            "residRef": "456"
                                        }
                                    ],
                                    "role": "grpRole:sidebars"
                                    }]}

    def test_remove_ref_from_package(self):
        with self.app.app_context():
            anything_left = PackageService().remove_ref_from_inmem_package(self.package1, "456")
            self.assertEqual(len(self.package1.get('groups', [])), 2)
            root_group = self.package1.get('groups', [])[0]
            self.assertEqual(len(root_group.get('refs', [])), 1)
            self.assertTrue(anything_left)

    def test_remove_two_refs_from_package(self):
        anything_left1 = PackageService().remove_ref_from_inmem_package(self.package1, "456")
        anything_left2 = PackageService().remove_ref_from_inmem_package(self.package1, "123")
        self.assertEqual(len(self.package1.get('groups', [])), 2)
        root_group = self.package1.get('groups', [])[0]
        self.assertEqual(len(root_group.get('refs', [])), 1)
        self.assertTrue(anything_left1)
        self.assertTrue(anything_left2)

    def test_remove_two_refs_from_package2(self):
        PackageService().remove_ref_from_inmem_package(self.package1, "789")
        PackageService().remove_ref_from_inmem_package(self.package1, "123")
        self.assertEqual(len(self.package1.get('groups', [])), 2)
        root_group = self.package1.get('groups', [])[0]
        self.assertEqual(len(root_group.get('refs', [])), 1)

    def test_remove_all_refs_from_package(self):
        anything_left1 = PackageService().remove_ref_from_inmem_package(self.package1, "456")
        anything_left2 = PackageService().remove_ref_from_inmem_package(self.package1, "789")
        anything_left3 = PackageService().remove_ref_from_inmem_package(self.package1, "123")
        self.assertEqual(len(self.package1.get('groups', [])), 1)
        root_group = self.package1.get('groups', [])[0]
        self.assertEqual(len(root_group.get('refs', [])), 0)
        self.assertTrue(anything_left1)
        self.assertTrue(anything_left2)
        self.assertFalse(anything_left3)


class TakesPackageServiceTestCase(TestCase):

    def setUp(self):
        self.service = TakesPackageService()

    def test_no_assocations(self):
        takes_package = {
            "sequence": 1,
            "package_type": "takes",
            "_id": "takes_package",
            "groups": [
                {
                    "id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"
                },
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Take-1 slugline",
                            "guid": "123",
                            "headline": "Take-1 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123"
                        }
                    ],
                    "role": "grpRole:main"
                }
            ]
        }

        take = {
            "slugline": "Take-1 slugline",
            "guid": "123",
            "headline": "Take-1 soccer headline",
            "type": "text",
            "linked_in_packages": [
                {"package": "takes_package", "package_type": "takes"}
            ]
        }

        updates = {}
        self.service.update_associations(updates, takes_package, take)
        self.assertEqual(updates, {})

    def test_first_take_with_associations(self):
        takes_package = {
            "sequence": 1,
            "package_type": "takes",
            "_id": "takes_package",
            "groups": [
                {
                    "id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"
                },
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Take-1 slugline",
                            "guid": "123",
                            "headline": "Take-1 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123",
                            "sequence": 1
                        }
                    ],
                    "role": "grpRole:main"
                }
            ]
        }

        take = {
            "_id": "123",
            "slugline": "Take-1 slugline",
            "guid": "123",
            "headline": "Take-1 soccer headline",
            "type": "text",
            "linked_in_packages": [
                {"package": "takes_package", "package_type": "takes"}
            ],
            "associations": {
                "featuremedia": {
                    "_id": "take1_featuremedia"
                }
            }
        }

        updates = {}
        self.service.update_associations(updates, takes_package, take)
        self.assertEqual(updates,
                         {
                             ASSOCIATED_TAKE_SEQUENCE: 1,
                             "associations": {
                                 "featuremedia": {
                                     "_id": "take1_featuremedia"
                                 }
                             }
                         })

    def test_first_take_with_associations_second_take_with_no_associations(self):
        takes_package = {
            "sequence": 2,
            ASSOCIATED_TAKE_SEQUENCE: 1,
            "package_type": "takes",
            "_id": "takes_package",
            "groups": [
                {
                    "id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"
                },
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Take-1 slugline",
                            "guid": "123",
                            "headline": "Take-1 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123",
                            "sequence": 1
                        },
                        {
                            "renditions": {},
                            "slugline": "Take-2 slugline",
                            "guid": "456",
                            "headline": "Take-2 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "456",
                            "sequence": 2
                        }

                    ],
                    "role": "grpRole:main"
                }
            ],
            "associations": {
                "featuremedia": {
                    "_id": "take1_featuremedia"
                }
            }
        }

        take = {
            "_id": "456",
            "slugline": "Take-2 slugline",
            "guid": "456",
            "headline": "Take-2 soccer headline",
            "type": "text",
            "linked_in_packages": [
                {"package": "takes_package", "package_type": "takes"}
            ]
        }
        updates = {}
        self.service.update_associations(updates, takes_package, take)
        self.assertEqual(updates, {})

    def test_first_take_with_associations_third_take_with_associations(self):
        takes_package = {
            "sequence": 3,
            ASSOCIATED_TAKE_SEQUENCE: 1,
            "package_type": "takes",
            "_id": "takes_package",
            "groups": [
                {
                    "id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"
                },
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Take-1 slugline",
                            "guid": "123",
                            "headline": "Take-1 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123",
                            "sequence": 1
                        },
                        {
                            "renditions": {},
                            "slugline": "Take-2 slugline",
                            "guid": "456",
                            "headline": "Take-2 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "456",
                            "sequence": 2
                        },
                        {
                            "renditions": {},
                            "slugline": "Take-3 slugline",
                            "guid": "789",
                            "headline": "Take-3 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "789",
                            "sequence": 3
                        }
                    ],
                    "role": "grpRole:main"
                }
            ],
            "associations": {
                "featuremedia": {
                    "_id": "take1_featuremedia"
                }
            }
        }

        take = {
            "_id": "789",
            "slugline": "Take-3 slugline",
            "guid": "789",
            "headline": "Take-3 soccer headline",
            "type": "text",
            "linked_in_packages": [
                {"package": "takes_package", "package_type": "takes"}
            ],
            "associations": {
                "featuremedia": {
                    "_id": "take3-featuremedia"
                }
            }
        }

        updates = {}
        self.service.update_associations(updates, takes_package, take)
        self.assertEqual(updates,
                         {
                             ASSOCIATED_TAKE_SEQUENCE: 3,
                             "associations": {
                                 "featuremedia": {
                                     "_id": "take3-featuremedia"
                                 }
                             }
                         })

    def test_third_take_remove_associations(self):
        takes_package = {
            "sequence": 3,
            ASSOCIATED_TAKE_SEQUENCE: 3,
            "package_type": "takes",
            "_id": "takes_package",
            "groups": [
                {
                    "id": "root", "refs": [{"idRef": "main"}], "role": "grpRole:NEP"
                },
                {
                    "id": "main",
                    "refs": [
                        {
                            "renditions": {},
                            "slugline": "Take-1 slugline",
                            "guid": "123",
                            "headline": "Take-1 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "123",
                            "sequence": 1
                        },
                        {
                            "renditions": {},
                            "slugline": "Take-2 slugline",
                            "guid": "456",
                            "headline": "Take-2 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "456",
                            "sequence": 2
                        },
                        {
                            "renditions": {},
                            "slugline": "Take-3 slugline",
                            "guid": "789",
                            "headline": "Take-3 soccer headline",
                            "location": "archive",
                            "type": "text",
                            "itemClass": "icls:text",
                            "residRef": "789",
                            "sequence": 3
                        }
                    ],
                    "role": "grpRole:main"
                }
            ],
            "associations": {
                "featuremedia": {
                    "_id": "take3-featuremedia"
                }
            }
        }

        take = {
            "_id": "789",
            "slugline": "Take-3 slugline",
            "guid": "789",
            "headline": "Take-3 soccer headline",
            "type": "text",
            "linked_in_packages": [
                {"package": "takes_package", "package_type": "takes"}
            ]
        }

        updates = {}
        self.service.update_associations(updates, takes_package, take)
        self.assertEqual(updates,
                         {
                             ASSOCIATED_TAKE_SEQUENCE: 3,
                             "associations": None
                         })
