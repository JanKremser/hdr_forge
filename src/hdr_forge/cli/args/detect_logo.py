"""Argument parsing for the 'detect-logo' subcommand."""

import argparse


def add_detect_logo_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'detect_logo' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    detect_logo_parser: argparse.ArgumentParser = parser.add_parser(
        'detect-logo',
        description='Detect logos in a video file',
        help='Detect logos'
    )

    detect_logo_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for logo detection'
    )

    detect_logo_parser.add_argument(
        '-e', '--export',
        help='Export detected logo mask to specified file path as PNG image'
    )

    detect_logo_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )
