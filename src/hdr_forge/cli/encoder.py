"""CLI output and progress tracking functionality."""

from hdr_forge.typedefs.video_typing import CropResult
from hdr_forge.cli.args.pars_encoder_settings import print_parameter_warnings
from hdr_forge.cli.cli_output import ANSI_BLUE, color_str, create_aspect_ratio_str
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfile
from hdr_forge.typedefs.encoder_typing import AudioCodec, AudioCodecItem, EncoderSettings, VideoCodec
from hdr_forge.encoder import Encoder


def _print_hdr10_metadata(video_codec_lib: VideoCodecBase) -> None:
    """Print HDR10 metadata information.

    Args:
        video: VideoCodecBase object with metadata
    """
    color = ANSI_BLUE
    v_param: dict = video_codec_lib.get_custom_lib_parameters()
    masterdisplay: str | None = v_param.get("master-display", None)
    master_display_str = color_str(masterdisplay or '-', color)
    maxcll: str | None = v_param.get("max-cll", None)
    maxcll_str = color_str(maxcll or '-', color)
    print(f"- HDR Metadata:")
    print(f"  + Master Display: {master_display_str}")
    print(f"  + MaxCLL/MaxFALL: {maxcll_str}")

def print_encoding_params(encoder: Encoder) -> None:
    """Print encoding parameters.

    Args:
        encoder: Encoder object with encoding configuration
    """

    color = ANSI_BLUE
    print()
    print(f"{color_str('_', color)}" * 70)
    print("Encoding Parameters:")
    print(f"- Output: {color_str(str(encoder.get_target_file()), color)}")

    video_codec: VideoCodec = encoder.get_encoding_video_codec()
    print(f"- Video Codec: {color_str(video_codec.value, color=color)}")

    audio_codec_items: dict[str, AudioCodecItem] = encoder.get_audio_codec_items()
    if audio_codec_items:
        print(f"- Audio Tracks:")
        for track in audio_codec_items:
            from_codec: str | AudioCodec | None = audio_codec_items[track].from_codec
            from_codec_str = "all"
            if from_codec:
                from_codec_str = from_codec.value if isinstance(from_codec, AudioCodec) else from_codec
            print(f"  + ID: {color_str(track, color)} {color_str(from_codec_str, color)} -> {color_str(audio_codec_items[track].to_codec.value, color)}")

    video_codec_lib: VideoCodecBase | None = encoder.get_video_codec_lib()
    if video_codec_lib:
        encoder_settings: EncoderSettings = encoder.get_encoder_settings()
        print_parameter_warnings(encoder_settings=encoder_settings, active_encoder_lib=video_codec_lib.lib)

        v_param: dict = video_codec_lib.get_custom_lib_parameters()
        crf: int | None = v_param.get("crf", None) or None
        cq: int | None = v_param.get("cq", None) or None

        if crf is not None:
            tune = v_param.get('tune')
            tune_str = f" | tune={color_str(tune, color)}" if tune else ""
            print(f"- Video Encoder: {color_str(video_codec_lib.lib.value, color)} | crf={color_str(crf, color)} | preset={color_str(v_param.get('preset') or '-', color)}{tune_str}")
        elif cq is not None:
            print(f"- Video Encoder: {color_str(video_codec_lib.lib.value, color)} | cq={color_str(cq, color)} | preset={color_str(v_param.get('preset') or '-', color)} | rc={color_str(v_param.get('rc') or '-', color)}")
        else:
            print(f"- Video Encoder: {color_str(video_codec_lib.lib.value, color)}")

        crop: CropResult = video_codec_lib.get_crop()
        crop_str = color_str(f"{crop.width}:{crop.height}:{crop.x}:{crop.y}", color) if crop.is_valid else color_str('-', color)
        resolution_w, resolution_h = video_codec_lib.get_encoding_resolution()
        aspect_ratio: str = create_aspect_ratio_str(resolution_w, resolution_h)
        pix_fmt = color_str(video_codec_lib.get_pix_format_for_encoding() or '-', color)
        bit_depth = color_str(video_codec_lib.get_bit_depth_for_encoding(), color)

        print(f"- Geometry:  {color_str(f'{resolution_w}x{resolution_h}', color)} @ {color_str(aspect_ratio, color)} | Crop: {crop_str}")
        print(f"- Encoding:  Format={pix_fmt} | Bit Depth={bit_depth}")

    hdr_formats_str: str = ', '.join([fmt.value.upper() for fmt in encoder.get_encoding_hdr_sdr_format()])
    print()
    print(f"HDR: {color_str(hdr_formats_str, color)}")

    if encoder.is_dolby_vision_encoding():
        dv_profile: DolbyVisionProfile | None = encoder.get_encoding_dolby_vision_profile()
        assert dv_profile is not None
        dv_el: bool | None = encoder.get_encoding_dolby_vision_el_present()
        dv_layout: str = f"BL+{'EL+' if dv_el else ''}RPU"
        print(f"- Dolby Vision: Profile {color_str(dv_profile.value, color)}")
        print(f"  + Layout: {color_str(dv_layout, color)}")

    if encoder.is_hdr10_encoding() and video_codec_lib:
        _print_hdr10_metadata(video_codec_lib=video_codec_lib)

    print(f"{color_str('_', color)}" * 70)
    print()
