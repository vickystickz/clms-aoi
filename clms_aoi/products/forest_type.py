"""Forest Type product."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Patch
from sentinelhub import MimeType

from clms_aoi.aoi import BoundingBox
from clms_aoi.products.base import BaseProduct


# Collection ID and EVALSCRIPT for the Forest Type product
COLLECTION_ID = "4d1aad1a-f800-43c5-87d0-5565a9a31c12"

# Dates Available: 2018, 2021, 2024

# EVALSCRIPT is used for visualization and statistics, while _CLASS_EVALSCRIPT is used for fetching raw class codes.


_CLASS_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: ["FTY", "dataMask"],
        output: {
            bands: 2,
            sampleType: "UINT8",
        },
    };
}

function evaluatePixel(sample) {
    return [sample.FTY, sample.dataMask];
}
"""


EVALSCRIPT = """
//VERSION=3
const factor = 1;
const offset = 0;
function setup() {
    return {
        input: ["FTY", "dataMask"],
        output: [
            { id: "default", bands: 4, sampleType: "UINT8" },
            { id: "index", bands: 1, sampleType: "FLOAT32" },
            { id: "browserStats", bands: 1, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1 },
        ],
    };
}

function evaluatePixel(samples) {
    const originalValue = samples.FTY;
    const val = originalValue * factor + offset;
    const dataMask = samples.dataMask;

    const EXCLUDED_VALUES = [0, 255];
    const isExcluded = dataMask === 0 || EXCLUDED_VALUES.includes(val);

    if (isExcluded) {
        return {
            default: [0, 0, 0, 0],
            index: [NaN],
            browserStats: [val],
            dataMask: [dataMask],
        };
    }

    const imgVals = getColor(originalValue);
    return {
        default: imgVals.concat(dataMask * 255),
        index: [val],
        browserStats: [val],
        dataMask: [dataMask],
    };
}

const ColorBar = [
    [1, [70, 158, 74]], // broadleaved forest
    [2, [28, 92, 36]], // coniferous forest
];
function getColor(value) {
    const closestEntry = ColorBar.reduce((prev, curr) => {
        return Math.abs(curr[0] - value) < Math.abs(prev[0] - value)
            ? curr
            : prev;
    });

    const [_, color] = closestEntry;
    return [color[0], color[1], color[2]];
}
"""


# The following dictionary maps the FTY class codes to their corresponding RGB colors and human-readable labels.
forest_type_classes = {
    0: ([189, 189, 189], "Non-forest"),
    1: ([70, 158, 74], "Broadleaved forest"),
    2: ([28, 92, 36], "Coniferous forest"),
}

# FTY pixel value used as the "no data" sentinel, distinct from the tile
# dataMask which flags pixels outside the collection's coverage.
_NODATA_VALUE = 255


class ForestTypeProduct(BaseProduct):
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
        """Fetch and display the color-mapped forest type image for one year.

        Returns the (H, W, 4) RGBA image array so callers can inspect or
        save it further (e.g. `plt.imsave(path, img)`).
        """
        response = self._request_data(
            geometry,
            year,
            evalscript=EVALSCRIPT,
        )
        img = response[0]

        if ax is None:
            _, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(img, extent=bbox, origin="upper")
        ax.set_title(f"Forest Type — {year}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend(
            handles=[
                Patch(color=[c / 255 for c in color], label=label)
                for color, label in forest_type_classes.values()
            ],
            loc="lower left",
            bbox_to_anchor=(1.01, 0),
        )

        if show:
            plt.tight_layout()
            plt.show()

        return img

    def fetch(self, bbox: BoundingBox, geometry: dict, year: int) -> np.ndarray:
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

            Returns
            -------
            np.ndarray
                The raw array returned by the `fetch()` method, containing per-pixel forest type class codes and data mask.  
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
                The raw array returned by the `fetch()` method, containing per-pixel forest type class codes and data mask.
        """
        codes = raw[..., 0]
        valid = (raw[..., 1] > 0) & (codes != _NODATA_VALUE)
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
                "class": forest_type_classes.get(int(code), ([0, 0, 0], f"Unknown ({int(code)})"))[1],
                "pixel_count": int(count),
                "pct": round(float(count) / total * 100, 2),
            }
            for code, count in zip(unique, counts)
        ]
        return pd.DataFrame(rows)
