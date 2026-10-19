"""
Regular latitude/longitude grid toolkit for SafeGrid.

Owner: Person 2 (Risk Engine & Geospatial Processing)
Branch: feature/risk-engine

Region-agnostic, hazard-agnostic. A "grid" is nothing more than a cell size plus
a rectangular bounding box; a named region (e.g. a state) is just one bounding
box, so adding or growing regions is data, never code.

Cells are indexed against a fixed GLOBAL anchor (-90, -180) rather than a
region's own corner. That keeps a cell's identity stable when a region grows:
Karnataka's cells are the same cells whether or not the country is queried.

Coordinates follow RFC 7946 GeoJSON, [longitude, latitude], closed rings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterator

# Global anchor so cell indices are stable across regions and non-negative.
ANCHOR_LAT = -90.0
ANCHOR_LON = -180.0

# Guards against binary floating-point error at exact cell boundaries
# (e.g. 12.3 / 0.1 == 1022.9999999999999). In index space this is ~1e-10 deg.
_EPSILON = 1e-9


@dataclass(frozen=True)
class GridSpec:
    """Cell size for a grid. The region (bounding box) is supplied per query."""

    cell_size_deg: float

    def __post_init__(self) -> None:
        if self.cell_size_deg <= 0:
            raise ValueError("cell_size_deg must be positive")

    @property
    def label(self) -> str:
        """Compact, filename-safe label used inside cell IDs."""
        return f"{self.cell_size_deg:g}"


@dataclass(frozen=True)
class Region:
    """A rectangular area of interest, in degrees (WGS84)."""

    name: str
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def __post_init__(self) -> None:
        if self.min_lat > self.max_lat or self.min_lon > self.max_lon:
            raise ValueError("Region bounds must satisfy min <= max")
        if not (-90.0 <= self.min_lat <= 90.0 and -90.0 <= self.max_lat <= 90.0):
            raise ValueError("Region latitudes must be within [-90, 90]")

    def contains(self, latitude: float, longitude: float) -> bool:
        """True when the point lies inside the region (inclusive of edges)."""
        return (
            self.min_lat <= latitude <= self.max_lat
            and self.min_lon <= longitude <= self.max_lon
        )


@dataclass(frozen=True)
class Cell:
    """One grid cell, identified by its global (row, col) index."""

    spec: GridSpec
    row: int
    col: int

    @property
    def cell_id(self) -> str:
        """Stable ID; includes the cell size so IDs can't be misread across specs."""
        return f"grid:{self.spec.label}:{self.row}:{self.col}"

    @property
    def center(self) -> tuple[float, float]:
        """(latitude, longitude) of the cell centre."""
        size = self.spec.cell_size_deg
        return (
            ANCHOR_LAT + (self.row + 0.5) * size,
            ANCHOR_LON + (self.col + 0.5) * size,
        )

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(min_lat, min_lon, max_lat, max_lon) of the cell."""
        size = self.spec.cell_size_deg
        min_lat = ANCHOR_LAT + self.row * size
        min_lon = ANCHOR_LON + self.col * size
        return (min_lat, min_lon, min_lat + size, min_lon + size)

    def polygon(self) -> dict[str, Any]:
        """Closed GeoJSON Polygon for this cell (one exterior ring, no holes)."""
        min_lat, min_lon, max_lat, max_lon = self.bounds
        ring = [
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]
        return {"type": "Polygon", "coordinates": [ring]}


def _index_for(origin_value: float, degrees: float, size: float) -> int:
    """Global index of the cell containing `degrees`, with boundary guard."""
    return math.floor((degrees - origin_value) / size + _EPSILON)


def cell_at(spec: GridSpec, latitude: float, longitude: float) -> Cell:
    """Returns the cell containing (latitude, longitude) for the given grid."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("latitude must be within [-90, 90]")
    row = _index_for(ANCHOR_LAT, latitude, spec.cell_size_deg)
    col = _index_for(ANCHOR_LON, longitude, spec.cell_size_deg)
    return Cell(spec=spec, row=row, col=col)


def cell_id_at(spec: GridSpec, latitude: float, longitude: float) -> str:
    """Convenience: the cell ID a point falls into."""
    return cell_at(spec, latitude, longitude).cell_id


def parse_cell_id(spec: GridSpec, cell_id: str) -> Cell:
    """
    Reverses `Cell.cell_id`. Raises ValueError when the ID belongs to a
    different cell size than `spec`.
    """
    parts = cell_id.split(":")
    if len(parts) != 4 or parts[0] != "grid":
        raise ValueError(f"Malformed cell_id: {cell_id!r}")
    if parts[1] != spec.label:
        raise ValueError(
            f"cell_id {cell_id!r} was built for cell size {parts[1]!r}, not {spec.label!r}"
        )
    try:
        return Cell(spec=spec, row=int(parts[2]), col=int(parts[3]))
    except ValueError as exc:
        raise ValueError(f"Malformed cell_id: {cell_id!r}") from exc


def iter_cells(spec: GridSpec, region: Region) -> Iterator[Cell]:
    """Yields every cell whose square overlaps `region`, row-major."""
    row_min = _index_for(ANCHOR_LAT, region.min_lat, spec.cell_size_deg)
    row_max = _index_for(ANCHOR_LAT, region.max_lat, spec.cell_size_deg)
    col_min = _index_for(ANCHOR_LON, region.min_lon, spec.cell_size_deg)
    col_max = _index_for(ANCHOR_LON, region.max_lon, spec.cell_size_deg)
    for row in range(row_min, row_max + 1):
        for col in range(col_min, col_max + 1):
            yield Cell(spec=spec, row=row, col=col)


def cells_multipolygon(cells: Iterator[Cell]) -> dict[str, Any]:
    """
    GeoJSON MultiPolygon built from a set of cells — one polygon per cell.

    No adjacency is merged, so gaps/holes between non-contiguous cells are
    preserved honestly. Intended for painting the map layer of a single risk class.
    """
    polygons = [cell.polygon()["coordinates"] for cell in cells]
    return {"type": "MultiPolygon", "coordinates": polygons}
