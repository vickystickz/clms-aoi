import numpy as np

from clms_aoi.products.forest_type import ForestTypeProduct


def _make_product():
    return ForestTypeProduct(config=None)


def test_summarize_computes_pixel_counts_and_pct():
    raw = np.zeros((4, 4, 2), dtype=np.uint8)
    raw[..., 0] = 1  # broadleaved forest everywhere
    raw[0:2, 0:2, 0] = 2  # coniferous forest in one quadrant
    raw[..., 1] = 1  # all pixels valid

    df = _make_product().summarize(raw)

    assert set(df["class"]) == {"Broadleaved forest", "Coniferous forest"}
    assert df.loc[df["class"] == "Coniferous forest", "pixel_count"].item() == 4
    assert df.loc[df["class"] == "Broadleaved forest", "pixel_count"].item() == 12
    assert abs(df["pct"].sum() - 100) < 1e-6


def test_summarize_excludes_nodata_pixels():
    raw = np.zeros((2, 2, 2), dtype=np.uint8)
    raw[..., 0] = 1
    raw[..., 1] = 1
    raw[1, 1, 1] = 0  # tile dataMask says no-data, should not be counted
    raw[0, 1, 0] = 255  # FTY nodata sentinel value, should not be counted

    df = _make_product().summarize(raw)

    assert df.loc[df["class"] == "Broadleaved forest", "pixel_count"].item() == 2


def test_summarize_returns_empty_frame_when_all_nodata():
    raw = np.zeros((2, 2, 2), dtype=np.uint8)

    df = _make_product().summarize(raw)

    assert df.empty
    assert list(df.columns) == ["class", "pixel_count", "pct"]


def test_summarize_labels_non_forest_class():
    raw = np.zeros((1, 1, 2), dtype=np.uint8)
    raw[..., 0] = 0  # non-forest
    raw[..., 1] = 1

    df = _make_product().summarize(raw)

    assert df.loc[0, "class"] == "Non-forest"


def test_summarize_labels_unknown_class_codes():
    raw = np.zeros((1, 1, 2), dtype=np.uint8)
    raw[..., 0] = 200  # not present in forest_type_classes
    raw[..., 1] = 1

    df = _make_product().summarize(raw)

    assert df.loc[0, "class"] == "Unknown (200)"
