"""Custom exception classes for the CLMS AOI package."""



class ClmsAoiError(Exception):
    """Base class for all errors in this package."""

    def __init__(self, message="An error occurred in the CLMS AOI module."):
        self.message = message
        super().__init__(self.message)
        

#  Handles Configuration errors 
class ConfigError(ClmsAoiError):
    """Base exception for config file errors."""

    def __init__(self, message="Configuration error encountered."):
        super().__init__(message)


class ConfigFileNotFoundError(ConfigError):
    """Raised when the YAML config file is not found."""

    def __init__(self, file_path=None):
        if file_path:
            msg = f"Config file not found at path: '{file_path}'"
        else:
            msg = "Config file path does not exist."
        super().__init__(msg)











class ConfigValidationError(ConfigError):
    """Raised when required keys are missing or values are the wrong type."""


# Handles AOI errors 

class AOIError(ClmsAoiError):
    """Base class for AOI loading/validation problems."""


class AOIFileNotFoundError(AOIError):
    """Raised when the AOI file path does not exist."""


class AOIFormatError(AOIError):
    """Raised when the AOI file can't be parsed as vector geometry."""


class AOIGeometryError(AOIError):
    """Raised when the AOI has no valid geometry, is empty, or is multi-feature
    when a single feature was expected."""


class AOICRSError(AOIError):
    """Raised when the AOI has no CRS and none was supplied, or reprojection fails."""


# Handles Authentication errors 

class AuthError(ClmsAoiError):
    """Base class for Sentinel Hub authentication problems."""


class MissingCredentialsError(AuthError):
    """Raised when client_id/client_secret are not found in config or env vars."""


class InvalidCredentialsError(AuthError):
    """Raised when Sentinel Hub rejects the credentials (bad id/secret)."""


class TokenRequestError(AuthError):
    """Raised when the OAuth token request fails for network/service reasons."""


# Handles product data errors

class ProductError(ClmsAoiError):
    """Base class for problems fetching or summarising product data."""


class NoDataError(ProductError):
    """Raised when a requested year returns no valid pixels for the AOI.

    This usually means the underlying Sentinel Hub collection has no scene
    covering that year, rather than a bug in the request itself.
    """
