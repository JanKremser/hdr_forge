"""CLI output and progress tracking functionality."""



from ehdr.cli.cli_output import BLUE, color_str
from ehdr.typing.dolby_vision_typing import DolbyVisionInfo, DolbyVisionSiteDataInfo
from ehdr.video import Video

def print_video_infos(video: Video) -> None:
    """Print extracted video information.

    Args:
        video: Video object with metadata
    """
    resolution: str = f"{video.get_width()}x{video.get_height()}"

    color = BLUE
    print()
    print(f"{color_str('_', color)}" * 70)
    print("Video Information:")
    print(f"  Input File: {color_str(str(video.get_filepath()), color)}")
    print(f"  Resolution: {color_str(resolution, color)}")
    print(f"  Frame Rate: {color_str(video.get_fps(), color)}")
    print(f"  Color Primaries: {color_str(video.get_color_primaries(), color)}")
    print(f"  Color Transfer: {color_str(video.get_color_transfer(), color)}")
    print(f"  Color Space: {color_str(video.get_color_space(), color)}")
    print(f"  HDR/SDR: {color_str(video.get_color_format().value.upper(), color)}")
    if video.is_hdr_video():
        print("  HDR10 Metadata:")
        max_cll_max_fall = video.get_max_cll_max_fall()
        print(f"    MasterDisplay: {color_str(video.get_master_display() or 'N/A', color)}")
        if max_cll_max_fall:
            max_cll, max_fall = max_cll_max_fall
            print(f"    MaxCLL/MaxFALL: {color_str(f'{max_cll}, {max_fall}', color)}")
        else:
            print(f"    MaxCLL/MaxFALL: {color_str('N/A', color)}")

    dolby_vision_info: DolbyVisionInfo | None = video.get_dolby_vision_info()
    if dolby_vision_info:
        print("  Dolby Vision Metadata:")
        print(f"    Profile: {color_str(dolby_vision_info.dv_profile or 'N/A', color)}")
        print(f"    Level: {color_str(dolby_vision_info.dv_level or 'N/A', color)}")
        print(f"    EL: {color_str(dolby_vision_info.dv_profile_el or 'N/A', color)}")
        print(f"    Format: {color_str(dolby_vision_info.dv_format, color)}")
    print(f"{color_str('_', color)}" * 70)
    print()
