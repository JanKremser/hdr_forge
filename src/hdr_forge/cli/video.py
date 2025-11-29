"""CLI output and progress tracking functionality."""



from hdr_forge.cli.cli_output import ANSI_BLUE, color_str, create_aspect_ratio_str
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionInfo
from hdr_forge.typedefs.mkv_typing import MkvTrack
from hdr_forge.typedefs.video_typing import MasterDisplayMetadata, build_master_display_string
from hdr_forge.video import Video

def _print_hdr10_metadata(video: Video) -> None:
    """Print HDR10 metadata information.

    Args:
        video: Video object with metadata
    """
    color = ANSI_BLUE
    master_display: MasterDisplayMetadata | None = video.get_master_display()
    print(f"    HDR10 MasterDisplay: {color_str(build_master_display_string(master_display) if master_display else '-', color)}")

    max_cll_max_fall = video.get_max_cll_max_fall()
    if max_cll_max_fall:
        max_cll, max_fall = max_cll_max_fall
        print(f"    HDR10 MaxCLL/MaxFALL: {color_str(f'{max_cll}, {max_fall}', color)}")
    else:
        print(f"    HDR10 MaxCLL/MaxFALL: {color_str('-', color)}")

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

    resolution: str = f"{video.get_width()}x{video.get_height()}"
    aspect_ratio: str = create_aspect_ratio_str(video.get_width(), video.get_height())
    print("Video Information:")
    print(f"  Input File: {color_str(str(video.get_filepath()), color)}")
    print(f"  Resolution: {color_str(resolution, color)}")
    print(f"  Aspect Ratio: {color_str(aspect_ratio, color)}")
    print(f"  Frame Rate: {color_str(float("{:.3f}".format(video.get_fps())), color)}")
    print(f"  Color Primaries: {color_str(video.get_color_primaries(), color)}")
    print(f"  Color Transfer: {color_str(video.get_color_transfer(), color)}")
    print(f"  Color Space: {color_str(video.get_color_space(), color)}")
    print(f"  Bit depth: {color_str(video.get_bit_depth(), color)}")

    hdr_formats_str: str = ', '.join([fmt.value.upper() for fmt in video.get_hdr_sdr_format()])
    print(f"  HDR/SDR: {color_str(hdr_formats_str, color)}")
    if video.is_hdr10_video():
        _print_hdr10_metadata(video=video)

    dolby_vision_info: DolbyVisionInfo | None = video.get_dolby_vision_info()
    if dolby_vision_info:
        print("  Dolby Vision Metadata:")
        print(f"    Profile: {color_str(dolby_vision_info.dv_profile or '-', color)}")
        print(f"    Layout: {color_str(dolby_vision_info.dv_layout, color)}")
        print(f"    Enhancement Layer (EL): {color_str(dolby_vision_info.dv_profile_el or '-', color)}")
        _print_hdr10_metadata(video=video)

    print(f"{color_str('_', color)}" * 70)
    print()
