"""In-place subtitle track property editing."""

from hdr_forge.tools import mkvpropedit
from hdr_forge.typedefs.encoder_typing import SubtitleMode, SubtitleModeItem, SubtitleTrackAction, SubtitleTrackOverride
from hdr_forge.typedefs.mkv_typing import MkvTrack


def build_subtitle_track_edits(
    source_subtitle_tracks: list[MkvTrack],
    output_subtitle_tracks: list[MkvTrack],
    subtitle_flags: SubtitleModeItem,
    overrides: dict[str, SubtitleTrackOverride],
) -> list[mkvpropedit.SubtitleTrackEdit]:
    """Build a list of subtitle track edits from subtitle flags and overrides.

    This function extracts the core edit-building logic that was previously embedded
    in Encoder._apply_subtitle_properties, making it reusable by standalone edit commands.

    Args:
        source_subtitle_tracks: List of source tracks (from Video object)
        output_subtitle_tracks: List of output/target tracks (from mkvmerge info)
        subtitle_flags: Global subtitle mode (COPY/AUTO) and language preference
        overrides: Per-track overrides (ID or language → action)

    Returns:
        List of SubtitleTrackEdit objects to pass to mkvpropedit.set_subtitle_track_properties.
        Returns empty list if subtitle_flags.mode == REMOVE (caller should treat as no-op).
    """
    # REMOVE mode produces no edits
    if subtitle_flags.mode == SubtitleMode.REMOVE:
        return []

    # Build set of source track IDs marked for removal (by ID or language)
    removed_source_ids: set[int] = set()
    for source_track in source_subtitle_tracks:
        track_id_str = str(source_track.id)
        override = (
            overrides.get(track_id_str)
            or overrides.get(source_track.properties.language or '')
        )
        if override and override.action == SubtitleTrackAction.REMOVE:
            removed_source_ids.add(source_track.id)

    # Build list of source tracks that are kept (not removed)
    kept_source_tracks = [t for t in source_subtitle_tracks if t.id not in removed_source_ids]

    edits: list[mkvpropedit.SubtitleTrackEdit] = []

    if subtitle_flags.mode == SubtitleMode.COPY:
        # COPY: Preserve source properties exactly
        for i, output_track in enumerate(output_subtitle_tracks):
            if i >= len(kept_source_tracks):
                continue

            source_track = kept_source_tracks[i]
            track_selector = f"track:@{output_track.id + 1}"

            # Start with source properties
            flag_default = source_track.properties.default_track or False
            flag_forced = source_track.properties.forced_track or False
            track_name = source_track.properties.track_name

            # Apply per-track overrides
            track_id_str = str(source_track.id)
            override = (
                overrides.get(track_id_str)
                or overrides.get(source_track.properties.language or '')
            )
            if override:
                if override.action == SubtitleTrackAction.DEFAULT:
                    flag_default = True
                elif override.action == SubtitleTrackAction.FORCED:
                    flag_forced = True
                elif override.action == SubtitleTrackAction.NONE:
                    flag_default = False
                    flag_forced = False

            edits.append(
                mkvpropedit.SubtitleTrackEdit(
                    track_selector=track_selector,
                    name=track_name,
                    flag_default=flag_default,
                    flag_forced=flag_forced,
                )
            )

    elif subtitle_flags.mode == SubtitleMode.AUTO:
        # AUTO: Intelligent selection with language matching
        default_lang: str | None = subtitle_flags.default_lang
        has_default_track = False

        for i, output_track in enumerate(output_subtitle_tracks):
            if i >= len(kept_source_tracks):
                continue

            source_track = kept_source_tracks[i]
            track_selector = f"track:@{output_track.id + 1}"

            # Determine title and flags from AUTO logic
            title: str = ""
            is_default = False
            is_forced = False

            # Check if this is a forced track
            if (
                source_track.properties.forced_track
                or (
                    source_track.properties.track_name
                    and "forced" in source_track.properties.track_name.lower()
                )
            ):
                title = "forced"
                is_forced = True
                # Only set as default if language matches and no other default yet
                if default_lang and source_track.properties.language == default_lang and not has_default_track:
                    is_default = True
                    has_default_track = True

            # Determine title if not forced
            track_name = source_track.properties.track_name or ""
            if title == "":
                if "commentary" in track_name.lower():
                    title = "commentary"
                else:
                    title = "full"

            # Append SDH if in track name
            if "sdh" in track_name.lower():
                title += " SDH"

            # Append codec info
            if source_track.codec:
                codec_parts = source_track.codec.upper().split('/')
                if len(codec_parts) > 1:
                    codec_name = codec_parts[1]
                else:
                    codec_parts2 = source_track.codec.upper().split(' ')
                    codec_name = codec_parts2[1] if len(codec_parts2) > 1 else source_track.codec.upper()
                title += f" ({codec_name})"

            # Apply per-track overrides (override AUTO logic)
            track_id_str = str(source_track.id)
            override = (
                overrides.get(track_id_str)
                or overrides.get(source_track.properties.language or '')
            )
            if override:
                if override.action == SubtitleTrackAction.DEFAULT:
                    is_default = True
                    has_default_track = True
                elif override.action == SubtitleTrackAction.FORCED:
                    is_forced = True
                elif override.action == SubtitleTrackAction.NONE:
                    is_default = False
                    is_forced = False

            edits.append(
                mkvpropedit.SubtitleTrackEdit(
                    track_selector=track_selector,
                    name=title,
                    flag_default=is_default,
                    flag_forced=is_forced,
                )
            )

    return edits
