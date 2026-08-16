
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

COLLECTION_ID = "714b4c8d-2d89-4ed8-933c-f7c8bb7a1d4b"


# Reference years: 2018, 2021, 2022, 2023 (annual from 2021 onward).

_CLASS_EVALSCRIPT = """
//VERSION=3

function setup() {
    return {
        input: ["LULUCF_INSTANCE", "dataMask"],
        output: {
            bands: 2,
            sampleType: "UINT8",
        },
    };
}

function evaluatePixel(sample) {
    return [sample.LULUCF_INSTANCE, sample.dataMask];
}
"""

EVALSCRIPT = """
//VERSION=3
const factor = 1;
const offset = 0;
function setup() {
    return {
        input: ["LULUCF_INSTANCE", "dataMask"],
        output: [
            { id: "default", bands: 4, sampleType: "UINT8" },
            { id: "index", bands: 1, sampleType: "FLOAT32" },
            { id: "browserStats", bands: 1, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1 },
        ],
    };
}

function evaluatePixel(samples) {
    const originalValue = samples.LULUCF_INSTANCE;
    const val = originalValue * factor + offset;
    const dataMask = samples.dataMask;

    const EXCLUDED_VALUES = [255];
    const isExcluded =
        dataMask === 0 || EXCLUDED_VALUES.includes(originalValue);

    if (isExcluded) {
        return {
            default: [0, 0, 0, 0],
            index: [NaN],
            browserStats: [val],
            dataMask: [dataMask],
        };
    }

    const imgVals = getColor(val);
    return {
        default: imgVals.concat(dataMask * 255),
        index: [val],
        browserStats: [val],
        dataMask: [dataMask],
    };
}

const ColorBar = [
    [11, [91, 12, 1]],
    [12, [191, 2, 40]],
    [13, [244, 38, 54]],
    [14, [255, 107, 33]],
    [21, [16, 29, 16]],
    [22, [1, 42, 15]],
    [23, [2, 62, 22]],
    [24, [4, 85, 31]],
    [25, [5, 117, 42]],
    [31, [126, 124, 17]],
    [32, [196, 122, 70]],
    [33, [249, 158, 89]],
    [34, [249, 208, 89]],
    [41, [189, 255, 26]],
    [42, [17, 164, 6]],
    [43, [22, 193, 6]],
    [44, [27, 237, 8]],
    [45, [128, 237, 8]],
    [51, [12, 178, 255]],
    [52, [10, 152, 217]],
    [53, [0, 98, 252]],
    [54, [1, 5, 205]],
    [55, [33, 96, 162]],
    [61, [89, 88, 88]],
    [62, [130, 129, 129]],
    [63, [168, 167, 167]],
    [64, [204, 205, 205]],
    [254, [247, 247, 247]],
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


# The 27 classes are two-digit codes: tens digit = one of the six main
# LULUCF categories, ones digit = a sub-class within it (4 + 5 + 4 + 5 + 5 +
# 4 = 27, matching the product's documented class count). Code 254 falls
# outside that scheme. The product's public docs don't name the individual
# sub-classes, so they're labeled with their parent category + code;
# replace with official names if/when available. Colors are copied from the
# `ColorBar` in the evalscript above.
_lulucf_categories = {
    1: "Forest land",
    2: "Grassland",
    3: "Cropland",
    4: "Settlements",
    5: "Wetlands",
    6: "Other land",
}

_color_by_code = {
    11: [91, 12, 1], 12: [191, 2, 40], 13: [244, 38, 54], 14: [255, 107, 33],
    21: [16, 29, 16], 22: [1, 42, 15], 23: [2, 62, 22], 24: [4, 85, 31], 25: [5, 117, 42],
    31: [126, 124, 17], 32: [196, 122, 70], 33: [249, 158, 89], 34: [249, 208, 89],
    41: [189, 255, 26], 42: [17, 164, 6], 43: [22, 193, 6], 44: [27, 237, 8], 45: [128, 237, 8],
    51: [12, 178, 255], 52: [10, 152, 217], 53: [0, 98, 252], 54: [1, 5, 205], 55: [33, 96, 162],
    61: [89, 88, 88], 62: [130, 129, 129], 63: [168, 167, 167], 64: [204, 205, 205],
    254: [247, 247, 247],
}

lulucf_classes = {
    code: (
        color,
        f"{_lulucf_categories[code // 10]} ({code})"
        if code // 10 in _lulucf_categories
        else f"Unclassified ({code})",
    )
    for code, color in _color_by_code.items()
}

_color_to_label = {tuple(rgb): label for rgb, label in lulucf_classes.values()}

_NODATA_VALUE = 255


class CorineLandCover(BaseProduct):
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
        """Fetch and display the color-mapped LULUCF Instance image for one year.

        The legend is built from colors actually present in the returned
        image rather than all 27 classes, since most AOIs only cover a
        handful of them.

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
        ax.set_title(f"CLCplus LULUCF Instance — {year}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        visible = img[img[..., 3] > 0][..., :3]
        present_colors = {tuple(rgb) for rgb in np.unique(
            visible, axis=0).tolist()} if visible.size else set()
        handles = [
            Patch(
                color=[c / 255 for c in rgb],
                label=_color_to_label.get(rgb, f"Unknown {rgb}"),
            )
            for rgb in sorted(present_colors)
        ]
        if handles:
            ax.legend(
                handles=handles,
                loc="lower left",
                bbox_to_anchor=(1.01, 0),
                fontsize="small",
            )

        if show:
            plt.tight_layout()
            plt.show()

        return img

    def fetch(self, bbox: BoundingBox, geometry: dict, year: int) -> np.ndarray:
        """Fetch raw per-pixel LULUCF Instance class codes for one year.

        Returns an (H, W, 2) array: band 0 is the LULUCF_INSTANCE class
        code, band 1 is the data mask (0 = no data). Uses TIFF output so
        class codes come back as exact integers rather than the
        color-mapped PNG used for `visualize`.
        """
        raw = self._request_data(
            geometry,
            year,
            evalscript=_CLASS_EVALSCRIPT,
            response_format=MimeType.TIFF,
        )
        return raw[0]

    def summarise(self, raw: np.ndarray) -> pd.DataFrame:
        """Summarise a `fetch()` array into per-class pixel counts and area share."""
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
                "class": lulucf_classes.get(int(code), ([0, 0, 0], f"Unknown ({int(code)})"))[1],
                "pixel_count": int(count),
                "pct": round(float(count) / total * 100, 2),
            }
            for code, count in zip(unique, counts)
        ]
        return pd.DataFrame(rows)

    def statistics(self, bbox: BoundingBox, geometry: dict, year: int) -> Any:
        result = np.random.rand(10, 10)  # Placeholder for actual stats
        print(
            f"Returned data is of type = {'stats'} and length {len(result)}.")
        return result
