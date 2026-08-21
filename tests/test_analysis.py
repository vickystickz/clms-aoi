"""Tests for AnalysisResult.to_chart.

These characterize the current behaviour of to_chart before it is enhanced:
everything runs offline, inputs are built in memory, and assertions target
structure (a file is produced, the right errors are raised) rather than
pixels — pixel-level assertions are brittle and break on cosmetic changes.

Chart code writes an image file, so the checks here are deliberately about
"did it produce a valid, non-empty file for this input" rather than what the
chart looks like.
"""

import matplotlib

matplotlib.use("Agg")  # headless: no display needed in CI

import pandas as pd
import pytest

from clms_aoi.analysis import AnalysisResult


@pytest.fixture
def single_year_df():
    """A single-year summary in the shape _run() produces."""
    return pd.DataFrame(
        {
            "class": ["Tree cover", "Cropland", "Built-up", "Grassland"],
            "pixel_count": [5000, 3000, 1500, 500],
            "pct": [50.0, 30.0, 15.0, 5.0],
            "area_ha": [5000.0, 3000.0, 1500.0, 500.0],
            "year": [2020, 2020, 2020, 2020],
        }
    )


@pytest.fixture
def multi_year_df():
    """A multi-year summary: one row per (class, year) across three years."""
    rows = []
    data = {
        "Tree cover": {2018: 5400.0, 2021: 5100.0, 2024: 4700.0},
        "Cropland": {2018: 2600.0, 2021: 2800.0, 2024: 3000.0},
        "Built-up": {2018: 700.0, 2021: 950.0, 2024: 1300.0},
    }
    for cls, per_year in data.items():
        for yr, area in per_year.items():
            rows.append(
                {"class": cls, "pct": 0.0, "area_ha": area, "year": yr}
            )
    return pd.DataFrame(rows)


def test_to_chart_single_year_creates_file(single_year_df, tmp_path):
    out = tmp_path / "single.png"
    AnalysisResult(single_year_df).to_chart(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_to_chart_multi_year_creates_file(multi_year_df, tmp_path):
    out = tmp_path / "multi.png"
    AnalysisResult(multi_year_df).to_chart(out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_to_chart_returns_self_for_chaining(single_year_df, tmp_path):
    """to_chart returns the result so calls can chain (e.g. .to_csv().to_chart())."""
    result = AnalysisResult(single_year_df)
    assert result.to_chart(tmp_path / "c.png") is result


def test_to_chart_accepts_title(single_year_df, tmp_path):
    out = tmp_path / "titled.png"
    AnalysisResult(single_year_df).to_chart(out, title="Land cover 2020")
    assert out.exists()


def test_to_chart_jpg_suffix(single_year_df, tmp_path):
    """A .jpg path is written as JPEG without error."""
    out = tmp_path / "chart.jpg"
    AnalysisResult(single_year_df).to_chart(out)
    assert out.exists()


def test_to_chart_creates_parent_directory(single_year_df, tmp_path):
    """to_chart makes missing parent directories rather than failing."""
    out = tmp_path / "nested" / "deeper" / "chart.png"
    AnalysisResult(single_year_df).to_chart(out)
    assert out.exists()