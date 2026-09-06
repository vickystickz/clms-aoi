"""Crop Land Type product."""

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
from clms_aoi.colors import convert_colors
from clms_aoi.exceptions import NoDataError

COLLECTION_ID = "4fa71893-371f-4440-97c4-917f569f67b2"

_CLASS_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: ["CTY", "dataMask"],
        output: { id: "default", bands: 2, sampleType: "UINT16" },
    };
}


function evaluatePixel(sample) {
    return {
        default: [sample.CTY, sample.dataMask],
    };
}
"""

_VISUALIZE_EVALSCRIPT = """
//VERSION=3

const factor = 1;
const offset = 0;

function setup() {
    return {
        input: ["CTY", "dataMask"],
        output: [
            { id: "default", bands: 4, sampleType: "UINT8" },
            { id: "index", bands: 1, sampleType: "FLOAT32" },
            { id: "browserStats", bands: 1, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1 },
        ],
    };
}

function evaluatePixel(samples) {
    const originalValue = samples.CTY;
    const val = originalValue * factor + offset;
    const dataMask = samples.dataMask;

    const EXCLUDED_VALUES = [0, 65535];
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
    [1110, [238, 110, 50]],
    [1120, [251, 162, 74]],
    [1130, [250, 220, 20]],
    [1140, [233, 67, 1]],
    [1150, [232, 169, 149]],
    [1210, [174, 199, 232]],
    [1220, [72, 151, 191]],
    [1310, [201, 140, 67]],
    [1320, [156, 91, 12]],
    [1410, [255, 121, 121]],
    [1420, [168, 106, 150]],
    [1430, [227, 119, 194]],
    [1440, [247, 182, 210]],
    [2100, [219, 219, 141]],
    [2200, [193, 206, 18]],
    [2310, [121, 160, 58]],
    [2320, [90, 124, 48]],
    [3100, [215, 215, 215]],
    [3200, [171, 171, 171]],
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

crop_type_colors = {
    1110: ([238, 110, 50],  "Wheat"),
    1120: ([251, 162, 74],  "Barley"),
    1130: ([250, 220, 20],  "Maize"),
    1140: ([233, 67, 1],    "Rice"),
    1150: ([232, 169, 149], "Other cereals"),
    1210: ([174, 199, 232], "Fresh Vegetables"),
    1220: ([72, 151, 191],  "Dry pulses"),
    1310: ([201, 140, 67],  "Potatoes"),
    1320: ([156, 91, 12],   "Sugar Beet"),
    1410: ([255, 121, 121], "Sunflower"),
    1420: ([168, 106, 150], "Soybeans"),
    1430: ([227, 119, 194], "Rapeseed"),
    1440: ([247, 182, 210], "Flax, cotton and hemp"),
    2100: ([219, 219, 141], "Grapes"),
    2200: ([193, 206, 18],  "Olives"),
    2310: ([121, 160, 58],  "Fruits"),
    2320: ([90, 124, 48],   "Nuts"),
    3100: ([215, 215, 215], "Unclassified arable crop"),
    3200: ([171, 171, 171], "Unclassified permanent crop"),
}


class CropLandTypeProduct(BaseProduct):

    """

    Crop Land Type product class for fetching and analyzing crop cover data.

     Attributes
        ----------
        collection_id : str
            The collection ID for the Crop Land Type product.

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

    @property
    def colors(self) -> dict:
        """Class name -> RGB (0-1) colour map for this product's crop-cover classes."""
        return convert_colors(crop_type_colors)

    def visualize(
        self,
        bbox: BoundingBox,
        geometry: dict,
        year: int,
        *,
        ax: Axes | None = None,
        show: bool = False,
    ) -> np.ndarray:
        """Method to fetch and display the color-mapped crop land type image for one year.


        This method returns the (H, W, 4) RGBA image array so callers can inspect or
        save it further (e.g. `plt.imsave(path, img)`).

        Parameters
        ----------
        bbox : BoundingBox
            The bounding box for the area of interest.
        geometry : dict
            The geometry of the area of interest in GeoJSON format.
        year : int
            The year for which to fetch the crop land type data.
        ax : Axes | None, optional
            The matplotlib Axes object to plot on. If None, a new figure and axes will be created. Default is None.
        show : bool, optional
            Whether to display the plot. Default is True.   
        """

        img = self._safe_request(geometry, year, evalscript=_VISUALIZE_EVALSCRIPT)
        if not np.any(img[..., 3] > 0):
            raise NoDataError(
                f"No valid pixels returned for year {year} within the requested AOI. "
                "This usually means the underlying Sentinel Hub collection has no "
                "scene covering that year — check the collection's available "
                "acquisition dates rather than assuming the request is broken."
            )

        if ax is None:
            _, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(img, extent=bbox, origin="upper")
        ax.set_title(f"Crop Land Type — {year}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend(
            handles=[
                Patch(color=[c / 255 for c in color], label=label)
                for color, label in crop_type_colors.values()
            ],
            loc="lower left",
            bbox_to_anchor=(1.01, 0),
        )

        if show:
            plt.tight_layout()
            plt.show()

        return img

    def fetch(self, bbox: BoundingBox, geometry: dict, year: int) -> np.ndarray:
        """ Method fetches raw per-pixel crop land type class codes for one year.

        Returns an (H, W, 2) array: band 0 is the CTY class code, band 1
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
            The year for which to fetch the crop land type data.

        Returns
        -------
        np.ndarray
            An (H, W, 2) array where band 0 contains the CTY class codes and band 1 contains the data mask (0 = no data).
        """
        return self._safe_request(
            geometry,
            year,
            evalscript=_CLASS_EVALSCRIPT,
            response_format=MimeType.TIFF,
        )

    def summarize(self, raw: np.ndarray) -> pd.DataFrame:
        """Method summarize a `fetch()` array into per-class pixel counts and area share.

        Parameters
        ----------
        raw : np.ndarray
            The raw array returned by the `fetch()` method, containing per-pixel crop land type class codes and data mask.
        """

        codes = raw[..., 0]
        # 0 and 65535 are CTY nodata/unclassified pixels, not real crop classes.
        # Only count pixels that are valid (dataMask > 0) and not in the excluded set.
        valid = (raw[..., 1] > 0) & ~np.isin(codes, [0, 65535])
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
                "class": crop_type_colors.get(int(code), ([0, 0, 0], f"Unknown ({int(code)})"))[1],
                "pixel_count": int(count),
                "pct": round(float(count) / total * 100, 2),
            }
            for code, count in zip(unique, counts)
        ]
        return pd.DataFrame(rows)
