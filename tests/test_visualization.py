"""Tests for clms_aoi.visualization.

Offline and self-contained: DataFrames are built in memory, no network or
credentials needed. Because the plotting functions return the matplotlib
figure, these assert on the figure's contents (bar count, colours) as well as
on the saved file — not just "a file appeared".
"""

import matplotlib

matplotlib.use("Agg")  # headless: no display needed in CI

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from clms_aoi.visualization import (
    _FALLBACK,
    plot_class_bars,
    plot_multiyear_bars,
)


@pytest.fixture
def single_year_df():
    return pd.DataFrame(
        {
            "class": ["Tree cover", "Cropland", "Built-up"],
            "pct": [60.0, 30.0, 10.0],
            "area_ha": [600.0, 300.0, 100.0],
        }
    )


@pytest.fixture
def multi_year_df():
    rows = []
    data = {
        "Tree cover": {2018: 540.0, 2021: 510.0},
        "Cropland": {2018: 260.0, 2021: 300.0},
    }
    for cls, per_year in data.items():
        for yr, area in per_year.items():
            rows.append({"class": cls, "area_ha": area, "year": yr})
    return pd.DataFrame(rows)


@pytest.fixture
def colors():
    return {
        "Tree cover": (0.0, 0.4, 0.0),
        "Cropland": (0.9, 0.6, 1.0),
        "Built-up": (1.0, 0.0, 0.0),
    }


# --- basic behaviour -------------------------------------------------------

def test_plot_class_bars_returns_figure(single_year_df):
    fig = plot_class_bars(single_year_df)
    assert fig is not None
    assert len(fig.axes) == 1
    plt.close(fig)


def test_plot_class_bars_draws_one_bar_per_class(single_year_df):
    fig = plot_class_bars(single_year_df)
    # One patch (bar) per class row.
    assert len(fig.axes[0].patches) == len(single_year_df)
    plt.close(fig)


def test_plot_class_bars_saves_file(single_year_df, tmp_path):
    out = tmp_path / "chart.png"
    fig = plot_class_bars(single_year_df, out)
    assert out.exists() and out.stat().st_size > 0
    plt.close(fig)


def test_plot_class_bars_no_path_writes_nothing(single_year_df, tmp_path):
    # Called without a path: returns a figure but writes no file.
    fig = plot_class_bars(single_year_df)
    assert list(tmp_path.iterdir()) == []
    plt.close(fig)


# --- the value toggle (new capability) -------------------------------------

def test_plot_class_bars_pct_value(single_year_df, tmp_path):
    out = tmp_path / "pct.png"
    fig = plot_class_bars(single_year_df, out, value="pct")
    assert out.exists()
    assert fig.axes[0].get_ylabel() == "Percentage (%)"   
    plt.close(fig)


def test_plot_class_bars_area_value_ylabel(single_year_df):
    fig = plot_class_bars(single_year_df, value="area_ha")
    assert fig.axes[0].get_ylabel() == "Area (ha)"
    plt.close(fig)


def test_plot_class_bars_invalid_value_raises(single_year_df):
    with pytest.raises(ValueError):
        plot_class_bars(single_year_df, value="nonsense")


# --- semantic colours (new capability) -------------------------------------

def test_plot_class_bars_applies_semantic_colors(single_year_df, colors):
    """Bars are coloured from the supplied map, matched by class name.

    Bars are sorted by value (Tree cover 600 > Cropland 300 > Built-up 100),
    so patch order is Tree cover, Cropland, Built-up. matplotlib stores colours
    as RGBA, so compare the first three channels with approx tolerance.
    """
    fig = plot_class_bars(single_year_df, colors=colors)
    patches = fig.axes[0].patches
    assert patches[0].get_facecolor()[:3] == pytest.approx((0.0, 0.4, 0.0))
    assert patches[2].get_facecolor()[:3] == pytest.approx((1.0, 0.0, 0.0))
    plt.close(fig)


def test_plot_class_bars_unknown_class_uses_grey_fallback():
    """A class name absent from the colour map falls back to grey, no error."""
    df = pd.DataFrame(
        {"class": ["Some Unmapped Class"], "area_ha": [100.0]}
    )
    fig = plot_class_bars(df, colors={"Tree cover": (0, 0.4, 0)})
    assert fig.axes[0].patches[0].get_facecolor()[:3] == pytest.approx(_FALLBACK)
    plt.close(fig)


def test_plot_class_bars_none_colors_all_grey(single_year_df):
    """colors=None must not crash; every bar uses the grey fallback."""
    fig = plot_class_bars(single_year_df, colors=None)
    for patch in fig.axes[0].patches:
        assert patch.get_facecolor()[:3] == pytest.approx(_FALLBACK)
    plt.close(fig)


# --- multi-year ------------------------------------------------------------

def test_plot_multiyear_bars_returns_figure(multi_year_df):
    fig = plot_multiyear_bars(multi_year_df)
    assert fig is not None
    plt.close(fig)


def test_plot_multiyear_bars_one_container_per_year(multi_year_df):
    # pivot.plot makes one bar container per year column.
    fig = plot_multiyear_bars(multi_year_df)
    assert len(fig.axes[0].containers) == multi_year_df["year"].nunique()
    plt.close(fig)


def test_plot_multiyear_bars_saves_file(multi_year_df, tmp_path):
    out = tmp_path / "multi.png"
    fig = plot_multiyear_bars(multi_year_df, out)
    assert out.exists() and out.stat().st_size > 0
    plt.close(fig)


def test_plot_multiyear_bars_invalid_value_raises(multi_year_df):
    with pytest.raises(ValueError):
        plot_multiyear_bars(multi_year_df, value="nonsense")