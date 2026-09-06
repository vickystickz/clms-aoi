from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import pandas as pd

from clms_aoi.aoi import AOIHandler
from clms_aoi.auth import SentinelHubAuthenticator
from clms_aoi.config import ConfigLoader
from clms_aoi.exceptions import ClmsAoiError, NoDataError, ProductError
from clms_aoi.outputs import write_csv
from clms_aoi.products.dynamic_land_cover import DynamicLandCover
from clms_aoi.products.forest_type import ForestTypeProduct
from clms_aoi.products.crop_land_type import CropLandTypeProduct

logger = logging.getLogger(__name__)


def _resolve_years(year: int | None, years: Iterable[int] | None) -> list[int]:
    if year is not None and years is not None:
        raise ValueError("Pass year= or years=, not both.")
    if year is not None:
        return [int(year)]
    if years is not None:
        return [int(y) for y in years]
    raise ValueError("Provide year= or years=.")


class AnalysisResult:
    """Holds the summary DataFrame and provides output helpers."""

    def __init__(self, df: pd.DataFrame, colors: dict | None = None) -> None:
        self._df = df
        self._colors = colors or {}

    @property
    def data(self) -> pd.DataFrame:
        return self._df

    def to_csv(self, path: str | Path) -> "AnalysisResult":
        write_csv(self._df, path)
        return self

    def to_chart(
        self,
        path: str | Path,
        *,
        value: str = "area_ha",
        figsize: tuple[int, int] = (12, 6),
        title: str | None = None,
    ) -> "AnalysisResult":
        from clms_aoi.visualization import plot_class_bars, plot_multiyear_bars

        multi_year = "year" in self._df.columns and self._df["year"].nunique(
        ) > 1
        draw = plot_multiyear_bars if multi_year else plot_class_bars
        fig = draw(self._df, path, colors=self._colors,
                   value=value, figsize=figsize, title=title)
        plt.close(fig)
        return self

    def __repr__(self) -> str:
        return f"AnalysisResult({len(self._df)} rows)"


class _BaseAnalyser:
    def __init__(self, config_path: str | Path) -> None:
        cfg = ConfigLoader.load(config_path)
        authenticator = SentinelHubAuthenticator(cfg.sentinelhub)
        self._token_cache = authenticator.get_sh_config(save_profile=None)

    def _load_aoi(self, aoi: str | Path) -> AOIHandler:
        handler = AOIHandler(aoi)
        handler.load_and_validate()
        return handler

    def _run(
        self,
        product: DynamicLandCover | ForestTypeProduct | CropLandTypeProduct,
        aoi: str | Path,
        year: int | None,
        years: Iterable[int] | None,
    ) -> AnalysisResult:
        resolved = _resolve_years(year, years)
        handler = self._load_aoi(aoi)
        bbox = handler.get_bbox()
        geometry = handler.geometry_geojson()
        aoi_area_ha = handler.area_ha()

        frames: list[pd.DataFrame] = []
        for y in resolved:
            try:
                raw = product.fetch(bbox, geometry, y)
                df = product.summarize(raw)
            except ClmsAoiError:
                raise
            except Exception as exc:
                logger.error(
                    "Failed to fetch/summarize %s for year %s: %s",
                    type(product).__name__, y, exc,
                )
                raise ProductError(
                    f"Failed to fetch or summarize data for year {y}: {exc}"
                ) from exc
            if df.empty:
                raise NoDataError(
                    f"No valid pixels returned for year {y} within the requested AOI. "
                    "This usually means the underlying Sentinel Hub collection has no "
                    "scene covering that year — check the collection's available "
                    "acquisition dates rather than assuming the request is broken."
                )
            df["area_ha"] = (df["pct"] / 100 * aoi_area_ha).round(2)
            df["year"] = y
            frames.append(df)

        combined = pd.concat(frames, ignore_index=True)
        return AnalysisResult(combined, colors=product.colors)

    def _visualize(
        self,
        product: DynamicLandCover | ForestTypeProduct | CropLandTypeProduct,
        aoi: str | Path,
        year: int,
        show: bool,
    ) -> Any:
        handler = self._load_aoi(aoi)
        try:
            return product.visualize(
                handler.get_bbox(), handler.geometry_geojson(), year, show=show
            )
        except ClmsAoiError:
            raise
        except Exception as exc:
            logger.error(
                "Failed to visualize %s for year %s: %s",
                type(product).__name__, year, exc,
            )
            raise ProductError(
                f"Failed to visualize data for year {year}: {exc}"
            ) from exc


class LandCover(_BaseAnalyser):
    """Analyse Dynamic Land Cover for an area of interest.

    Parameters
    ----------
    config_path:
        Path to the YAML configuration file containing Sentinel Hub credentials.

    Examples
    --------
    >>> lc = LandCover("config.yml")
    >>> result = lc.analyse(aoi="boundary.geojson", year=2020)
    >>> result.to_csv("landcover.csv").to_chart("landcover.jpg")
    >>> lc.visualize(aoi="boundary.geojson", year=2020)
    """

    def __init__(self, config_path: str | Path) -> None:
        super().__init__(config_path)
        self._product = DynamicLandCover(self._token_cache)

    def analyse(
        self,
        aoi: str | Path,
        *,
        year: int | None = None,
        years: Iterable[int] | None = None,
    ) -> AnalysisResult:
        """Fetch and summarise land cover for *aoi*.

        Pass exactly one of *year* (single int) or *years* (list/range of ints).
        """
        return self._run(self._product, aoi, year=year, years=years)

    def visualize(self, aoi: str | Path, *, year: int, show: bool = True) -> Any:
        """Fetch and display the color-mapped land cover map for *aoi* and *year*."""
        return self._visualize(self._product, aoi, year, show)


class ForestType(_BaseAnalyser):
    """Analyse Forest Type (broadleaved / coniferous) for an area of interest.

    Parameters
    ----------
    config_path:
        Path to the YAML configuration file containing Sentinel Hub credentials.

    Examples
    --------
    >>> ft = ForestType("config.yml")
    >>> result = ft.analyse(aoi="boundary.geojson", years=[2018, 2021])
    >>> result.to_csv("forest_type.csv").to_chart("forest_type.jpg")
    >>> ft.visualize(aoi="boundary.geojson", year=2021)
    """

    def __init__(self, config_path: str | Path) -> None:
        super().__init__(config_path)
        self._product = ForestTypeProduct(self._token_cache)

    def analyse(
        self,
        aoi: str | Path,
        *,
        year: int | None = None,
        years: Iterable[int] | None = None,
    ) -> AnalysisResult:
        """Fetch and summarise forest type for *aoi*.

        Pass exactly one of *year* (single int) or *years* (list/range of ints).
        """
        return self._run(self._product, aoi, year=year, years=years)

    def visualize(self, aoi: str | Path, *, year: int, show: bool = True) -> Any:
        """Fetch and display the color-mapped forest type map for *aoi* and *year*."""
        return self._visualize(self._product, aoi, year, show)


class CropType(_BaseAnalyser):
    """Analyse Crop land Type for an area of interest.

    Parameters
    ----------
    config_path:
        Path to the YAML configuration file containing Sentinel Hub credentials.

    Examples
    --------
    >>> clt = CropLandType("config.yml")
    >>> result = clt.analyse(aoi="boundary.geojson", year=2020)
    >>> result.to_csv("croplandtype.csv").to_chart("croplandtype.jpg")
    >>> clt.visualize(aoi="boundary.geojson", year=2020)
    """

    def __init__(self, config_path: str | Path) -> None:
        super().__init__(config_path)
        self._product = CropLandTypeProduct(self._token_cache)

    def analyse(
        self,
        aoi: str | Path,
        *,
        year: int | None = None,
        years: Iterable[int] | None = None,
    ) -> AnalysisResult:
        """Fetch and summarize crop type cover for *aoi*.

        Pass exactly one of *year* (single int) or *years* (list/range of ints).
        """
        return self._run(self._product, aoi, year=year, years=years)

    def visualize(self, aoi: str | Path, *, year: int, show: bool = True) -> Any:
        """Fetch and display the color-mapped crop type map for *aoi* and *year*."""
        return self._visualize(self._product, aoi, year, show)
