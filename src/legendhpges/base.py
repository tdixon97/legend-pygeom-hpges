from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from legendmeta import AttrsDict
from pint import Quantity
from pyg4ometry import geant4

from . import utils
from .materials import make_natural_germanium
from .registry import default_g4_registry
from .registry import default_units_registry as u


class HPGe(ABC, geant4.LogicalVolume):
    """An High-Purity Germanium detector.

    Parameters
    ----------
    metadata
        LEGEND HPGe configuration metadata file name describing the
        detector shape.
    name
        name to attach to this detector. Used to name solid and logical
        volume.
    registry
        pyg4ometry Geant4 registry instance.
    material
        pyg4ometry Geant4 material for the detector.
    """

    def __init__(
        self,
        metadata: str | dict | AttrsDict,
        name: str | None = None,
        registry: geant4.Registry = default_g4_registry,
        material: geant4.MaterialCompound = None,
    ) -> None:
        if registry is None:
            msg = "registry cannot be None"
            raise ValueError(msg)

        if metadata is None:
            msg = "metadata cannot be None"
            raise ValueError(msg)

        if material is None:
            material = make_natural_germanium(registry)

        # build crystal, declare as detector
        if not isinstance(metadata, (dict, AttrsDict)):
            with Path(metadata).open() as jfile:
                self.metadata = AttrsDict(json.load(jfile))
        else:
            self.metadata = AttrsDict(metadata)

        if name is None:
            self.name = self.metadata.name
        else:
            self.name = name

        self.registry = registry

        self.surfaces = []

        # build logical volume, default [mm]
        super().__init__(self._g4_solid(), material, self.name, self.registry)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.metadata})"

    def _g4_solid(self) -> geant4.solid.SolidBase:
        """Build (by default) a :class:`pyg4ometry.solid.GenericPolycone` instance from the (r, z) information.

        Returns
        -------
        g4_solid
            A derived class of :class:`pyg4ometry.solid.SolidBase` to be used to construct the logical volume.

        Note
        ----
            Detectors with a special geometry can have this method overridden in their class definition.
        """
        # return ordered r,z lists, default unit [mm]
        r, z = self._decode_polycone_coord()

        # build generic polycone, default [mm]
        return geant4.solid.GenericPolycone(
            self.name, 0, 2 * math.pi, r, z, self.registry
        )

    @abstractmethod
    def _decode_polycone_coord(self) -> tuple[list[float], list[float]]:
        """Decode shape information from geometry dictionary into (r, z) coordinates.

        Suitable for building a :class:`G4GenericPolycone`.

        Returns
        -------
        (r, z)
            two lists of r and z coordinates, respectively.

        Note
        ----
        Must be overloaded by derived classes.
        """

    def distance_to_surface(self, coords: np.Array) -> np.ndarray:
        """Compute the distance of a set of points to the nearest detector surface.

        Parameters
        ----------
        coords
            2D array of `(x,y,z)` coordinates for each point, first index corresponds to the point, second to the dimension `(x,y,z)`.

        Returns
        -------
        numpy array of the distance from each point to the nearest surface.

        Note
        ----
        - Only implemented for solids based on :class:`G4GenericPolycone`
        - Coordinates should be relative to the origin of the polycone.
        """
        # check type of the solid
        if isinstance(self.solid, geant4.solid.GenericPolycone) is False:
            msg = f"distance_to_surface is not implemented for {type(self.solid)} yet"
            raise NotImplementedError(msg)

        if np.shape(coords)[1] != 3:
            msg = "coords must be provided as a 2D array with x,y,z coordinates for each point."
            raise ValueError(msg)

        # convert x,y,z into r,z

        rz_coords = utils.convert_coords(coords)

        # get the coordinates
        r = self.solid.pR
        z = self.solid.pZ

        # build lists of pairs of coordinates
        s1 = np.array([np.array([r1, z1]) for r1, z1 in zip(r[:-1], z[:-1])])
        s2 = np.array([np.array([r2, z2]) for r2, z2 in zip(r[1:], z[1:])])

        n_segments = np.shape(s1)[0]
        n = np.shape(coords)[0]

        dists = np.full((n, n_segments), np.nan)

        for segment in range(n_segments):
            dists[:, segment] = utils.shortest_distance(
                s1[segment], s2[segment], rz_coords
            )

        return np.min(dists, axis=1)

    @property
    def volume(self) -> Quantity:
        """Volume of the HPGe."""
        volume = 0
        r1 = self.solid.pR[-1]
        z1 = self.solid.pZ[-1]
        for i in range(len(self.solid.pZ)):
            r2 = self.solid.pR[i]
            z2 = self.solid.pZ[i]
            volume += (r1 * r1 + r1 * r2 + r2 * r2) * (z2 - z1)
            r1 = r2
            z1 = z2

        return (2 * math.pi * abs(volume) / 6) * u.mm**3

    @property
    def mass(self) -> Quantity:
        """Mass of the HPGe."""
        return (self.volume * (self.material.density * u.g / u.cm**3)).to(u.g)
