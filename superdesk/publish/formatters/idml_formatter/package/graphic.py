from lxml import etree


from .base import BasePackageElement


class Graphic(BasePackageElement):
    """
    As Adobe's idml specification explains:
        ``
        The Graphic.xml file contains the links, colors, swatches, gradients, mixed inks, mixed ink groups, tints,
        and stroke styles contained in the document.
        ``
    """

    # Default indesign colours.
    # If defaults colors are not implemented, colors will not be available after idml was imported.
    COLORS = (
        {
            'Self': 'Color/Black',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 0 0 100',
            'ColorOverride': 'Specialblack',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Black',
            'ColorEditable': 'false',
            'ColorRemovable': 'false',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch3',
        },
        {
            'Self': 'Color/C=0 M=0 Y=100 K=0',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 0 100 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'C=0 M=0 Y=100 K=0',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch6'
        },
        {
            'Self': 'Color/C=0 M=100 Y=0 K=0',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 100 0 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'C=0 M=100 Y=0 K=0',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch5'
        },
        {
            'Self': 'Color/C=100 M=0 Y=0 K=0',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '100 0 0 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'C=100 M=0 Y=0 K=0',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch4'
        },
        {
            'Self': 'Color/C=100 M=90 Y=10 K=0',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '100 90 10 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'C=100 M=90 Y=10 K=0',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch9'
        },
        {
            'Self': 'Color/C=15 M=100 Y=100 K=0',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '15 100 100 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'C=15 M=100 Y=100 K=0',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch7'
        },
        {
            'Self': 'Color/C=75 M=5 Y=100 K=0',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '75 5 100 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'C=75 M=5 Y=100 K=0',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch8'
        },
        {
            'Self': 'Color/Cyan',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '100 0 0 0',
            'ColorOverride': 'Hiddenreserved',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Cyan',
            'ColorEditable': 'false',
            'ColorRemovable': 'false',
            'Visible': 'false',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'n'
        },
        {
            'Self': 'Color/Hyperlink',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '86 56.99999999999999 0 16',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Hyperlink',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatcha'
        },
        {
            'Self': 'Color/Magenta',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 100 0 0',
            'ColorOverride': 'Hiddenreserved',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Magenta',
            'ColorEditable': 'false',
            'ColorRemovable': 'false',
            'Visible': 'false',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'n'
        },
        {
            'Self': 'Color/Paper',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 0 0 0',
            'ColorOverride': 'Specialpaper',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Paper',
            'ColorEditable': 'true',
            'ColorRemovable': 'false',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch2'
        },
        {
            'Self': 'Color/Registration',
            'Model': 'Registration',
            'Space': 'CMYK',
            'ColorValue': '100 100 100 100',
            'ColorOverride': 'Specialregistration',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Registration',
            'ColorEditable': 'false',
            'ColorRemovable': 'false',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch1'
        },
        {
            'Self': 'Color/Yellow',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 0 100 0',
            'ColorOverride': 'Hiddenreserved',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': 'Yellow',
            'ColorEditable': 'false',
            'ColorRemovable': 'false',
            'Visible': 'false',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'n'
        },
        {
            'Self': 'Color/u8d',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 0 0 100',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': '$ID/',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'false',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'n'
        },
        {
            'Self': 'Color/u8f',
            'Model': 'Process',
            'Space': 'CMYK',
            'ColorValue': '0 0 0 0',
            'ColorOverride': 'Normal',
            'AlternateSpace': 'NoAlternateColor',
            'AlternateColorValue': '',
            'Name': '$ID/',
            'ColorEditable': 'true',
            'ColorRemovable': 'true',
            'Visible': 'false',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'n'
        }
    )
    INKS = (
        {
            'Self': 'Ink/$ID/Process Cyan',
            'Name': '$ID/Process Cyan',
            'Angle': '75',
            'ConvertToProcess': 'false',
            'Frequency': '70',
            'NeutralDensity': '0.61',
            'PrintInk': 'true',
            'TrapOrder': '1',
            'InkType': 'Normal'
        },
        {
            'Self': 'Ink/$ID/Process Magenta',
            'Name': '$ID/Process Magenta',
            'Angle': '15',
            'ConvertToProcess': 'false',
            'Frequency': '70',
            'NeutralDensity': '0.76',
            'PrintInk': 'true',
            'TrapOrder': '2',
            'InkType': 'Normal'
        },
        {
            'Self': 'Ink/$ID/Process Yellow',
            'Name': '$ID/Process Yellow',
            'Angle': '0',
            'ConvertToProcess': 'false',
            'Frequency': '70',
            'NeutralDensity': '0.16',
            'PrintInk': 'true',
            'TrapOrder': '3',
            'InkType': 'Normal'
        },
        {
            'Self': 'Ink/$ID/Process Black',
            'Name': '$ID/Process Black',
            'Angle': '45',
            'ConvertToProcess': 'false',
            'Frequency': '70',
            'NeutralDensity': '1.7',
            'PrintInk': 'true',
            'TrapOrder': '4',
            'InkType': 'Normal'
        }
    )
    STROKESTYLES = (
        {
            'Self': 'StrokeStyle/$ID/Triple_Stroke',
            'Name': '$ID/Triple_Stroke'
        },
        {
            'Self': 'StrokeStyle/$ID/ThickThinThick',
            'Name': '$ID/ThickThinThick'
        },
        {
            'Self': 'StrokeStyle/$ID/ThinThickThin',
            'Name': '$ID/ThinThickThin'
        },
        {
            'Self': 'StrokeStyle/$ID/ThickThick',
            'Name': '$ID/ThickThick'
        },
        {
            'Self': 'StrokeStyle/$ID/ThickThin',
            'Name': '$ID/ThickThin'
        },
        {
            'Self': 'StrokeStyle/$ID/ThinThick',
            'Name': '$ID/ThinThick'
        },
        {
            'Self': 'StrokeStyle/$ID/ThinThin',
            'Name': '$ID/ThinThin'
        },
        {
            'Self': 'StrokeStyle/$ID/Japanese Dots',
            'Name': '$ID/Japanese Dots'
        },
        {
            'Self': 'StrokeStyle/$ID/White Diamond',
            'Name': '$ID/White Diamond'
        },
        {
            'Self': 'StrokeStyle/$ID/Left Slant Hash',
            'Name': '$ID/Left Slant Hash'
        },
        {
            'Self': 'StrokeStyle/$ID/Right Slant Hash',
            'Name': '$ID/Right Slant Hash'
        },
        {
            'Self': 'StrokeStyle/$ID/Straight Hash',
            'Name': '$ID/Straight Hash'
        },
        {
            'Self': 'StrokeStyle/$ID/Wavy',
            'Name': '$ID/Wavy'
        },
        {
            'Self': 'StrokeStyle/$ID/Canned Dotted',
            'Name': '$ID/Canned Dotted'
        },
        {
            'Self': 'StrokeStyle/$ID/Canned Dashed 3x2',
            'Name': '$ID/Canned Dashed 3x2'
        },
        {
            'Self': 'StrokeStyle/$ID/Canned Dashed 4x4',
            'Name': '$ID/Canned Dashed 4x4'
        },
        {
            'Self': 'StrokeStyle/$ID/Dashed',
            'Name': '$ID/Dashed'
        },
        {
            'Self': 'StrokeStyle/$ID/Solid',
            'Name': '$ID/Solid'
        }
    )

    @property
    def filename(self):
        """
        Filename inside IDML package.
        Used as a filename for a file inside zip container.
        :return str: filename
        """
        return 'Resources/Graphic.xml'

    def _build_etree(self):
        self._etree = etree.Element(
            etree.QName(self.XMLNS_IDPKG, 'Graphic'),
            nsmap={'idPkg': self.XMLNS_IDPKG}
        )
        self._etree.set('DOMVersion', self.DOM_VERSION)
        self._add_colors()
        self._add_inks()
        self._add_pasted_smooth_shade()
        self._add_swatch()
        self._add_gradient()
        self._add_strokestyles()

    def _add_colors(self):
        """
        Add colors (<Color...>) defined `Graphic.COLORS`.
        As Adobe's idml specification explains:
            ``
            The <Color> element corresponds to a color in a document, including both named and unnamed colors.
            ``
        """
        for _attribs in self.COLORS:
            etree.SubElement(self._etree, 'Color', attrib=_attribs)

    def _add_inks(self):
        """
        Add inks (<Ink...>) defined `Graphic.INKS`.
        As Adobe's idml specification explains:
            ``
            For process colors, Cyan, Magenta, Yellow and Black inks are mixed
            together to produce a range of colors.
            ``
        """
        for _attribs in self.INKS:
            etree.SubElement(self._etree, 'Ink', attrib=_attribs)

    def _add_pasted_smooth_shade(self):
        """
        Add <PastedSmoothShade..>
        """
        pastedsmoothshade = etree.SubElement(
            self._etree, 'PastedSmoothShade',
            attrib={
                'Self': 'PastedSmoothShade/u90',
                'ContentsVersion': '0',
                'ContentsType': 'ConstantShade',
                'SpotColorList': '',
                'ContentsEncoding': 'Ascii64Encoding',
                'ContentsMatrix': '1 0 0 1 0 0',
                'Name': '$ID/',
                'ColorEditable': 'true',
                'ColorRemovable': 'true',
                'Visible': 'false',
                'SwatchCreatorID': '7937',
                'SwatchColorGroupReference': 'n'
            }
        )
        # Properties
        properties = etree.SubElement(pastedsmoothshade, 'Properties')
        etree.SubElement(properties, 'Contents').text = etree.CDATA('AAAAAUBv4AAAAAAAAAAAAAAAAAAAAAAAAAAAAA==')

    def _add_strokestyles(self):
        """
        Add stroke styles (<StrokeStyle...>) defined `Graphic.STROKESTYLES`.
        """
        for _attribs in self.STROKESTYLES:
            etree.SubElement(self._etree, 'StrokeStyle', attrib=_attribs)

    def _add_swatch(self):
        """
        Add <Swatch..>.
        As Adobe's idml specification explains:
            ``
            In the InDesign user interface, colors, tints, gradients, and mixed inks are all swatches,
            and can be applied to the  ll or stroke of a page item or text.
            Swatches share similar attributes and are used in similar ways.
            Swatches are not the same as inks, but each swatch generally
            corresponds to one ink or to a speci c set of inks.
            A <Color> element, for example, might correspond to a single spot ink,
            or might be made up of percentages of process inks.
            ``
        """
        etree.SubElement(self._etree, 'Swatch', attrib={
            'Self': 'Swatch/None',
            'Name': 'None',
            'ColorEditable': 'false',
            'ColorRemovable': 'false',
            'Visible': 'true',
            'SwatchCreatorID': '7937',
            'SwatchColorGroupReference': 'u18ColorGroupSwatch0',
        })

    def _add_gradient(self):
        """
        Add <Gradient..>.
        As Adobe's idml specification explains:
           ``
           A gradient is a blend between two or more colors or between two tints of the same color.
           Gradients can include the “Paper” color, process colors, spot colors,
           or mixed inks using any color model or color space.
           A gradient is a blend between two or more colors or between two tints of the same color.
           Gradients can include the “Paper” color, process colors, spot colors,
           or mixed inks using any color model or color space.
           ``
        """
        gradient = etree.SubElement(
            self._etree, 'Gradient',
            attrib={
                'Self': 'Gradient/u8e',
                'Type': 'Linear',
                'Name': '$ID/',
                'ColorEditable': 'true',
                'ColorRemovable': 'true',
                'Visible': 'false',
                'SwatchCreatorID': '7937',
                'SwatchColorGroupReference': 'n',
            }
        )
        etree.SubElement(gradient, 'GradientStop', attrib={
            'Self': 'u8eGradientStop0',
            'StopColor': 'Color/u8f',
            'Location': '0'
        })
        etree.SubElement(gradient, 'GradientStop', attrib={
            'Self': 'u8eGradientStop1',
            'StopColor': 'Color/Black',
            'Location': '100',
            'Midpoint': '50'
        })
