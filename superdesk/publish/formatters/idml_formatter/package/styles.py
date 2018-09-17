import uuid
from lxml import etree

from .base import BasePackageElement


class Styles(BasePackageElement):
    """
    As Adobe's idml specification explains:
      ``
      The Styles.xml file contains all of the paragraph, character, object, cell, table,
      and table of contents (TOC) styles used in the document.
      ``
    """

    XML_DECLARATION = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
    # http://wwwimages.adobe.com/content/dam/acom/en/devnet/indesign/sdk/cs6/idml/idml-specification.pdf
    # page 430
    PARAGRAPHSTYLE_DEFAULTS = {
        'Imported': 'false',
        'SplitDocument': 'false',
        'EmitCss': 'true',
        'StyleUniqueId': '$ID/',
        'IncludeClass': 'true',
        'EmptyNestedStyles': 'true',
        'EmptyLineStyles': 'true',
        'EmptyGrepStyles': 'true',
        'FillColor': 'Color/Black',
        'FontStyle': 'Regular',
        'PointSize': '12',
        'HorizontalScale': '100',
        'KerningMethod': '$ID/Metrics',
        'Ligatures': 'true',
        'PageNumberType': 'AutoPageNumber',
        'StrokeWeight': '1',
        'Tracking': '0',
        'Composer': 'HL Composer',
        'DropCapCharacters': '0',
        'DropCapLines': '0',
        'BaselineShift': '0',
        'Capitalization': 'Normal',
        'StrokeColor': 'Swatch/None',
        'HyphenateLadderLimit': '3',
        'VerticalScale': '100',
        'LeftIndent': '0',
        'RightIndent': '0',
        'FirstLineIndent': '0',
        'AutoLeading': '120',
        'AppliedLanguage': '$ID/English: USA',
        'Hyphenation': 'true',
        'HyphenateAfterFirst': '2',
        'HyphenateBeforeLast': '2',
        'HyphenateCapitalizedWords': 'true',
        'HyphenateWordsLongerThan': '5',
        'NoBreak': 'false',
        'HyphenationZone': '36',
        'SpaceBefore': '0',
        'SpaceAfter': '0',
        'Underline': 'false',
        'OTFFigureStyle': 'Default',
        'DesiredWordSpacing': '100',
        'MaximumWordSpacing': '133',
        'MinimumWordSpacing': '80',
        'DesiredLetterSpacing': '0',
        'MaximumLetterSpacing': '0',
        'MinimumLetterSpacing': '0',
        'DesiredGlyphScaling': '100',
        'MaximumGlyphScaling': '100',
        'MinimumGlyphScaling': '100',
        'StartParagraph': 'Anywhere',
        'KeepAllLinesTogether': 'false',
        'KeepWithNext': '0',
        'KeepFirstLines': '2',
        'KeepLastLines': '2',
        'Position': 'Normal',
        'StrikeThru': 'false',
        'CharacterAlignment': 'AlignEmCenter',
        'KeepLinesTogether': 'false',
        'StrokeTint': '-1',
        'FillTint': '-1',
        'OverprintStroke': 'false',
        'OverprintFill': 'false',
        'GradientStrokeAngle': '0',
        'GradientFillAngle': '0',
        'GradientStrokeLength': '-1',
        'GradientFillLength': '-1',
        'GradientStrokeStart': '0 0',
        'GradientFillStart': '0 0',
        'Skew': '0',
        'RuleAboveLineWeight': '1',
        'RuleAboveTint': '-1',
        'RuleAboveOffset': '0',
        'RuleAboveLeftIndent': '0',
        'RuleAboveRightIndent': '0',
        'RuleAboveWidth': 'ColumnWidth',
        'RuleBelowLineWeight': '1',
        'RuleBelowTint': '-1',
        'RuleBelowOffset': '0',
        'RuleBelowLeftIndent': '0',
        'RuleBelowRightIndent': '0',
        'RuleBelowWidth': 'ColumnWidth',
        'RuleAboveOverprint': 'false',
        'RuleBelowOverprint': 'false',
        'RuleAbove': 'false',
        'RuleBelow': 'false',
        'LastLineIndent': '0',
        'HyphenateLastWord': 'true',
        'ParagraphBreakType': 'Anywhere',
        'SingleWordJustification': 'FullyJustified',
        'OTFOrdinal': 'false',
        'OTFFraction': 'false',
        'OTFDiscretionaryLigature': 'false',
        'OTFTitling': 'false',
        'RuleAboveGapTint': '-1',
        'RuleAboveGapOverprint': 'false',
        'RuleBelowGapTint': '-1',
        'RuleBelowGapOverprint': 'false',
        'Justification': 'LeftAlign',
        'DropcapDetail': '1',
        'PositionalForm': 'None',
        'OTFMark': 'true',
        'HyphenWeight': '5',
        'OTFLocale': 'true',
        'HyphenateAcrossColumns': 'true',
        'KeepRuleAboveInFrame': 'false',
        'IgnoreEdgeAlignment': 'false',
        'OTFSlashedZero': 'false',
        'OTFStylisticSets': '0',
        'OTFHistorical': 'false',
        'OTFContextualAlternate': 'true',
        'UnderlineGapOverprint': 'false',
        'UnderlineGapTint': '-1',
        'UnderlineOffset': '-9999',
        'UnderlineOverprint': 'false',
        'UnderlineTint': '-1',
        'UnderlineWeight': '-9999',
        'StrikeThroughGapOverprint': 'false',
        'StrikeThroughGapTint': '-1',
        'StrikeThroughOffset': '-9999',
        'StrikeThroughOverprint': 'false',
        'StrikeThroughTint': '-1',
        'StrikeThroughWeight': '-9999',
        'MiterLimit': '4',
        'StrokeAlignment': 'OutsideAlignment',
        'EndJoin': 'MiterEndJoin',
        'SpanColumnType': 'SingleColumn',
        'SplitColumnInsideGutter': '6',
        'SplitColumnOutsideGutter': '0',
        'KeepWithPrevious': 'false',
        'SpanColumnMinSpaceBefore': '0',
        'SpanColumnMinSpaceAfter': '0',
        'OTFSwash': 'false',
        'ParagraphShadingTint': '-1',
        'ParagraphShadingOverprint': 'false',
        'ParagraphShadingWidth': 'ColumnWidth',
        'ParagraphShadingOn': 'false',
        'ParagraphShadingClipToFrame': 'false',
        'ParagraphShadingSuppressPrinting': 'false',
        'ParagraphShadingLeftOffset': '0',
        'ParagraphShadingRightOffset': '0',
        'ParagraphShadingTopOffset': '0',
        'ParagraphShadingBottomOffset': '0',
        'ParagraphShadingTopOrigin': 'AscentTopOrigin',
        'ParagraphShadingBottomOrigin': 'DescentBottomOrigin',
        'ParagraphBorderTint': '-1',
        'ParagraphBorderOverprint': 'false',
        'ParagraphBorderOn': 'false',
        'ParagraphBorderGapTint': '-1',
        'ParagraphBorderGapOverprint': 'false',
        'Tsume': '0',
        'LeadingAki': '-1',
        'TrailingAki': '-1',
        'KinsokuType': 'KinsokuPushInFirst',
        'KinsokuHangType': 'None',
        'BunriKinshi': 'true',
        'RubyOpenTypePro': 'true',
        'RubyFontSize': '-1',
        'RubyAlignment': 'RubyJIS',
        'RubyType': 'PerCharacterRuby',
        'RubyParentSpacing': 'RubyParent121Aki',
        'RubyXScale': '100',
        'RubyYScale': '100',
        'RubyXOffset': '0',
        'RubyYOffset': '0',
        'RubyPosition': 'AboveRight',
        'RubyAutoAlign': 'true',
        'RubyParentOverhangAmount': 'RubyOverhangOneRuby',
        'RubyOverhang': 'false',
        'RubyAutoScaling': 'false',
        'RubyParentScalingPercent': '66',
        'RubyTint': '-1',
        'RubyOverprintFill': 'Auto',
        'RubyStrokeTint': '-1',
        'RubyOverprintStroke': 'Auto',
        'RubyWeight': '-1',
        'KentenKind': 'None',
        'KentenFontSize': '-1',
        'KentenXScale': '100',
        'KentenYScale': '100',
        'KentenPlacement': '0',
        'KentenAlignment': 'AlignKentenCenter',
        'KentenPosition': 'AboveRight',
        'KentenCustomCharacter': '',
        'KentenCharacterSet': 'CharacterInput',
        'KentenTint': '-1',
        'KentenOverprintFill': 'Auto',
        'KentenStrokeTint': '-1',
        'KentenOverprintStroke': 'Auto',
        'KentenWeight': '-1',
        'Tatechuyoko': 'false',
        'TatechuyokoXOffset': '0',
        'TatechuyokoYOffset': '0',
        'AutoTcy': '0',
        'AutoTcyIncludeRoman': 'false',
        'Jidori': '0',
        'GridGyoudori': '0',
        'GridAlignFirstLineOnly': 'false',
        'GridAlignment': 'None',
        'CharacterRotation': '0',
        'RotateSingleByteCharacters': 'false',
        'Rensuuji': 'true',
        'ShataiMagnification': '0',
        'ShataiDegreeAngle': '4500',
        'ShataiAdjustTsume': 'true',
        'ShataiAdjustRotation': 'false',
        'Warichu': 'false',
        'WarichuLines': '2',
        'WarichuSize': '50',
        'WarichuLineSpacing': '0',
        'WarichuAlignment': 'Auto',
        'WarichuCharsBeforeBreak': '2',
        'WarichuCharsAfterBreak': '2',
        'OTFHVKana': 'false',
        'OTFProportionalMetrics': 'false',
        'OTFRomanItalics': 'false',
        'LeadingModel': 'LeadingModelAkiBelow',
        'ScaleAffectsLineHeight': 'false',
        'ParagraphGyoudori': 'false',
        'CjkGridTracking': 'false',
        'GlyphForm': 'None',
        'RubyAutoTcyDigits': '0',
        'RubyAutoTcyIncludeRoman': 'false',
        'RubyAutoTcyAutoScale': 'true',
        'TreatIdeographicSpaceAsSpace': 'true',
        'AllowArbitraryHyphenation': 'false',
        'BulletsAndNumberingListType': 'NoList',
        'NumberingStartAt': '1',
        'NumberingLevel': '1',
        'NumberingContinue': 'true',
        'NumberingApplyRestartPolicy': 'true',
        'BulletsAlignment': 'LeftAlign',
        'NumberingAlignment': 'LeftAlign',
        'NumberingExpression': '^#.^t',
        'BulletsTextAfter': '^t',
        'ParagraphBorderLeftOffset': '0',
        'ParagraphBorderRightOffset': '0',
        'ParagraphBorderTopOffset': '0',
        'ParagraphBorderBottomOffset': '0',
        'ParagraphBorderStrokeEndJoin': 'MiterEndJoin',
        'ParagraphBorderTopLeftCornerOption': 'None',
        'ParagraphBorderTopRightCornerOption': 'None',
        'ParagraphBorderBottomLeftCornerOption': 'None',
        'ParagraphBorderBottomRightCornerOption': 'None',
        'ParagraphBorderTopLeftCornerRadius': '1',
        'ParagraphBorderTopRightCornerRadius': '1',
        'ParagraphBorderBottomLeftCornerRadius': '1',
        'ParagraphBorderBottomRightCornerRadius': '1',
        'ParagraphShadingTopLeftCornerOption': 'None',
        'ParagraphShadingTopRightCornerOption': 'None',
        'ParagraphShadingBottomLeftCornerOption': 'None',
        'ParagraphShadingBottomRightCornerOption': 'None',
        'ParagraphShadingTopLeftCornerRadius': '1',
        'ParagraphShadingTopRightCornerRadius': '1',
        'ParagraphShadingBottomLeftCornerRadius': '1',
        'ParagraphShadingBottomRightCornerRadius': '1',
        'ParagraphBorderStrokeEndCap': 'ButtEndCap',
        'ParagraphBorderWidth': 'ColumnWidth',
        'ParagraphBorderTopOrigin': 'AscentTopOrigin',
        'ParagraphBorderBottomOrigin': 'DescentBottomOrigin',
        'ParagraphBorderTopLineWeight': '1',
        'ParagraphBorderBottomLineWeight': '1',
        'ParagraphBorderLeftLineWeight': '1',
        'ParagraphBorderRightLineWeight': '1',
        'ParagraphBorderDisplayIfSplits': 'false',
        'MergeConsecutiveParaBorders': 'false',
        'ProviderHyphenationStyle': 'HyphAll',
        'DigitsType': 'DefaultDigits',
        'Kashidas': 'DefaultKashidas',
        'DiacriticPosition': 'OpentypePositionFromBaseline',
        'CharacterDirection': 'DefaultDirection',
        'ParagraphDirection': 'LeftToRightDirection',
        'ParagraphJustification': 'DefaultJustification',
        'ParagraphKashidaWidth': '2',
        'XOffsetDiacritic': '0',
        'YOffsetDiacritic': '0',
        'OTFOverlapSwash': 'false',
        'OTFStylisticAlternate': 'false',
        'OTFJustificationAlternate': 'false',
        'OTFStretchedAlternate': 'false',
        'KeyboardDirection': 'DefaultDirection',
    }

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'Resources/Styles.xml'

    def _build_etree(self):
        self._etree = etree.Element(
            etree.QName(self.XMLNS_IDPKG, 'Styles'),
            nsmap={'idPkg': self.XMLNS_IDPKG}
        )
        self._etree.set('DOMVersion', self.DOM_VERSION)
        self._add_paragraph_style_group_paragraphs()
        self._add_paragraph_style_group_headings()
        self._add_paragraph_style_group_lists()
        self._add_table_style_group()
        self._add_character_style_group()
        self._add_paragraph_style_group_custom()

    def _add_paragraph_style_group_paragraphs(self):
        """
        Add paragraphs style group
        """
        # RootParagraphStyleGroup
        self._rootparagraphstylegroup = etree.SubElement(
            self._etree,
            'RootParagraphStyleGroup',
            attrib={
                'Self': 'root_paragraph_style_group',
            }
        )
        # ParagraphStyleGroup $ID/Paragraphs
        paragraphstylegroup = etree.SubElement(
            self._rootparagraphstylegroup,
            'ParagraphStyleGroup',
            attrib={
                'Self': 'ParagraphStyleGroup/$ID/Paragraphs',
                'Name': '$ID/Paragraphs'
            }
        )
        # ParagraphStyle.Paragraphs:NormalParagraph
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Paragraphs%3aNormalParagraph',
                'Name': 'Paragraphs:NormalParagraph',
                'NextStyle': 'ParagraphStyle/Paragraphs%3aNormalParagraph',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4())
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No paragraph style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '12'
        # ParagraphStyle.Paragraphs:Blockquote
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Paragraphs%3aBlockquote',
                'Name': 'Paragraphs:Blockquote',
                'NextStyle': 'ParagraphStyle/Paragraphs%3aBlockquote',
                'KeyboardShortcut': '0 0',
                'FontStyle': 'Italic',
                'LeftIndent': '30',
                'RightIndent': '30',
                'ParagraphBorderOn': 'true',
                'ParagraphBorderLeftOffset': '-20',
                'ParagraphBorderTopLineWeight': '0',
                'ParagraphBorderBottomLineWeight': '0',
                'ParagraphBorderLeftLineWeight': '4',
                'ParagraphBorderRightLineWeight': '0',
                'StyleUniqueId': str(uuid.uuid4())
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No paragraph style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '12'
        # ParagraphStyle.Paragraphs:Preformatted
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Paragraphs%3aPreformatted',
                'Name': 'Paragraphs:Preformatted',
                'NextStyle': 'ParagraphStyle/Paragraphs%3aPreformatted',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4())
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No paragraph style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '12'
        etree.SubElement(
            properties, 'AppliedFont', attrib={'type': 'string'}
        ).text = 'Courier'
        # ParagraphStyle.Paragraphs:Preformatted
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Paragraphs%3aNormalParagraph',
                'Name': 'Paragraphs:NormalParagraph',
                'NextStyle': 'ParagraphStyle/Paragraphs%3aNormalParagraph',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4())
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No paragraph style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '12'

    def _add_paragraph_style_group_headings(self):
        """
        Add headings style group
        """
        # ParagraphStyleGroup
        paragraphstylegroup = etree.SubElement(
            self._rootparagraphstylegroup,
            'ParagraphStyleGroup',
            attrib={
                'Self': 'ParagraphStyleGroup/$ID/Headings',
                'Name': '$ID/Headings'
            }
        )
        # ParagraphStyle.Headings:Heading1
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Headings%3aHeading1',
                'Name': 'Headings:Heading1',
                'NextStyle': 'ParagraphStyle/Headings%3aHeading1',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'PointSize': '40',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '40'
        # ParagraphStyle.Headings:Heading2
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Headings%3aHeading2',
                'Name': 'Headings:Heading2',
                'NextStyle': 'ParagraphStyle/Headings%3aHeading2',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'PointSize': '30',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '30'
        # ParagraphStyle.Headings:Heading3
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Headings%3aHeading3',
                'Name': 'Headings:Heading3',
                'NextStyle': 'ParagraphStyle/Headings%3aHeading3',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'PointSize': '20',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '20'
        # ParagraphStyle.Headings:Heading4
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Headings%3aHeading4',
                'Name': 'Headings:Heading4',
                'NextStyle': 'ParagraphStyle/Headings%3aHeading4',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'PointSize': '14',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '14'
        # ParagraphStyle.Headings:Heading5
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Headings%3aHeading5',
                'Name': 'Headings:Heading5',
                'NextStyle': 'ParagraphStyle/Headings%3aHeading5',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'PointSize': '11',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '11'
        # ParagraphStyle.Headings:Heading6
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Headings%3aHeading6',
                'Name': 'Headings:Heading6',
                'NextStyle': 'ParagraphStyle/Headings%3aHeading6',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'PointSize': '9',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '9'

    def _add_paragraph_style_group_lists(self):
        """
        Add lists style group
        """
        # ParagraphStyleGroup
        paragraphstylegroup = etree.SubElement(
            self._rootparagraphstylegroup,
            'ParagraphStyleGroup',
            attrib={
                'Self': 'ParagraphStyleGroup/$ID/Lists',
                'Name': '$ID/Lists'
            }
        )
        # ParagraphStyle.Lists:OrderedList
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Lists%3aOrderedList',
                'Name': 'Lists:OrderedList',
                'NextStyle': 'ParagraphStyle/Lists%3aOrderedList',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No paragraph style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '12'
        # ParagraphStyle.Lists:UnorderedList
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Lists%3aUnorderedList',
                'Name': 'Lists:UnorderedList',
                'NextStyle': 'ParagraphStyle/Lists%3aUnorderedList',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No paragraph style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '12'

    def _add_table_style_group(self):
        """
        Add table style group
        """
        # RootTableStyleGroup
        self._roottablestylegroup = etree.SubElement(
            self._etree,
            'RootTableStyleGroup',
            attrib={
                'Self': 'root_table_style_group',
            }
        )
        # TableStyle
        tablestyle = etree.SubElement(
            self._roottablestylegroup,
            'TableStyle',
            attrib={
                'Self': 'TableStyle/$ID/NormalTable',
                'Name': '$ID/NormalTable',
                'Imported': 'false',
                'NextStyle': 'TableStyle/$ID/NormalTable',
                'KeyboardShortcut': '0 0'
            }
        )
        # Properties
        properties = etree.SubElement(tablestyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No table style]'

    def _add_character_style_group(self):
        """
        Add characters style group
        """
        # RootCharacterStyleGroup
        self._rootcharacterstylegroup = etree.SubElement(
            self._etree,
            'RootCharacterStyleGroup',
            attrib={
                'Self': 'root_character_style_group',
            }
        )
        # CharacterStyle No character style
        etree.SubElement(
            self._rootcharacterstylegroup,
            'CharacterStyle',
            attrib={
                'Self': 'CharacterStyle/$ID/[No character style]',
                'Name': '$ID/[No character style]'
            }
        )
        # CharacterStyle.Hyperlink
        characterstyle = etree.SubElement(
            self._rootcharacterstylegroup,
            'CharacterStyle',
            attrib={
                'Self': 'CharacterStyle/$ID/Hyperlink',
                'Name': '$ID/Hyperlink',
                'FillColor': 'Color/Hyperlink',
                'Underline': 'true',
            }
        )
        # Properties
        properties = etree.SubElement(characterstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = '$ID/[No character style]'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'

    def _add_paragraph_style_group_custom(self):
        """
        Add custom style group
        """
        # ParagraphStyleGroup
        paragraphstylegroup = etree.SubElement(
            self._rootparagraphstylegroup,
            'ParagraphStyleGroup',
            attrib={
                'Self': 'ParagraphStyleGroup/$ID/Custom',
                'Name': '$ID/Custom'
            }
        )

        # ParagraphStyle.Custom:Headline
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Custom%3aHeadline',
                'Name': 'Custom:Headline',
                'NextStyle': 'ParagraphStyle/Custom%3aHeadline',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'FontStyle': 'Bold',
                'PointSize': '48',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '48'
        # ParagraphStyle.Custom:Byline
        paragraphstyle = etree.SubElement(
            paragraphstylegroup,
            'ParagraphStyle',
            attrib={
                'Self': 'ParagraphStyle/Custom%3aByline',
                'Name': 'Custom:Byline',
                'NextStyle': 'ParagraphStyle/Custom%3aByline',
                'KeyboardShortcut': '0 0',
                'StyleUniqueId': str(uuid.uuid4()),
                'FontStyle': 'Bold',
                'PointSize': '20',
            }
        )
        properties = etree.SubElement(paragraphstyle, 'Properties')
        etree.SubElement(
            properties, 'BasedOn', attrib={'type': 'string'}
        ).text = 'ParagraphStyle/$ID/NormalParagraphStyle'
        etree.SubElement(
            properties, 'PreviewColor', attrib={'type': 'enumeration'}
        ).text = 'Nothing'
        etree.SubElement(
            properties, 'ParagraphShadingColor', attrib={'type': 'object'}
        ).text = 'Color/Black'
        etree.SubElement(
            properties, 'Leading', attrib={'type': 'unit'}
        ).text = '20'
