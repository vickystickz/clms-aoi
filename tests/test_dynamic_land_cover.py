import numpy as np

from clms_aoi.products.dynamic_land_cover import DynamicLandCover


def _make_product():
    return DynamicLandCover(config=None)


def test_summarise_computes_pixel_counts_and_pct():
    raw = np.zeros((4, 4, 2), dtype=np.uint8)
    raw[..., 0] = 10  # tree cover everywhere
    raw[0:2, 0:2, 0] = 80  # water in one quadrant
    raw[..., 1] = 1  # all pixels valid

    df = _make_product().summarise(raw)

    assert set(df["class"]) == {"Tree cover", "Permanent water bodies"}
    assert df.loc[df["class"] == "Permanent water bodies", "pixel_count"].item() == 4
    assert df.loc[df["class"] == "Tree cover", "pixel_count"].item() == 12
    assert abs(df["pct"].sum() - 100) < 1e-6


def test_summarise_excludes_nodata_pixels():
    raw = np.zeros((2, 2, 2), dtype=np.uint8)
    raw[..., 0] = 10
    raw[..., 1] = 1
    raw[1, 1, 1] = 0  # one no-data pixel, should not be counted

    df = _make_product().summarise(raw)

    assert df.loc[df["class"] == "Tree cover", "pixel_count"].item() == 3


def test_summarise_returns_empty_frame_when_all_nodata():
    raw = np.zeros((2, 2, 2), dtype=np.uint8)

    df = _make_product().summarise(raw)

    assert df.empty
    assert list(df.columns) == ["class", "pixel_count", "pct"]


def test_summarise_labels_unknown_class_codes():
    raw = np.zeros((1, 1, 2), dtype=np.uint8)
    raw[..., 0] = 200  # not present in lulc_colors
    raw[..., 1] = 1

    df = _make_product().summarise(raw)

    assert df.loc[0, "class"] == "Unknown (200)"
