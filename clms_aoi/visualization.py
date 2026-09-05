''' Visualization for CLMS AOI analysis results.'''
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
_FALLBACK = (0.6,0.6,0.6)

def plot_class_bars(
       df,
       path = None,
       *,
       colors = None,
       value = "area_ha",
       figsize = (12,6),
       title = None,

):
    ''' Plot per-class bar chart for a single year.
    The bars are colored according to the provided class colour mapping.
    Classes without a matching colour use a grey fallback.

    Parameters
    ---------
    df : pandas.DataFrame
        DataFrame containing class data.
    path: str or pathlib.Path, optional
        Path where the figure needs to be saved.
    colors: dict, optional
        Mapping of class names to normalized RGB tuples
        ``{class_name : (r,g,b)}`` . If None, all bars use grey color.
    value: {"area_ha", "pct"}, optional
        Column to plot.
    figsize: tuple, optional
        Figure size.
    title: str, optional
        Optional chart title.

    Returns
    --------
       The generated figure

    Raises
    -------
      ValueError
        If ``value`` is not "area_ha" or "pct".

    '''
    # Confirm if the value is valid
    if value not in {"area_ha", "pct"}:
        raise ValueError( "Value must be either 'area_ha" or "pct")
    if value not in df.columns:
        raise KeyError(f"value column {value!r} not found in DataFrame.")

    color_map = colors or {}
    class_column = "class" if "class" in df.columns else "density_class"

    #Sort the values in ascending order
    data = df.sort_values (value, ascending = False)

    #Look-up colors and grey as a fallback
    bar_colors = [
        color_map.get(class_name, _FALLBACK)
        for class_name in data[class_column]
    ]

    # Plot the bars
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(
        data[class_column],
        data[value],
        color = bar_colors,
    )
    ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=9)

    if value == "area_ha":
        ax.set_ylabel("Area (ha)")
    else:
        ax.set_ylabel("Percentage (%)")

    if title is not None:
        ax.set_title(title)

    ax.tick_params(axis='x', rotation = 45)
    fig.tight_layout()

    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        image_format = "jpeg" if path.suffix.lower() == ".jpg" else None
        fig.savefig(path, dpi=150, format=image_format)

    return fig

def plot_multiyear_bars(
    df,
    path=None,
    *,
    colors=None,
    value="area_ha",
    figsize=(13, 6),
    title=None,
):
    """Plot grouped bars comparing classes across multiple years.

    Bars are grouped by class and coloured by year. Semantic class colours apply to single-year
    charts.

    Saves to ``path`` if provided and returns the matplotlib figure.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing class, year, and value data.
    path : str or pathlib.Path, optional
        Path where the figure should be saved.
    colors : dict, optional
        Mapping of class names to normalized RGB tuples. This parameter is
        accepted for API consistency but multi-year bars are coloured by year.
    value : {"area_ha", "pct"}, optional
        Column to plot.
    figsize : tuple, optional
        Figure size.
    title : str, optional
        Optional chart title.

    Returns
    -------
        The generated figure.

    Raises
    ------
    ValueError
        If value is not "area_ha" or "pct".
    """

    # Confirm if the value is valid
    if value not in {"area_ha", "pct"}:
        raise ValueError( "Value must be either 'area_ha" or "pct")
    if value not in df.columns:
        raise KeyError(f"value column {value!r} not found in DataFrame.")
        

    # Keep the same API behaviour as plot_class_bars.
    # Multi-year charts are coloured by year, so this map is not used
    color_map = colors or {}

    class_col = (
        "class"
        if "class" in df.columns
        else "density_class"
    )

    # 3. Pivot: classes on x-axis, one bar per year
    pivot = (
        df.pivot(
            index=class_col,
            columns="year",
            values=value,
        )
        .fillna(0)
    )

    # #Sort the values in ascending order
    pivot = pivot.loc[
        pivot.sum(axis=1)
        .sort_values(ascending=False)
        .index
    ]

    # Create figure and axes
    fig, ax = plt.subplots(figsize=figsize)

    # Draw grouped bars, coloured by year
    pivot.plot(
        kind="bar",
        ax=ax,
    )

    # Add value labels to each year's bars
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f")

    # Set y-axis label
    if value == "area_ha":
        ax.set_ylabel("Area (ha)")
    else:
        ax.set_ylabel("Percentage (%)")

    # Optional title
    if title is not None:
        ax.set_title(title)

    # X-axis formatting
    ax.tick_params(axis="x", rotation=45)

    # Legend represents years
    ax.legend(
        title="Year",
    )

    fig.tight_layout()

    # Save if a path is provided
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        image_format = (
            "jpeg"
            if path.suffix.lower() == ".jpg"
            else None
        )

        fig.savefig(
            path,
            dpi=150,
            format=image_format,
        )

    return fig