"""Command-line interface with logging configuration."""

import argparse
import logging
import sys

from .auth import SentinelHubAuthenticator
from .aoi import AOIHandler
from .config import ConfigLoader
from .exceptions import ClmsAoiError


def setup_logging(verbose: bool = False):
    """Sets up basic logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_validate_config(args):
    """Validates the given YAML configuration file."""
    try:
        config = ConfigLoader.load(args.path)
        logging.info(f"Config loaded successfully from '{args.path}'.")
        logging.info(f"Products configured: {config.products}")
        return 0
    except ClmsAoiError as error:
        logging.error(f"Config Validation Error: {error}")
        return 1


def cmd_check_auth(args):
    """Tests authentication against Sentinel Hub."""
    try:
        config = ConfigLoader.load(args.config)
        authenticator = SentinelHubAuthenticator(config.sentinelhub)
        token = authenticator.authenticate()
        logging.info("Authentication Successful!")
        logging.info(f"Access Token: {token[:15]}...")
        return 0
    except ClmsAoiError as error:
        logging.error(f"Authentication Failed: {error}")
        return 1


def cmd_check_aoi(args) -> int:
    """Validate vector GeoJSON or GeoPackage boundary file."""
    try:
        aoi = AOIHandler(args.aoi)
        aoi.load_and_validate()
        logging.info("AOI Valid! Bounding box: %s", aoi.get_bbox())
        return 0
    except ClmsAoiError as error:
        logging.error("AOI Validation Failed: %s", error)
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="clms-aoi", description="CLMS AOI Analysis Tool")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable debug logging output")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command to validate-config
    clms_validate = subparsers.add_parser(
        "validate-config", help="Validate YAML config file")
    clms_validate.add_argument("path", help="Path to config YAML file")

    # Command: check-auth
    clms_auth = subparsers.add_parser(
        "check-auth", help="Test Sentinel Hub authentication")
    clms_auth.add_argument("--config", default="config.yaml",
                           help="Path to config YAML file")

    # Command: check-aoi
    clms_aoi = subparsers.add_parser(
        "check-aoi", help="Validate vector AOI boundary file (.geojson or .gpkg)")
    clms_aoi.add_argument("--aoi", required=True,
                          help="Path to boundary vector file")

    args = parser.parse_args()

    # Configure logging based on user flags
    setup_logging(args.verbose)

    if args.command == "validate-config":
        sys.exit(cmd_validate_config(args))
    elif args.command == "check-auth":
        sys.exit(cmd_check_auth(args))
    elif args.command == "check-aoi":
        sys.exit(cmd_check_aoi(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
