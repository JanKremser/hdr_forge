"""Argument parsing for the 'inject-metadata' subcommand."""

import argparse


def add_inject_metadata_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'inject-metadata' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    inject_parser: argparse.ArgumentParser = parser.add_parser(
        'inject-metadata',
        description="""
Inject Dolby Vision/HDR10 and/or HDR10Plus metadata into an existing HEVC video stream, without re-encoding.
NVENC GPU-encoded videos cannot be retroactively assigned HDR metadata using this function.
Only CPU-encoded videos can be retroactively assigned HDR metadata.
""",
        help='Inject Dolby Vision metadata'
    )

    inject_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input Video file'
    )

    inject_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output video file'
    )

    inject_parser.add_argument(
        '--rpu',
        required=False,
        help="""
Path to the RPU file containing Dolby Vision metadata to be injected.
Example:
    --rpu "path/to/dolby_vision.rpu"
"""
    )

    inject_parser.add_argument(
        '--el',
        required=False,
        help="""
Path to the EL file containing Dolby Vision enhancement layer data to be injected.
The ".hevc" extension is important; without this change, an error will occur.
Example:
    --el "path/to/dolby_vision.hevc"
"""
    )

    inject_parser.add_argument(
        '--hdr10',
        required=False,
        help="""
Path to HDR10 metadata JSON file to be injected.
Example:
    --hdr10 "path/to/hdr10_metadata.json"
"""
    )

    inject_parser.add_argument(
        '--hdr10plus',
        required=False,
        help="""
Path to HDR10 metadata JSON file to be injected.
Example:
    --hdr10plus "path/to/hdr10plus_metadata.json"
"""
    )

    inject_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )
