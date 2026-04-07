"""Argument parsing for the 'info' subcommand."""

import argparse


def add_info_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'info' subcommand.

    Args:
        parser: Argument parser to add arguments to
    """
    info_parser: argparse.ArgumentParser = parser.add_parser(
        'info',
        description='Shows information about a video file',
        help='Display video information'
    )

    info_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Video file for information display'
    )

    info_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )
