# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013 - 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import arrow
import datetime
import logging

from flask import current_app as app
from superdesk import etree as sd_etree, app, get_resource_service
from superdesk.errors import ParserError
from superdesk.io.registry import register_feed_parser
from superdesk.io.feed_parsers import XMLFeedParser
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE
from superdesk.metadata.utils import is_normal_package
from lxml import etree

NITF = 'application/nitf+xml'
NS = {'iptc': 'http://iptc.org/std/NITF/2006-10-18',
      'nitf': 'http://iptc.org/std/NITF/2006-10-18/',
      'xhtml': 'http://www.w3.org/1999/xhtml'}

logger = logging.getLogger(__name__)


def get_content_tag(elem):
    try:
        return elem.tag.rsplit('}')[1]
    except IndexError:
        return elem.tag


class NewsMLTwoFeedParser(XMLFeedParser):
    """
    Feed Parser which can parse if the feed is in NewsML 2 format.
    """

    NAME = 'newsml2'

    label = 'News ML 2.0 Parser'
    # map subject qcode prefix to scheme
    # if value is None, no "scheme" is used, and name comes from qcode
    # if value is not None, <name> element is used instead of qcode
    SUBJ_QCODE_PREFIXES = {
        'subj': None
    }
    missing_voc = None

    def can_parse(self, xml):
        return any([xml.tag.endswith(tag) for tag in ['newsMessage', 'newsItem', 'packageItem']])

    def parse(self, xml, provider=None):
        self.root = xml
        items = []
        try:
            header = self.parse_header(xml)
            for item_set in xml.findall(self.qname('itemSet')):
                for item_tree in item_set:
                    item = self.parse_item(item_tree)
                    item['priority'] = header['priority']
                    items.append(item)
            else:
                if xml.tag.endswith('newsItem') or xml.tag.endswith('packageItem'):
                    item = self.parse_item(xml)
                    item.setdefault('priority', header['priority'])
                    items.append(item)
            return items
        except Exception as ex:
            raise ParserError.newsmlTwoParserError(ex, provider)

    def parse_item(self, tree):
        # config is not accessible during __init__, so we check it here
        if self.__class__.missing_voc is None:
            self.__class__.missing_voc = app.config.get('QCODE_MISSING_VOC', 'continue')
            if self.__class__.missing_voc not in ('reject', 'create', 'continue'):
                logger.warning('Bad QCODE_MISSING_VOC value ({value}) using default ("continue")'
                               .format(value=self.missing_voc))
                self.__class__.missing_voc = 'continue'

        item = dict()
        item['guid'] = tree.attrib['guid'] + ':' + tree.attrib['version']
        item['uri'] = tree.attrib['guid']
        item['version'] = tree.attrib['version']

        self.parse_item_meta(tree, item)
        self.parse_content_meta(tree, item)
        self.parse_rights_info(tree, item)

        if is_normal_package(item):
            self.parse_group_set(tree, item)
        else:
            self.parse_content_set(tree, item)

        return item

    def parse_header(self, tree):
        """Parse header element.

        :param tree:
        :return: dict
        """
        header = tree.find(self.qname('header'))
        priority = 5
        if header is not None:
            priority_elt = header.find(self.qname('priority'))
            if priority_elt is not None:
                priority = self.map_priority(priority_elt.text)

        return {'priority': priority}

    def parse_item_meta(self, tree, item):
        """Parse itemMeta tag"""
        meta = tree.find(self.qname('itemMeta'))
        item[ITEM_TYPE] = meta.find(self.qname('itemClass')).attrib['qcode'].split(':')[1]

        versioncreated_elt = meta.find(self.qname('versionCreated'))
        if versioncreated_elt is not None and versioncreated_elt.text:
            item['versioncreated'] = self.datetime(meta.find(self.qname('versionCreated')).text)
        firstcreated_elt = meta.find(self.qname('firstCreated'))
        if firstcreated_elt is not None and firstcreated_elt.text:
            item['firstcreated'] = self.datetime(firstcreated_elt.text)
        item['pubstatus'] = (meta.find(self.qname('pubStatus')).attrib['qcode'].split(':')[1]).lower()
        item['ednote'] = meta.find(self.qname('edNote')).text if meta.find(self.qname('edNote')) is not None else ''

        embargoed = meta.find(self.qname('embargoed'))
        if embargoed is not None and embargoed.text:
            try:
                item['embargoed'] = self.datetime(embargoed.text)
            except ValueError:
                item['embargoed_text'] = embargoed.text  # store it for inspection
                logger.warning("Can't parse embargoed info '%s' on item '%s'", embargoed.text, item['guid'])

    def parse_content_meta(self, tree, item):
        """Parse contentMeta tag"""
        meta = tree.find(self.qname('contentMeta'))

        def parse_meta_item_text(key, dest=None, elemTree=None):
            if dest is None:
                dest = key

            if elemTree is None:
                elemTree = meta

            elem = elemTree.find(self.qname(key))
            if elem is not None and elem.text:
                if dest == 'urgency':
                    item[dest] = int(elem.text)
                else:
                    item[dest] = elem.text

        parse_meta_item_text('urgency')
        parse_meta_item_text('slugline')
        parse_meta_item_text('headline')
        parse_meta_item_text('by', 'byline')

        item['slugline'] = item.get('slugline', '')
        item['headline'] = item.get('headline', '')

        try:
            if item[ITEM_TYPE] != CONTENT_TYPE.TEXT and item[ITEM_TYPE] != CONTENT_TYPE.COMPOSITE:
                # only for media item
                item['description_text'] = meta.find(self.qname('description')).text
                item['archive_description'] = item['description_text']
        except AttributeError:
            pass

        try:
            item['language'] = meta.find(self.qname('language')).get('tag')
        except AttributeError:
            pass

        self.parse_content_subject(meta, item)
        self.parse_content_place(meta, item)

        for info_source in meta.findall(self.qname('infoSource')):
            if info_source.get('role', '') == 'cRole:source':
                item['original_source'] = info_source.get('literal')
                break

        item['genre'] = []
        for genre_el in meta.findall(self.qname('genre')):
            for name_el in genre_el.findall(self.qname('name')):
                lang = name_el.get(self.qname("lang", ns='xml'))
                if lang and lang.startswith('en'):
                    item['genre'].append({'name': name_el.text})

        self.parse_authors(meta, item)

        content_created = meta.find(self.qname('contentCreated'))
        if content_created is not None and content_created.text and not item.get('firstcreated'):
            item['firstcreated'] = self.datetime(content_created.text)

        content_updated = meta.find(self.qname('contentModified'))
        if content_updated is not None and content_updated.text and not item.get('versioncreated'):
            item['versioncreated'] = self.datetime(content_updated.text)

        return meta

    def parse_content_subject(self, tree, item):
        """Parse subj type subjects into subject list."""
        item['subject'] = []
        for subject_elt in tree.findall(self.qname('subject')):
            qcode_parts = subject_elt.get('qcode', '').split(':')
            if len(qcode_parts) == 2 and qcode_parts[0] in self.SUBJ_QCODE_PREFIXES:
                scheme = self.SUBJ_QCODE_PREFIXES[qcode_parts[0]]
                if scheme is None:
                    # this is a main subject, we use IPTC qcode
                    try:
                        name = app.subjects[qcode_parts[1]]
                    except KeyError:
                        logger.debug("Subject code {code}' not found".format(code=qcode_parts[1]))
                        continue
                else:
                    # we use the given name if it exists
                    name_elt = subject_elt.find(self.qname('name'))
                    name = name_elt.text if name_elt is not None and name_elt.text else ""
                    try:
                        name = self.getVocabulary(scheme, qcode_parts[1], name)
                    except ValueError:
                        logger.info('Subject element rejected for "{code}"'.format(code=qcode_parts[1]))
                        continue

                subject_data = {
                    'qcode': qcode_parts[1],
                    'name': name
                }
                if scheme:
                    subject_data["scheme"] = scheme
                item['subject'].append(subject_data)

    def parse_content_place(self, tree, item):
        """Parse subject with type="cptType:5" into place list."""
        for subject in tree.findall(self.qname('subject')):
            if subject.get('type', '') == 'cptType:5':
                item['place'] = []
                item['place'].append({'name': self.get_literal_name(subject)})
                broader = subject.find(self.qname('broader'))
                if broader is not None:
                    item['place'].append({'name': self.get_literal_name(broader)})

    def parse_rights_info(self, tree, item):
        """Parse Rights Info tag"""
        info = tree.find(self.qname('rightsInfo'))
        if info is not None:
            item['usageterms'] = getattr(info.find(self.qname('usageTerms')), 'text', '')
            # item['copyrightholder'] = info.find(self.qname('copyrightHolder')).attrib['literal']
            # item['copyrightnotice'] = getattr(info.find(self.qname('copyrightNotice')), 'text', None)

    def parse_group_set(self, tree, item):
        item['groups'] = []
        for group in tree.find(self.qname('groupSet')):
            data = {}
            data['id'] = group.attrib['id']
            data['role'] = group.attrib['role']
            data['refs'] = self.parse_refs(group)
            item['groups'].append(data)

    def parse_refs(self, group_tree):
        refs = []
        for tree in group_tree:
            if 'idref' in tree.attrib:
                refs.append({'idRef': tree.attrib['idref']})
            else:
                ref = {}
                if 'version' in tree.attrib:
                    ref['residRef'] = tree.attrib['residref'] + ':' + tree.attrib['version']
                else:
                    ref['residRef'] = tree.attrib['residref']
                ref['contentType'] = tree.attrib['contenttype']
                ref['itemClass'] = tree.find(self.qname('itemClass')).attrib['qcode']

                for headline in tree.findall(self.qname('headline')):
                    ref['headline'] = headline.text

                refs.append(ref)
        return refs

    def parse_content_set(self, tree, item):
        item['renditions'] = {}
        for content in tree.find(self.qname('contentSet')):
            if content.tag == self.qname('inlineXML'):
                try:
                    item['word_count'] = int(content.attrib['wordcount'])
                except (KeyError, ValueError):
                    pass
                content = self.parse_inline_content(content, item=item)
                item['body_html'] = content.get('content')
                if 'format' in content:
                    item['format'] = content.get('format')
            elif content.tag == self.qname('inlineData'):
                item['body_html'] = content.text
                try:
                    item['word_count'] = int(content.attrib['wordcount'])
                except KeyError:
                    pass
            else:
                rendition = self.parse_remote_content(content)
                item['renditions'][rendition['rendition']] = rendition

    def parse_inline_content(self, tree, item, ns=NS['xhtml']):
        if tree.get('contenttype') == NITF:
            try:
                body_content = tree.xpath('.//nitf:body.content/nitf:block/*', namespaces=NS)
            except AttributeError:
                return {'contenttype': NITF, 'content': ''}
            elements = [etree.tostring(sd_etree.clean_html(e), encoding='unicode', method='html') for e in body_content]
            return {'contenttype': NITF, 'content': '\n'.join(elements)}
        else:
            html = tree.find(self.qname('html', ns))
            if html is None:
                try:
                    ns = tree.nsmap.get(None)  # fallback for missing xmlns
                except AttributeError:
                    ns = None
                html = tree.find(self.qname('html', ns))
            body = html.find(self.qname('body', ns))
            elements = []
            for elem in body:
                if elem.text:
                    tag = get_content_tag(elem)
                    elements.append('<%s>%s</%s>' % (tag, elem.text, tag))

            # If there is a single p tag then replace the line feeds with breaks
            if len(elements) == 1 and get_content_tag(body[0]) == 'p':
                elements[0] = elements[0].replace('\n    ', '</p><p>').replace('\n', '<br/>')

            content = dict()
            content['contenttype'] = tree.attrib['contenttype']
            if len(elements) > 0:
                content['content'] = "\n".join(elements)
            elif body.text:
                content['content'] = '<pre>' + body.text + '</pre>'
                content['format'] = CONTENT_TYPE.PREFORMATTED
            return content

    def parse_remote_content(self, tree):
        content = dict()
        content['residRef'] = tree.attrib.get('residref')
        content['sizeinbytes'] = int(tree.attrib.get('size', '0'))
        content['rendition'] = tree.attrib['rendition'].split(':')[1]
        content['mimetype'] = tree.attrib['contenttype']
        content['href'] = tree.attrib.get('href', None)
        return content

    def datetime(self, string):
        try:
            return datetime.datetime.strptime(string, '%Y-%m-%dT%H:%M:%S.000Z')
        except (ValueError, TypeError):
            try:
                return arrow.get(string).datetime
            except arrow.parser.ParserError:
                raise ValueError(string)

    def get_literal_name(self, item):
        """Get name for item with fallback to literal attribute if name is not provided."""
        name = item.find(self.qname('name'))
        return name.text if name is not None else item.attrib.get('literal')

    def parse_authors(self, meta, item):
        item['authors'] = []
        for creator in meta.findall(self.qname('creator')):
            name = creator.find(self.qname('name'))
            if name is not None:
                item['authors'].append({
                    'uri': creator.get('uri'),
                    'name': name.text,
                })

    def getVocabulary(self, voc_id, qcode, name):
        """Retrieve vocabulary and accept or reject it

        The vocabulary will be kept if it exists in local vocabularies.
        If it doesn't exist, it will be either created or rejected depending
        on the value of QCODE_MISSING_VOC:
            - if "reject", missing vocabulary are rejected (i.e. ValueError is raised)
            - if "create", a new vocabulary is created
            - if "continue" (default), value is returned but not created (it will be present in the resulting item,
              but the missing vocabulary is not added to SD)
        :param str qcode: qcode to check
        :param str name: name
        :return: value to use for name
        :raise ValueError: value is rejected
        """
        vocabularies_service = get_resource_service('vocabularies')
        voc = vocabularies_service.find_one(req=None, _id=voc_id)
        create = False
        if voc is None:
            create = True
            if self.missing_voc == "reject":
                raise ValueError
            elif self.missing_voc == "create":
                voc = {
                    "_id": voc_id,
                    "field_type": None,
                    "items": [],
                    "type": "manageable",
                    "schema": {"name": {}, "qcode": {}, "parent": {}},
                    "service": {
                            "all": 1
                    },
                    "display_name": voc_id.capitalize(),
                    "unique_field": "qcode",
                }
            elif self.missing_voc == "continue":
                return name
            else:
                raise RuntimeError("Unexpected missing_voc value: {}".format(self.missing_voc))
        try:
            items = voc['items']
        except KeyError:
            logger.warning("Creating missing items for {qcode}".format(qcode=qcode))
            voc['items'] = items = []

        for item in items:
            if item['qcode'] == qcode:
                if item.get("is_active", True):
                    return item.get('name', name)
                else:
                    # the vocabulary exists but is disabled
                    raise ValueError

        items.append({"is_active": True, "name": name, "qcode": qcode})
        if create:
            vocabularies_service.post([voc])
        else:
            vocabularies_service.put(voc_id, voc)
        return name


register_feed_parser(NewsMLTwoFeedParser.NAME, NewsMLTwoFeedParser())
