"""Module for loading and handling Vector Area of Interest (AOI) files."""

import os
import logging
import geopandas as gpd
from shapely.ops import unary_union

from .exceptions import (
    AOICRSError,
    AOIFileNotFoundError,
    AOIFormatError,
    AOIGeometryError,
)

logger = logging.getLogger(__name__)

# A bounding box as (minx,miny,maxx,maxy) in the AOI's CRS, defined as a type alias.
BoundingBox = tuple[float, float, float,float]

class AOIHandler:
    """Loads, validates, and processes vector AOI files (.geojson, .gpkg)."""

    def __init__(self, file_path: str, target_crs: str = "EPSG:4326"):
        """Initializes the AOI handler with a file path and target CRS.

        Parameters
        ----------
        file_path : str
            Path to the .geojson or .gpkg vector file.
        target_crs : str, optional
            Target coordinate reference system (default is 'EPSG:4326').
        """
        self.file_path = file_path
        self.target_crs = target_crs
        self.gdf = None
        self.merged_geometry = None

    def load_and_validate(self):
        """Loads the vector file, validates geometry, and reprojects if necessary."""
        # Ensure file exists
        if not os.path.exists(self.file_path):
            logger.error("AOI file does not exist at path: %s", self.file_path)
            raise AOIFileNotFoundError(self.file_path)

        # Read the vector dataset using GeoPandas
        try:
            logger.info("Reading AOI vector file: %s", self.file_path)
            self.gdf = gpd.read_file(self.file_path)
        except Exception as error:
            logger.error("Failed to parse vector file: %s", error)
            raise AOIFormatError(f"Could not open vector file '{self.file_path}'. Details: {error}")

        # Ensure the dataset is not empty
        if self.gdf.empty:
            logger.error("The AOI vector dataset is empty.")
            raise AOIGeometryError("The loaded AOI file contains no features or geometries.")

        # Check the CRS of the dataset
        if self.gdf.crs is None:
            logger.error("The AOI dataset lacks spatial reference (CRS).")
            raise AOICRSError("Vector dataset has no defined CRS. Please define a projection.")

        # Validate and fix invalid geometries (e.g., self-intersecting polygons)
        if not self.gdf.geometry.is_valid.all():
            logger.warning("Invalid geometries detected. Attempting automatic fix using buffer(0)...")
            self.gdf["geometry"] = self.gdf.geometry.buffer(0)

        # Reproject dataset if it doesn't match the target CRS
        current_crs = self.gdf.crs.to_string()
        if current_crs.upper() != self.target_crs.upper():
            logger.info("Reprojecting AOI from %s to %s...", current_crs, self.target_crs)
            try:
                self.gdf = self.gdf.to_crs(self.target_crs)
            except Exception as error:
                logger.error("Reprojection to %s failed: %s", self.target_crs, error)
                raise AOICRSError(f"Failed to reproject dataset to {self.target_crs}: {error}")

        # Merge features into a single Shapely geometry
        self.merged_geometry = unary_union(self.gdf.geometry)
        logger.info("AOI loaded and validated successfully.")
        return self.gdf

    def get_bbox(self) -> tuple[float, float, float, float]:
        """Returns the bounding box tuple: (minx, miny, maxx, maxy)."""
        if self.gdf is None:
            self.load_and_validate()
        bounds = self.gdf.total_bounds
        return (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))

    def get_geometry(self):
        """Returns the unified Shapely geometry object representing the AOI."""
        if self.merged_geometry is None:
            self.load_and_validate()
        return self.merged_geometry


    def geometry_geojson(self) -> dict:
        """ Returns the merged AOI geometry as a GeoJSON dict."""
        return self.get_geometry().__geo_interface__

    def area_ha(self) -> float:
        """ Returns total area in hectares using an equal-area projection"""
        if self.gdf is None:
            self.load_and_validate()
        projected = self.gdf.to_crs("EPSG:6933")
        return float(projected.geometry.area.sum()/10000.0)
