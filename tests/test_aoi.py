import os
import warnings

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from clms_aoi.aoi import AOIHandler
from clms_aoi.exceptions import (
    AOICRSError,
    AOIFileNotFoundError,
    AOIFormatError,
    AOIGeometryError,
)
@pytest.fixture(params=[(".gpkg", "GPKG"), (".geojson", "GeoJSON")])
def sample_vector_file(request, tmp_path):
    """Fixture that generates both GPKG and GeoJSON test files in EPSG:4326."""
    ext, driver = request.param
    poly = Polygon([(13.0, 47.8), (13.1, 47.8), (13.1, 47.9), (13.0, 47.9), (13.0, 47.8)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly], crs="EPSG:4326")

    file_path = tmp_path / f"test_boundary{ext}"
    gdf.to_file(file_path, driver=driver)
    return str(file_path)


def test_aoi_load_and_bbox(sample_vector_file):
    """Tests loading valid vector files (GPKG & GeoJSON) and calculating bbox."""
    handler = AOIHandler(sample_vector_file, target_crs="EPSG:4326")
    handler.load_and_validate()

    bbox = handler.get_bbox()
    assert len(bbox) == 4
    assert bbox[0] == pytest.approx(13.0)
    assert bbox[1] == pytest.approx(47.8)


def test_aoi_file_not_found():
    """Tests that a missing file raises AOIFileNotFoundError."""
    handler = AOIHandler("non_existent_file.gpkg")
    with pytest.raises(AOIFileNotFoundError):
        handler.load_and_validate()


def test_aoi_missing_crs(tmp_path):
    """Tests that a dataset without CRS raises AOICRSError using GPKG format."""
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly])

    file_path = tmp_path / "no_crs.gpkg"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        gdf.to_file(file_path, driver="GPKG")

    handler = AOIHandler(str(file_path))
    with pytest.raises(AOICRSError):
        handler.load_and_validate()


@pytest.mark.parametrize("ext, driver", [(".gpkg", "GPKG"), (".geojson", "GeoJSON")])
def test_aoi_reproject(tmp_path, ext, driver):
    """Tests automatic reprojection from EPSG:4326 to a projected CRS."""
    poly = Polygon([(13.0, 47.8), (13.1, 47.8), (13.1, 47.9), (13.0, 47.9), (13.0, 47.8)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly], crs="EPSG:4326")

    file_path = tmp_path / f"reproject_test{ext}"
    gdf.to_file(file_path, driver=driver)

    handler = AOIHandler(str(file_path), target_crs="EPSG:32633")
    reprojected_gdf = handler.load_and_validate()

    assert reprojected_gdf.crs.to_string() == "EPSG:32633"


@pytest.mark.parametrize("ext, driver", [(".gpkg", "GPKG"), (".geojson", "GeoJSON")])
def test_aoi_empty_file(tmp_path, ext, driver):
    """Tests that loading an empty vector dataset raises AOIGeometryError."""
    gdf = gpd.GeoDataFrame(columns=["id", "geometry"], crs="EPSG:4326")

    file_path = tmp_path / f"empty{ext}"
    gdf.to_file(file_path, driver=driver)

    handler = AOIHandler(str(file_path))
    with pytest.raises(AOIGeometryError):
        handler.load_and_validate()

def test_aoi_area_ha():
    """ Test to ensure that area_ha returns correct hectares for a box of known size."""
    import geopandas as gpd
    from shapely.geometry import box

    # A 1000 m x 1000 m square in a metre-based CRS = exactly 100 ha.
    square_utm = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[box(500000, 5000000, 501000, 5001000)],
        crs="EPSG:32633",
    )
    # Convert to lon/lat, the CRS the handler expects.
    square_wgs84 = square_utm.to_crs("EPSG:4326")

    handler = AOIHandler("unused")
    handler.gdf = square_wgs84
    from shapely.ops import unary_union
    handler.merged_geometry = unary_union(square_wgs84.geometry)

    area = handler.area_ha()
    assert area == pytest.approx(100, rel=0.01)   # within 1% of 100 ha


def test_aoi_geometry_geojson(sample_vector_file):
    """Tests that geometry_geojson returns a valid GeoJSON geometry dict."""
    handler = AOIHandler(sample_vector_file, target_crs="EPSG:4326")
    handler.load_and_validate()

    gj = handler.geometry_geojson()
    assert isinstance(gj, dict)
    assert gj["type"] in {"Polygon", "MultiPolygon"}
    assert "coordinates" in gj