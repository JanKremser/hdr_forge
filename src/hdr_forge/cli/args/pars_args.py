"""Command-line argument parsing for HDR Forge."""

import argparse

from hdr_forge import __version__
from hdr_forge.cli.cli_output import rainbow_text
from hdr_forge.cli.args.info import add_info_subcommand
from hdr_forge.cli.args.detect_logo import add_detect_logo_subcommand
from hdr_forge.cli.args.convert import add_convert_subcommand
from hdr_forge.cli.args.extract_metadata import add_extract_metadata_subcommand
from hdr_forge.cli.args.inject_metadata import add_inject_metadata_subcommand
from hdr_forge.cli.args.edit import add_edit_subcommand


HDR_FORGE_LOGO = rainbow_text("""
    █▒   ▒█ █▀▀▀▀▄  █▀▀▀█       █▀▀▀▀▀ █▀▀▀▀█ █▀▀▀█▄ █▀▀▀▀ █▀▀▀▀▀
    ███████ █     █ ██▀▀▀       █▀▀▀   █    █ ██▀▀▀  █ ▄▄▄ █▀▀▀
    █▒   ▒█ █▄▄▄▄▀  █ ▀▄▄       █      █▄▄▄▄█ █ ▀▄▄  █▄▄▄█ █▄▄▄▄▄
  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄""")


def _add_version_arg(parser: argparse.ArgumentParser) -> None:
    """Add version argument to the parser.

    Args:
        parser: Argument parser to add the version argument to
    """
    parser.add_argument(
        '--version',
        action='version',
        version=f"""          HDR forge {__version__} - © JanKremser"""
    )


def parse_args():
    """Parse command-line arguments with subcommands.

    Returns:
        Parsed arguments namespace
    """
    print(HDR_FORGE_LOGO + "\n")
    parser = argparse.ArgumentParser(
        description='HDR Forge - HDR Video Converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    _add_version_arg(parser=parser)

    # Create subcommands
    subparsers: argparse._SubParsersAction = parser.add_subparsers(dest='command', help='Subcommand')
    subparsers.required = True

    add_info_subcommand(parser=subparsers)
    add_detect_logo_subcommand(parser=subparsers)
    add_convert_subcommand(parser=subparsers)
    add_extract_metadata_subcommand(parser=subparsers)
    add_inject_metadata_subcommand(parser=subparsers)
    add_edit_subcommand(parser=subparsers)

    return parser.parse_args()
