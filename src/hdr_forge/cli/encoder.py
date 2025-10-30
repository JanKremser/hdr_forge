"""CLI output and progress tracking functionality."""

from hdr_forge.analyze.crop_video import CropResult
from hdr_forge.cli.args.pars_encoder_settings import print_parameter_warnings
from hdr_forge.cli.cli_output import ANSI_BLUE, color_str, create_aspect_ratio_str
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionEnhancementLayer, DolbyVisionProfile
from hdr_forge.typedefs.encoder_typing import EncoderSettings, VideoCodec
from hdr_forge.encoder import Encoder


def print_encoding_params(encoder: Encoder) -> None:
    """Print encoding parameters.

    Args:
        encoder: Encoder object with encoding configuration
    """

    color = ANSI_BLUE
    print()
    print(f"{color_str('_', color)}" * 70)
    print("Encoding Parameters:")
    print(f"  Output File: {color_str(str(encoder.get_target_file()), color)}")

    video_codec: VideoCodec = encoder.get_encoding_video_codec()
    print(f"  Video Codec: {color_str(video_codec.value, color)}")
    video_codec_lib: VideoCodecBase | None = encoder.get_video_codec_lib()
    if video_codec_lib:
         # Print warnings for incompatible parameters
        encoder_settings: EncoderSettings = encoder.get_encoder_settings()
        print_parameter_warnings(encoder_settings=encoder_settings, active_encoder_lib=video_codec_lib.lib)

        v_param: dict = video_codec_lib.get_custom_lib_parameters()
        print(f"  Video Encoder Library: {color_str(video_codec_lib.lib.value, color)}")
        crf: int | None = v_param.get("crf", None) or None
        if crf is not None:
            print(f"    CRF: {color_str(crf, color)}")
        cq: int | None = v_param.get("cq", None) or None
        if cq is not None:
            print(f"    CQ: {color_str(cq, color)}")
        print(f"    Preset: {color_str(v_param.get('preset') or '-', color)}")
        print(f"    Tune: {color_str(v_param.get('tune') or '-', color)}")

        crop: CropResult = video_codec_lib.get_crop()
        if crop.is_valid:
            print(f"  Crop: {color_str(f"{crop.width}:{crop.height}:{crop.x}:{crop.y}", color)}")
        else:
            print(f"  Crop: {color_str('-', color)}")

        resolution_w, resolution_h = video_codec_lib.get_encoding_resolution()
        aspect_ratio: str = create_aspect_ratio_str(resolution_w, resolution_h)
        print(f"  Resolution: {color_str(f"{resolution_w}x{resolution_h}", color)}")
        print(f"  Aspect Ratio: {color_str(aspect_ratio, color)}")
        print(f"  HDR/SDR: {color_str(encoder.get_encoding_hdr_sdr_format().value.upper(), color)}")
        if video_codec_lib.is_hdr_encoding():
            masterdisplay: str | None = v_param.get("master-display", None)
            print(f"    MasterDisplay: {color_str(masterdisplay or '-', color)}")
            maxcll: str | None = v_param.get("max-cll", None)
            print(f"    MaxCLL/MaxFALL: {color_str(maxcll or '-', color)}")
    if encoder.is_dolby_vision_encoding():
        dv_profile: DolbyVisionProfile | None = encoder.get_encoding_dolby_vision_profile()
        assert dv_profile is not None
        print(f"  Dolby Vision:")
        print(f"    Profile: {color_str(dv_profile.value, color)}")

        dv_el: DolbyVisionEnhancementLayer | None = encoder.get_encoding_dolby_vision_enhancement_layer()

        dv_layout: str = f"BL+{'EL+' if dv_el else ''}RPU"
        print(f"    Layout: {color_str(dv_layout, color)}")

        dv_el_str: str | None = dv_el.value if dv_el else None
        print(f"    Enhancement Layer (EL): {color_str(dv_el_str or '-', color)}")
    print(f"{color_str('_', color)}" * 70)
    print()
