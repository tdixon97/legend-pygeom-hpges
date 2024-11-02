from __future__ import annotations

import math

from .base import HPGe


class SemiCoax(HPGe):
    """A semi-coaxial germanium detector."""

    def _decode_polycone_coord(self):
        c = self.metadata.geometry

        def _tan(a):
            return math.tan(math.pi * a / 180)

        r = []
        z = []
        surfaces = []

        r += [0, c.borehole.radius_in_mm]
        z += [c.borehole.depth_in_mm, c.borehole.depth_in_mm]
        surfaces += ["p+"]

        if c.taper.borehole.height_in_mm > 0:
            r += [
                c.borehole.radius_in_mm,
                c.borehole.radius_in_mm
                + c.taper.borehole.height_in_mm * _tan(c.taper.borehole.angle_in_deg),
            ]
            z += [c.taper.borehole.height_in_mm, 0]
            surfaces += ["p+", "p+"]
        else:
            r += [c.borehole.radius_in_mm]
            z += [0]
            surfaces += ["p+"]

        r += [
            c.groove.radius_in_mm.inner,
            c.groove.radius_in_mm.inner,
            c.groove.radius_in_mm.outer,
            c.groove.radius_in_mm.outer,
        ]

        z += [0, c.groove.depth_in_mm, c.groove.depth_in_mm, 0]
        surfaces += ["p+", "passive", "passive", "passive"]

        if c.taper.bottom.height_in_mm > 0:
            r += [
                c.radius_in_mm
                - c.taper.bottom.height_in_mm * _tan(c.taper.bottom.angle_in_deg),
                c.radius_in_mm,
            ]
            z += [0, c.taper.bottom.height_in_mm]
            surfaces += ["n+", "n+"]
        else:
            r += [c.radius_in_mm]
            z += [0]
            surfaces += ["n+"]

        if c.taper.top.height_in_mm > 0:
            r += [
                c.radius_in_mm,
                c.radius_in_mm
                - c.taper.top.height_in_mm * _tan(c.taper.top.angle_in_deg),
            ]
            z += [c.height_in_mm - c.taper.top.height_in_mm, c.height_in_mm]
            surfaces += ["n+", "n+"]
        else:
            r += [c.radius_in_mm]
            z += [c.height_in_mm]
            surfaces += ["n+"]

        r += [0]
        z += [c.height_in_mm]
        surfaces += ["n+"]

        self.surfaces = surfaces
        return r, z
