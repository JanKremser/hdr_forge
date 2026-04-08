"""Argument parsing for the 'edit' subcommand."""

import argparse


def add_edit_subcommand(parser: argparse._SubParsersAction) -> None:
    """Add arguments for the 'edit' subcommand."""
    edit_parser: argparse.ArgumentParser = parser.add_parser(
        'edit',
        description='Edit MKV files in-place (no re-encoding)',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Edit MKV file properties in-place',
    )

    edit_parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input MKV file or directory containing MKV files',
    )

    edit_parser.add_argument(
        '-s', '--subtitle-flags',
        default=None,
        help="""
Subtitle flags. Same syntax as the convert subcommand.
If omitted, subtitle properties are left untouched.

  Global modes:
    [copy]                 : Preserve source subtitle flags exactly
    [auto]                 : Intelligently set forced/default tracks by system language
    [auto>ger]             : Auto-select for a specific language

  Per-track overrides (use track IDs from 'hdr_forge info'):
    [ID:default]           : Set a track as default  (e.g. 3:default)
    [ID:forced]            : Set a track as forced  (e.g. 3:forced)
    [ID:none]              : Remove default and forced flags from a track  (e.g. 3:none)
    [LANG:default]         : Set tracks of a language as default  (e.g. ger:default)

  Combine with semicolons:
    [copy;3:default]       : Copy flags, override track 3 as default
    [auto>eng;4:forced]    : Auto-select English as default language, force track 4

Note: In-place editing does not support :remove (track removal requires remux).
Track IDs are mkvmerge absolute track IDs, shown by 'hdr_forge info'.
"""
    )

    edit_parser.add_argument(
        '-d', '--debug',
        action='store_true',
    )
