"""CLI output and progress tracking functionality."""

from hdr_forge.cli.cli_output import ANSI_BLUE, color_str, create_aspect_ratio_str
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionInfo
from hdr_forge.typedefs.mkv_typing import MkvTrack
from hdr_forge.typedefs.video_typing import CropResult, MasterDisplayColorPrimaries, MasterDisplayMetadata, build_master_display_string
from hdr_forge.video import Video

def _print_hdr10_metadata(video: Video) -> None:
    """Print HDR10 metadata information.

    Args:
        video: Video object with metadata
    """
    color = ANSI_BLUE
    master_display: MasterDisplayMetadata | None = video.get_master_display()
    master_display_str = color_str(build_master_display_string(master_display) if master_display else '-', color)

    max_cll_max_fall = video.get_max_cll_max_fall()
    max_cll_fall_str = color_str(f'{max_cll_max_fall[0]}, {max_cll_max_fall[1]}', color) if max_cll_max_fall else color_str('-', color)

    master_display_color_primaries: None | MasterDisplayColorPrimaries = video.get_mastering_display_color_primaries()
    primaries_str = color_str(master_display_color_primaries.value if master_display_color_primaries else '-', color)

    print(f"- HDR Metadata: {primaries_str}")
    print(f"  + Master Display: {master_display_str}")
    print(f"  + MaxCLL/MaxFALL: {max_cll_fall_str}")

def print_video_infos(video: Video) -> None:
    """Print extracted video information.

    Args:
        video: Video object with metadata
    """

    color = ANSI_BLUE
    print()
    print(f"{color_str('_', color)}" * 70)

    print(f"Container: {color_str(str(video.get_container_type()), color)}")
    print(f"- File: {color_str(str(video.get_filepath()), color)}")

    video_tracks: list[MkvTrack] = video.get_container_video_tracks()
    if video_tracks:
        print(f"- Video Tracks:")
        for v_track in video_tracks:
            print(f"  + ID: {color_str(v_track.id, color)} Codec: {color_str(v_track.codec, color)}")

    audio_tracks: list[MkvTrack] = video.get_container_audio_tracks()
    if audio_tracks:
        print(f"- Audio Tracks:")
        for a_track in audio_tracks:
            lang = color_str(a_track.properties.language or '-', color)
            name = color_str(a_track.properties.track_name or '-', color)
            print(f"  + ID: {color_str(a_track.id, color)} Codec: {color_str(a_track.codec, color)} lang: {lang} Name: {name}")

    subs_tracks: list[MkvTrack] = video.get_container_subtitles_tracks()
    if subs_tracks:
        print(f"- Subtitle Tracks:")
        for s_track in subs_tracks:
            lang = color_str(s_track.properties.language or '-', color)
            name = color_str(s_track.properties.track_name or '-', color)
            print(f"  + ID: {color_str(s_track.id, color)} Codec: {color_str(s_track.codec, color)} lang: {lang} Name: {name}")

    resolution: str = f"{video.get_width()}x{video.get_height()}"
    aspect_ratio: str = create_aspect_ratio_str(video.get_width(), video.get_height())
    fps = float("{:.3f}".format(video.get_fps()))
    interlaced = 'Yes' if video.is_video_interlaced() else 'No'

    print("\nVideo Information:")
    print(f"- Geometry:   {color_str(resolution, color)} @ {color_str(aspect_ratio, color)} ~ {color_str(f'{fps}', color)}fps")
    print(f"- Interlaced: {color_str(interlaced, color)}")

    color_prim = color_str(video.get_color_primaries() or "-", color)
    color_trans = color_str(video.get_color_transfer() or "-", color)
    color_space = color_str(video.get_color_space() or "-", color)
    color_range = color_str(video.get_color_range() or '-', color)
    pix_fmt = color_str(video.get_pix_fmt() or '-', color)
    bit_depth = color_str(video.get_bit_depth(), color)

    print(f"- Color:      Primaries={color_prim} | Transfer={color_trans} | Space={color_space} | Range={color_range}")
    print(f"- Encoding:   Format={pix_fmt} | Bit Depth={bit_depth}")
    print()

    hdr_formats_str: str = ', '.join([fmt.value.upper() for fmt in video.get_hdr_sdr_format()])
    print(f"HDR: {color_str(hdr_formats_str, color)}")

    dolby_vision_info: DolbyVisionInfo | None = video.get_dolby_vision_info()
    if dolby_vision_info:
        print(f"- Dolby Vision: Profile {color_str(dolby_vision_info.dv_profile or '-', color)}")
        print(f"  + Layout: {color_str(dolby_vision_info.dv_layout, color)}", end="")
        if dolby_vision_info.dv_profile_el:
            print(f" | EL={color_str(dolby_vision_info.dv_profile_el, color)}", end="")
        print()
        print(f"  + DM Version: {color_str(dolby_vision_info.dm_version or '-', color)} | CM Version: {color_str(dolby_vision_info.cm_version or '-', color)}")

        crop: CropResult | None = video.get_dolby_vision_crop()
        if crop and crop.is_valid:
            crop_str: str = color_str(f"{crop.width}:{crop.height}:{crop.x}:{crop.y}", color)
            print(f"  + RPU Crop: {crop_str}")
        _print_hdr10_metadata(video=video)
    elif video.is_hdr10_video():
        _print_hdr10_metadata(video=video)

    print(f"{color_str('_', color)}" * 70)
    print()
