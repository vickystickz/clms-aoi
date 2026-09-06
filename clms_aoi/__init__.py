"""CLMS AOI — Copernicus Land Monitoring Service area-of-interest analysis tool."""

__version__ = "0.1.1"

from .config import ConfigLoader, SentinelHubCredentials
from .auth import SentinelHubAuthenticator
from .exceptions import ClmsAoiError
from .analysis import LandCover, ForestType, CropType

# The below define what gets exported when someone runs: from clms_aoi import *
__all__ = [
    "ConfigLoader",
    "SentinelHubCredentials",
    "SentinelHubAuthenticator",
    "ClmsAoiError",
    "LandCover",
    "ForestType",
    "CropType",
    "__version__",
]
