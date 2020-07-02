#!/usr/bin/env python

#import Inkscape_helper.inkscape_helper as doc
#import inkscape_helper as helper
from inkscape_helper.Coordinate import Coordinate
import inkscape_helper.Effect as eff
import inkscape_helper.SVG as svg
from inkscape_helper.Ellipse import Ellipse

from inkscape_helper.Line import Line
from inkscape_helper.EllipticArc import EllipticArc

from math import *

#Note: keep in mind that SVG coordinates start in the top-left corner i.e. with an inverted y-axis

# first define some SVG primitives
greenStyle = svg.green_style

def _makeCurvedSurface(topLeft, w, h, cutSpacing, hCutCount, thickness, parent, invertNotches = False, centralRib = False):
    group = svg.group(parent)
    width = Coordinate(w, 0)
    height = Coordinate(0, h)
    wCutCount = int(floor(w / cutSpacing))
    if wCutCount % 2 == 0:
        wCutCount += 1    # make sure we have an odd number of cuts
    xCutDist = w / wCutCount
    xSpacing = Coordinate(xCutDist, 0)
    ySpacing = Coordinate(0, cutSpacing)
    cut = height / hCutCount - ySpacing
    plateThickness = Coordinate(0, thickness)
    notchEdges = [0]
    topHCuts = []
    bottomHCuts = []

    for cutIndex in range(wCutCount):
        if (cutIndex % 2 == 1) != invertNotches:  # make a notch here
            inset = plateThickness
        else:
            inset = Coordinate(0, 0)

        # A-column of cuts
        aColStart = topLeft + xSpacing * cutIndex
        notchEdges.append((aColStart - topLeft).x)

        if cutIndex > 0: # no cuts at x == 0
            doc.draw_line(group, aColStart, aColStart + cut / 2)
            for j in range(hCutCount - 1):
                pos = aColStart + cut / 2 + ySpacing + (cut + ySpacing) * j
                doc.draw_line(group, pos, pos + cut)
            doc.draw_line(group, aColStart + height - cut / 2, aColStart + height)

        # B-column of cuts, offset by half the cut length; these cuts run in the opposite direction
        bColStart = topLeft + xSpacing * cutIndex + xSpacing / 2
        for j in reversed(range(hCutCount)):
            end = bColStart + ySpacing / 2 + (cut + ySpacing) * j
            start = end + cut
            if centralRib and hCutCount % 2 == 0 and cutIndex % 2 == 1:
                holeTopLeft = start + (ySpacing - plateThickness - xSpacing) / 2
                if j == hCutCount // 2 - 1:
                    start -= plateThickness / 2
                    doc.draw_line(group, holeTopLeft + plateThickness + xSpacing, holeTopLeft + plateThickness)
                    doc.draw_line(group, holeTopLeft, holeTopLeft + xSpacing)
                elif j == hCutCount // 2:
                    end += plateThickness / 2
            if j == 0:  # first row
                end += inset
            elif j == hCutCount - 1:  # last row
                start -= inset
            doc.draw_line(group, start, end)

        #horizontal cuts (should be done last)
        topHCuts.append((aColStart + inset, aColStart + inset + xSpacing))
        bottomHCuts.append((aColStart + height - inset, aColStart + height - inset + xSpacing))

    # draw the outline
    for c in reversed(bottomHCuts):
        doc.draw_line(group, c[1], c[0])
    doc.draw_line(group, topLeft + height, topLeft)
    for c in topHCuts:
        doc.draw_line(group, c[0], c[1])
    doc.draw_line(group, topLeft + width, topLeft + width + height)

    notchEdges.append(w)
    return notchEdges

def _makeNotchedEllipse(center, ellipse, startAngle, thickness, notches, parent, invertNotches):
    startAngle += pi # rotate 180 degrees to put the lid on the topside
    c2 = ellipse.notchCoordinate(ellipse.rAngle(startAngle), thickness)
    a1 = atan2((ellipse.w/2 + thickness) * c2.y, (ellipse.h/2 + thickness) * c2.x)
    for n in range(1, len(notches) - 1):
        startA = ellipse.angleFromDist(startAngle, notches[n])
        endA = ellipse.angleFromDist(startAngle, notches[n + 1])
        c1 = center + ellipse.coordinateFromAngle(endA)
        c2 = ellipse.notchCoordinate(endA, thickness)

        a2 = atan2((ellipse.w/2 + thickness) * c2.y, (ellipse.h/2 + thickness) * c2.x)

        c2 += center
        if (n % 2 == 1) != invertNotches:
            doc.draw_ellipse(parent, ellipse.w / 2, ellipse.h / 2, center, (startA, endA))
            doc.draw_line(parent, c1, c2)
        else:
            doc.draw_ellipse(parent, ellipse.w / 2 + thickness, ellipse.h / 2 + thickness, center, (a1, a2))
            doc.draw_line(parent, c2, c1)

        a1 = a2



class EllipticalBox(eff.Effect):
    """
    Creates a new layer with the drawings for a parametrically generaded box.
    """
    def __init__(self):
        options = [
            ['unit', 'string', 'mm', 'Unit, one of: cm, mm, in, ft, ...'],
            ['thickness', 'float', '3.0', 'Material thickness'],
            ['width', 'float', '100', 'Box width'],
            ['height', 'float', '100', 'Box height'],
            ['depth', 'float', '100', 'Box depth'],
            ['cut_dist', 'float', '1.5', 'Distance between cuts on the wrap around. Note that this value will change slightly to evenly fill up the available space.'],
            ['auto_cut_dist', 'inkbool', 'false', 'Automatically set the cut distance based on the curvature.'], # in progress
            ['cut_nr', 'int', '3', 'Number of cuts across the depth of the box.'],
            ['lid_angle', 'float', '120', 'Angle that forms the lid (in degrees, measured from centerpoint of the ellipse)'],
            ['body_ribcount', 'int', '0', 'Number of ribs in the body'],
            ['lid_ribcount', 'int', '0', 'Number of ribs in the lid'],
            ['invert_lid_notches', 'inkbool', 'false', 'Invert the notch pattern on the lid (keeps the lid from sliding sideways)'],
            ['central_rib_lid', 'inkbool', 'false', 'Create a central rib in the lid'],
            ['central_rib_body', 'inkbool', 'false', 'Create a central rib in the body']
        ]
        eff.Effect.__init__(self, options)


    def effect(self):
        """
        Draws as basic elliptical box, based on provided parameters
        """

        # input sanity check
        error = False
        if min(self.options.height, self.options.width, self.options.depth) == 0:
            inkex.errormsg('Error: Dimensions must be non zero')
            error = True

        if self.options.cut_nr < 1:
            inkex.errormsg('Error: Number of cuts should be at least 1')
            error = True

        if (self.options.central_rib_lid or self.options.central_rib_body) and self.options.cut_nr % 2 == 1:
            inkex.errormsg('Error: Central rib is only valid with an even number of cuts')
            error = True

        if self.options.unit not in self.knownUnits:
            inkex.errormsg('Error: unknown unit. '+ self.options.unit)
            error = True

        if error:
            exit()


        # convert units
        unit = self.options.unit
        H = self.unittouu(str(self.options.height) + unit)
        W = self.unittouu(str(self.options.width) + unit)
        D = self.unittouu(str(self.options.depth) + unit)
        thickness = self.unittouu(str(self.options.thickness) + unit)
        cutSpacing = self.unittouu(str(self.options.cut_dist) + unit)
        cutNr = self.options.cut_nr

        doc_root = self.document.getroot()
        docWidth = self.unittouu(doc_root.get('width'))
        docHeigh = self.unittouu(doc_root.attrib['height'])

        layer = svg.layer(doc_root, 'Elliptical Box')

        ell = Ellipse(W, H)

        #body and lid
        lidAngleRad = self.options.lid_angle * 2 * pi / 360
        lidStartAngle = pi / 2 - lidAngleRad / 2
        lidEndAngle = pi / 2 + lidAngleRad / 2

        lidLength = ell.dist_from_theta(lidStartAngle, lidEndAngle)
        bodyLength = ell.dist_from_theta(lidEndAngle, lidStartAngle)

        # do not put elements right at the edge of the page
        xMargin = 3
        yMargin = 3
        bodyNotches = _makeCurvedSurface(Coordinate(xMargin, yMargin), bodyLength, D, cutSpacing, cutNr, thickness, layer, False, self.options.central_rib_body)
        lidNotches = _makeCurvedSurface(Coordinate(xMargin, D + 2 * yMargin), lidLength, D, cutSpacing, cutNr, thickness, layer, not self.options.invert_lid_notches, self.options.centralRibLid)
        a1 = lidEndAngle

        # create elliptical sides
        sidesGrp = svg.group(layer)

        elCenter = Coordinate(xMargin + thickness + W / 2, 2 * D + H / 2 + thickness + 3 * yMargin)

        # indicate the division between body and lid
        if self.options.invert_lid_notches:
            doc.draw_line(sidesGrp, elCenter, elCenter + ell.coordinateFromAngle(ell.rAngle(lidStartAngle + pi)), greenStyle)
            doc.draw_line(sidesGrp, elCenter, elCenter + ell.coordinateFromAngle(ell.rAngle(lidEndAngle + pi)), greenStyle)
        else:
            angleA = ell.angleFromDist(lidStartAngle, lidNotches[2])
            angleB = ell.angleFromDist(lidStartAngle, lidNotches[-2])

            doc.draw_line(sidesGrp, elCenter, elCenter + ell.coordinateFromAngle(angleA + pi), greenStyle)
            doc.draw_line(sidesGrp, elCenter, elCenter + ell.coordinateFromAngle(angleB + pi), greenStyle)

        _makeNotchedEllipse(elCenter, ell, lidEndAngle, thickness, bodyNotches, sidesGrp, False)
        _makeNotchedEllipse(elCenter, ell, lidStartAngle, thickness, lidNotches, sidesGrp, not self.options.invert_lid_notches)

        # ribs
        spacer = Coordinate(0, 10)
        innerRibCenter = Coordinate(xMargin + thickness + W / 2, 2 * D +  1.5 * (H + 2 *thickness) + 4 * yMargin)
        innerRibGrp = svg.group(layer)

        outerRibCenter = Coordinate(2 * xMargin + 1.5 * (W + 2 * thickness) , 2 * D + 1.5 * (H + 2 * thickness) + 4 * yMargin)
        outerRibGrp = svg.group(layer)


        if self.options.centralRibLid:

            _makeNotchedEllipse(innerRibCenter, ell, lidStartAngle, thickness, lidNotches, innerRibGrp, False)
            _makeNotchedEllipse(outerRibCenter, ell, lidStartAngle, thickness, lidNotches, outerRibGrp, True)

        if self.options.centralRibBody:
            _makeNotchedEllipse(innerRibCenter + spacer, ell, lidEndAngle, thickness, bodyNotches, innerRibGrp, False)
            _makeNotchedEllipse(outerRibCenter + spacer, ell, lidEndAngle, thickness, bodyNotches, outerRibGrp, True)

        if self.options.centralRibLid or self.options.centralRibBody:
            doc.draw_text(sidesGrp, elCenter, 'side (duplicate this)')
            doc.draw_text(innerRibGrp, innerRibCenter, 'inside rib')
            doc.draw_text(outerRibGrp, outerRibCenter, 'outside rib')

# Create effect instance and apply it.
effect = EllipticalBox()
effect.affect()
