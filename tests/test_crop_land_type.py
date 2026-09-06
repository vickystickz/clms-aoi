import numpy as np

from clms_aoi.products.crop_land_type import CropLandTypeProduct, crop_type_colors


def _make_product():
    return CropLandTypeProduct(config=None)


def test_summarize_computes_pixel_counts_and_pct():
    raw = np.zeros((4, 4, 2), dtype=np.uint16)
    raw[..., 0] = 1110  # wheat everywhere
    raw[0:2, 0:2, 0] = 1130  # maize in one quadrant
    raw[..., 1] = 1  # all pixels valid

    df = _make_product().summarize(raw)

    assert set(df["class"]) == {"Wheat", "Maize"}
    assert df.loc[df["class"] == "Maize", "pixel_count"].item() == 4
    assert df.loc[df["class"] == "Wheat", "pixel_count"].item() == 12
    assert abs(df["pct"].sum() - 100) < 1e-6


def test_summarize_excludes_nodata_pixels():
    raw = np.zeros((2, 2, 2), dtype=np.uint16)
    raw[..., 0] = 1110
    raw[..., 1] = 1
    raw[1, 1, 1] = 0  # tile dataMask says no-data, should not be counted
    raw[0, 1, 0] = 65535  # CTY nodata sentinel value, should not be counted

    df = _make_product().summarize(raw)

    assert df.loc[df["class"] == "Wheat", "pixel_count"].item() == 2


def test_summarize_excludes_zero_class_code():
    raw = np.zeros((1, 1, 2), dtype=np.uint16)
    raw[..., 0] = 0  # unclassified, should not be counted even though valid
    raw[..., 1] = 1

    df = _make_product().summarize(raw)

    assert df.empty


def test_summarize_returns_empty_frame_when_all_nodata():
    raw = np.zeros((2, 2, 2), dtype=np.uint16)

    df = _make_product().summarize(raw)

    assert df.empty
    assert list(df.columns) == ["class", "pixel_count", "pct"]


def test_summarize_labels_unknown_class_codes():
    raw = np.zeros((1, 1, 2), dtype=np.uint16)
    raw[..., 0] = 9999  # not present in crop_type_colors
    raw[..., 1] = 1

    df = _make_product().summarize(raw)

    assert df.loc[0, "class"] == "Unknown (9999)"


def test_colors_property_normalizes_rgb_by_class_name():
    colors = _make_product().colors

    assert colors["Wheat"] == (238 / 255, 110 / 255, 50 / 255)
    assert set(colors) == {name for _, name in crop_type_colors.values()}
