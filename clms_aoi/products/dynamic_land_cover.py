"""Dynamic Land Cover product."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Patch
from sentinelhub import MimeType

from clms_aoi.products.base import BaseProduct
from clms_aoi.aoi import BoundingBox

COLLECTION_ID = "828f6b20-8ffd-48f8-a1da-fefd271456db"

_CLASS_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: ["LCM10", "dataMask"],
        output: {
            bands: 2,
            sampleType: "UINT8",
        },
    };
}

function evaluatePixel(sample) {
    return [sample.LCM10, sample.dataMask];
}
"""


_VISUALIZE_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: ["LCM10", "dataMask"],
        output: {
            bands: 4,
            sampleType: "AUTO",
        },
    };
}

const map = [
    [10, 0x006400],
    [20, 0xffbb22],
    [30, 0xffff4c],
    [40, 0xf096ff],
    [50, 0x0096a0],
    [60, 0x00cf75],
    [70, 0xfae6a0],
    [80, 0xb4b4b4],
    [90, 0xfa0000],
    [100, 0x0064c8],
    [110, 0xf0f0f0],
    [254, 0x0a0a0a],
];

const visualizer = new ColorMapVisualizer(map);

function evaluatePixel(sample) {
    return visualizer.process(sample.LCM10).concat(sample.dataMask);
}
"""


lulc_colors = {
    10:  ([0, 100, 0],     "Tree cover"),
    20:  ([255, 187, 34],  "Shrubland"),
    30:  ([255, 255, 76],  "Grassland"),
    40:  ([240, 150, 255], "Cropland"),
    50:  ([250, 0, 0],     "Built-up"),
    60:  ([180, 180, 180], "Bare/sparse vegetation"),
    70:  ([240, 240, 240], "Snow and ice"),
    80:  ([0, 100, 200],   "Permanent water bodies"),
    90:  ([0, 150, 160],   "Herbaceous wetland"),
    95:  ([0, 207, 117],   "Mangroves"),
    100: ([250, 230, 160], "Moss and lichen"),
    254: ([10, 10, 10],    "Unclassifiable"),
}


class DynamicLandCover(BaseProduct):

    """

    Dynamic Land Cover product class for fetching and analyzing land cover data.

     Attributes
        ----------
        collection_id : str
            The collection ID for the Dynamic Land Cover product.

    Methods
        ----------
        visualize()
            Return a visualization of the product (e.g. a color map).
        fetch()
            Return a visualization of the product (e.g. a color map).
        summarize()
            Return a visualization of the product (e.g. a color map).
        statistics()
            Return a visualization of the product (e.g. a color map).
    """
    COLLECTION_ID = COLLECTION_ID

    def visualize(
        self,
        bbox: BoundingBox,
        geometry: dict,
        year: int,
        *,
        ax: Axes | None = None,
        show: bool = True,
    ) -> np.ndarray:
        """Method to fetch and display the color-mapped land cover image for one year.


        This method returns the (H, W, 4) RGBA image array so callers can inspect or
        save it further (e.g. `plt.imsave(path, img)`).

        Parameters
        ----------
        bbox : BoundingBox
            The bounding box for the area of interest.
        geometry : dict
            The geometry of the area of interest in GeoJSON format.
        year : int
            The year for which to fetch the land cover data.
        ax : Axes | None, optional
            The matplotlib Axes object to plot on. If None, a new figure and axes will be created. Default is None.
        show : bool, optional
            Whether to display the plot. Default is True.   
        """

        response = self._request_data(
            geometry,
            year,
            evalscript=_VISUALIZE_EVALSCRIPT,
        )
        img = response[0]

        if ax is None:
            _, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(img, extent=bbox, origin="upper")
        ax.set_title(f"Land Cover — {year}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend(
            handles=[
                Patch(color=[c / 255 for c in color], label=label)
                for color, label in lulc_colors.values()
            ],
            loc="lower left",
            bbox_to_anchor=(1.01, 0),
        )

        if show:
            plt.tight_layout()
            plt.show()

        return img

    def fetch(self, bbox: BoundingBox, geometry: dict, year: int) -> np.ndarray:
        """ Method fetches raw per-pixel land cover class codes for one year.

        Returns an (H, W, 2) array: band 0 is the LCM10 class code, band 1
        is the data mask (0 = no data). Uses TIFF output so class codes come
        back as exact integers rather than the color-mapped PNG used for
        `visualize`.

        Parameters
        ----------
        bbox : BoundingBox
            The bounding box for the area of interest.
        geometry : dict
            The geometry of the area of interest in GeoJSON format.
        year : int
            The year for which to fetch the land cover data.

        Returns
        -------
        np.ndarray
            An (H, W, 2) array where band 0 contains the LCM10 class codes and band 1 contains the data mask (0 = no data).
        """
        raw = self._request_data(
            geometry,
            year,
            evalscript=_CLASS_EVALSCRIPT,
            response_format=MimeType.TIFF,
        )
        return raw[0]

    def summarize(self, raw: np.ndarray) -> pd.DataFrame:
        """Method summarize a `fetch()` array into per-class pixel counts and area share.

        Parameters
        ----------
        raw : np.ndarray
            The raw array returned by the `fetch()` method, containing per-pixel land cover class codes and data mask.
        """

        codes = raw[..., 0]
        valid = raw[..., 1] > 0
        values = codes[valid]
        total = int(values.size)

        if total == 0:
            return pd.DataFrame({
                "class": pd.Series(dtype="object"),
                "pixel_count": pd.Series(dtype="int64"),
                "pct": pd.Series(dtype="float64"),
            })

        unique, counts = np.unique(values, return_counts=True)
        rows = [
            {
                "class": lulc_colors.get(int(code), ([0, 0, 0], f"Unknown ({int(code)})"))[1],
                "pixel_count": int(count),
                "pct": round(float(count) / total * 100, 2),
            }
            for code, count in zip(unique, counts)
        ]
        return pd.DataFrame(rows)
