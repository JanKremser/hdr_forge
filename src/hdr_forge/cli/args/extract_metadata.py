"""Argument parsing for the 'extract-metadata' subcommand."""

import argparse


def add_extract_metadata_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'extract-metadata' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    extract_parser: argparse.ArgumentParser = parser.add_parser(
        'extract-metadata',
        description="""
Extract Dolby Vision/HDR10 and/or HDR10Plus metadata from a encoded video file.
""",
        help='Extract Dolby Vision metadata'
    )

    extract_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input Video file'
    )

    extract_parser.add_argument(
        '-o', '--output',
        required=False,
        help='Output folder for extracted HDR-JSON, RPU and EL files'
    )

    extract_parser.add_argument(
        '--to-dv-8',
        action='store_true',
        required=False,
        help='Convert extracted Dolby Vision metadata to Profile 8.1 format'
    )

    extract_parser.add_argument(
        '--crop',
        action='store_true',
        required=False,
        help='Crop RPU active area offsets (passes --crop to dovi_tool)'
    )

    extract_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )
