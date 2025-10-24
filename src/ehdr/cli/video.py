"""CLI output and progress tracking functionality."""



from ehdr.cli.cli_output import BLUE, color_str, create_aspect_ratio_str
from ehdr.typedefs.dolby_vision_typing import DolbyVisionInfo
from ehdr.typedefs.mkv_typing import MkvTrack
from ehdr.typedefs.video_typing import MasterDisplayMetadata, build_master_display_string
from ehdr.video import Video

def print_video_infos(video: Video) -> None:
    """Print extracted video information.

    Args:
        video: Video object with metadata
    """

    color = BLUE
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
    print(f"  Frame Rate: {color_str(video.get_fps(), color)}")
    print(f"  Color Primaries: {color_str(video.get_color_primaries(), color)}")
    print(f"  Color Transfer: {color_str(video.get_color_transfer(), color)}")
    print(f"  Color Space: {color_str(video.get_color_space(), color)}")
    print(f"  HDR/SDR: {color_str(video.get_hdr_sdr_format().value.upper(), color)}")
    if video.is_hdr_video():
        print("  HDR10 Metadata:")
        master_display: MasterDisplayMetadata | None = video.get_master_display()
        print(f"    MasterDisplay: {color_str(build_master_display_string(master_display) if master_display else '-', color)}")

        max_cll_max_fall = video.get_max_cll_max_fall()
        if max_cll_max_fall:
            max_cll, max_fall = max_cll_max_fall
            print(f"    MaxCLL/MaxFALL: {color_str(f'{max_cll}, {max_fall}', color)}")
        else:
            print(f"    MaxCLL/MaxFALL: {color_str('-', color)}")

    dolby_vision_info: DolbyVisionInfo | None = video.get_dolby_vision_info()
    if dolby_vision_info:
        print("  Dolby Vision Metadata:")
        print(f"    Profile: {color_str(dolby_vision_info.dv_profile or '-', color)}")
        print(f"    Layout: {color_str(dolby_vision_info.dv_layout, color)}")
        print(f"    Enhancement Layer (EL): {color_str(dolby_vision_info.dv_profile_el or '-', color)}")

    print(f"{color_str('_', color)}" * 70)
    print()
