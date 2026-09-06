from unittest.mock import patch

import numpy as np
import pytest

from clms_aoi.exceptions import NoDataError
from clms_aoi.products.corine_land_cover import CorineLandCover, lulucf_classes


def _make_product():
    return CorineLandCover(config=None)


def test_summarize_computes_pixel_counts_and_pct():
    raw = np.zeros((4, 4, 2), dtype=np.uint8)
    raw[..., 0] = 11  # forest land everywhere
    raw[0:2, 0:2, 0] = 31  # cropland in one quadrant
    raw[..., 1] = 1  # all pixels valid

    df = _make_product().summarize(raw)

    assert set(df["class"]) == {name for _, name in [
        lulucf_classes[11], lulucf_classes[31]]}
    assert df["pixel_count"].sum() == 16
    assert abs(df["pct"].sum() - 100) < 1e-6


def test_summarize_excludes_nodata_pixels():
    raw = np.zeros((2, 2, 2), dtype=np.uint8)
    raw[..., 0] = 11
    raw[..., 1] = 1
    raw[1, 1, 1] = 0  # tile dataMask says no-data, should not be counted
    raw[0, 1, 0] = 255  # LULUCF nodata sentinel value, should not be counted

    df = _make_product().summarize(raw)

    assert df.loc[0, "pixel_count"] == 2


def test_summarize_returns_empty_frame_when_all_nodata():
    raw = np.zeros((2, 2, 2), dtype=np.uint8)

    df = _make_product().summarize(raw)

    assert df.empty
    assert list(df.columns) == ["class", "pixel_count", "pct"]


def test_summarize_labels_unknown_class_codes():
    raw = np.zeros((1, 1, 2), dtype=np.uint8)
    raw[..., 0] = 99  # not present in lulucf_classes
    raw[..., 1] = 1

    df = _make_product().summarize(raw)

    assert df.loc[0, "class"] == "Unknown (99)"


def test_fetch_raises_no_data_error_when_year_has_no_valid_pixels():
    product = _make_product()
    empty_raw = np.zeros((4, 4, 2), dtype=np.uint8)  # dataMask all 0

    with patch.object(product, "_request_data", return_value=[empty_raw]):
        with pytest.raises(NoDataError, match="2099"):
            product.fetch(bbox=None, geometry={}, year=2099)


def test_fetch_returns_data_when_year_has_valid_pixels():
    product = _make_product()
    raw = np.zeros((4, 4, 2), dtype=np.uint8)
    raw[..., 0] = 11
    raw[..., 1] = 1

    with patch.object(product, "_request_data", return_value=[raw]):
        result = product.fetch(bbox=None, geometry={}, year=2021)

    assert np.array_equal(result, raw)


def test_visualize_raises_no_data_error_when_year_has_no_valid_pixels():
    product = _make_product()
    empty_img = np.zeros((4, 4, 4), dtype=np.uint8)  # alpha channel all 0

    with patch.object(product, "_request_data", return_value=[empty_img]):
        with pytest.raises(NoDataError, match="2099"):
            product.visualize(bbox=(0, 0, 1, 1), geometry={},
                               year=2099, show=False)
