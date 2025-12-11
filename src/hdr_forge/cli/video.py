"""CLI output and progress tracking functionality."""



from hdr_forge.cli.cli_output import ANSI_BLUE, color_str, create_aspect_ratio_str
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionInfo
from hdr_forge.typedefs.mkv_typing import MkvTrack
from hdr_forge.typedefs.video_typing import MasterDisplayColorPrimaries, MasterDisplayMetadata, build_master_display_string
from hdr_forge.video import Video

def _print_hdr10_metadata(video: Video) -> None:
    """Print HDR10 metadata information.

    Args:
        video: Video object with metadata
    """
    color = ANSI_BLUE
    master_display: MasterDisplayMetadata | None = video.get_master_display()
    print(f"    MasterDisplay: {color_str(build_master_display_string(master_display) if master_display else '-', color)}")

    max_cll_max_fall = video.get_max_cll_max_fall()
    if max_cll_max_fall:
        max_cll, max_fall = max_cll_max_fall
        print(f"    MaxCLL/MaxFALL: {color_str(f'{max_cll}, {max_fall}', color)}")
    else:
        print(f"    MaxCLL/MaxFALL: {color_str('-', color)}")

    master_display_color_primaries: None | MasterDisplayColorPrimaries = video.get_mastering_display_color_primaries()
    print(f"    Mastering Color Primaries: {color_str(master_display_color_primaries.value if master_display_color_primaries else '-', color)}")

def print_video_infos(video: Video) -> None:
    """Print extracted video information.

    Args:
        video: Video object with metadata
    """

    color = ANSI_BLUE
    print()
    print(f"{color_str('_', color)}" * 70)

    print("Container Information:")
    print(f"  Container Type: {color_str(str(video.get_container_type()), color)}")
    video_tracks: list[MkvTrack] = video.get_container_video_tracks()
    for v_track in video_tracks:
        print(f"  Video Tracks:")
        print(f"    ID: {color_str(str(v_track.id), color)}")
        print(f"    Codec: {color_str(v_track.codec, color)}")
        print(f"    Language: {color_str(v_track.properties.language or '-', color)}")
    audio_tracks: list[MkvTrack] = video.get_container_audio_tracks()
    for a_track in audio_tracks:
        print(f"  Audio Tracks:")
        print(f"    ID: {color_str(str(a_track.id), color)}")
        print(f"    Codec: {color_str(a_track.codec, color)}")
        print(f"    Language: {color_str(a_track.properties.language or '-', color)}")
    subs_tracks: list[MkvTrack] = video.get_container_subtitles_tracks()
    for s_track in subs_tracks:
        print(f"  Subtitles Tracks:")
        print(f"    ID: {color_str(str(s_track.id), color)}")
        print(f"    Codec: {color_str(s_track.codec, color)}")
        print(f"    Language: {color_str(s_track.properties.language or '-', color)}")

    resolution: str = f"{video.get_width()}x{video.get_height()}"
    aspect_ratio: str = create_aspect_ratio_str(video.get_width(), video.get_height())
    print("Video Information:")
    print(f"  Input File: {color_str(str(video.get_filepath()), color)}")
    print(f"  Resolution: {color_str(resolution, color)}")
    print(f"  Aspect Ratio: {color_str(aspect_ratio, color)}")
    print(f"  Frame Rate: {color_str(float("{:.3f}".format(video.get_fps())), color)}")
    print(f"  Interlaced: {color_str('Yes' if video.is_video_interlaced() else 'No', color)}")
    print(f"  Color Primaries: {color_str(video.get_color_primaries() or "-", color)}")
    print(f"  Color Transfer: {color_str(video.get_color_transfer() or "-", color)}")
    print(f"  Color Space: {color_str(video.get_color_space() or "-", color)}")
    print(f"  Color Range: {color_str(video.get_color_range() or '-', color)}")
    print(f"  Pixel Format: {color_str(video.get_pix_fmt() or '-', color)}")
    print(f"  Bit depth: {color_str(video.get_bit_depth(), color)}")

    hdr_formats_str: str = ', '.join([fmt.value.upper() for fmt in video.get_hdr_sdr_format()])

    dolby_vision_info: DolbyVisionInfo | None = video.get_dolby_vision_info()
    if dolby_vision_info:
        print("  HDR10/Dolby Vision Metadata:")
        print(f"    Profile: {color_str(dolby_vision_info.dv_profile or '-', color)}")
        print(f"    Layout: {color_str(dolby_vision_info.dv_layout, color)}")
        if dolby_vision_info.dv_profile_el:
            print(f"    Enhancement Layer (EL): {color_str(dolby_vision_info.dv_profile_el or '-', color)}")
        _print_hdr10_metadata(video=video)
    elif video.is_hdr10_video():
        print(f"  HDR/SDR: {color_str(hdr_formats_str, color)}")
        _print_hdr10_metadata(video=video)

    print(f"{color_str('_', color)}" * 70)
    print()
