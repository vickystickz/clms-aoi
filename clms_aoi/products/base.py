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
    """Abstract base for a CLMS product fetcher + summariser.

     Attributes
        ----------
        config : any
            The configuration object for the Sentinel Hub API.
        base_url : string
            The base URL for the Sentinel Hub API.

    Methods
        ----------
        _request_data()
            Call the Sentinel Hub Statistical API and return the parsed JSON.
        visualize()
            Return a visualization of the product (e.g. a color map).
    """

    #: Sentinel Hub collection ID (BYOC).
    COLLECTION_ID: str = ""

    def __init__(self, config: any, base_url: str = _CDSE_BASE_URL) -> None:
        self._config = config
        self._stats_url = base_url.rstrip("/") + _STATS_PATH

    @abstractmethod
    def visualize(self) -> Any:
        """Return a visualization of the product (e.g. a color map)."""

    @abstractmethod
    def summarize(self) -> Any:
        """Return a summary of the product (e.g. per-class pixel counts)."""

    def _request_data(
        self,
        geometry: dict | None,
        year: int,
        evalscript: str,
        resolution: float = 0.001,
        response_format: MimeType = MimeType.PNG,
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
                SentinelHubRequest.output_response(
                    "default", response_format),
            ],
            geometry=geometry,
            resolution=[resolution, resolution],
            config=self._config,
        )
        print("Request created successfully")
        return request.get_data()
