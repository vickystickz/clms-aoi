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

from clms_aoi.exceptions import NoDataError


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

    def _safe_request(
        self,
        geometry: dict,
        year: int,
        *,
        evalscript: str,
        response_format: MimeType = MimeType.PNG,
    ) -> Any:
        """Call `_request_data` and turn any fetch failure into a `NoDataError`.

        Covers both hard failures (network/API errors, an empty response list)
        and the case where the request succeeds but the year has no scene
        covering the AOI.
        """
        try:
            response = self._request_data(
                geometry,
                year,
                evalscript=evalscript,
                response_format=response_format,
            )
            return response[0]
        except Exception as exc:
            raise NoDataError(
                f"Could not fetch data for year {year} within the requested AOI: {exc}. "
                "This usually means the underlying Sentinel Hub collection has no "
                "scene covering that year — check the collection's available "
                "acquisition dates rather than assuming the request is broken."
            ) from exc
