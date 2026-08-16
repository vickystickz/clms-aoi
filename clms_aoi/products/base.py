"""Shared interface that every product module implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sentinelhub import (
    DataCollection,
    SentinelHubRequest,
    CRS,
    MimeType,
    Geometry,
)


_CDSE_BASE_URL = "https://sh.dataspace.copernicus.eu"
_STATS_PATH = "/api/v1/statistics"


class BaseProduct(ABC):
    """Abstract base for a CLMS product fetcher + summariser."""

    #: Sentinel Hub collection ID (BYOC).
    COLLECTION_ID: str = ""

    def __init__(self, config: any, base_url: str = _CDSE_BASE_URL) -> None:
        self._config = config
        self._stats_url = base_url.rstrip("/") + _STATS_PATH

    @abstractmethod
    def visualize() -> Any:
        """Return a visualization of the product (e.g. a color map)."""

    @abstractmethod
    def statistics() -> Any:
        """Return a visualization of the product (e.g. a color map)."""

    def _request_data(
        self,
        bbox:  tuple[float, float, float, float],
        geometry: dict | None,
        year: int,
        evalscript: str,
        resolution: float = 0.001,
    ) -> Any:
        """Call the Sentinel Hub Statistical API and return the parsed JSON."""
        geometry = Geometry(geometry, crs=CRS.WGS84)
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.define_byoc(
                        self.COLLECTION_ID
                    ),
                    time_interval=(f"{year}-01-01", f"{year}-12-31"),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response("default", MimeType.PNG),
            ],
            geometry=geometry,
            resolution=[resolution, resolution],
            config=self._config,
        )
        print("Request created successfully")
        return request.get_data()
