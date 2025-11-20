"""Parse encoder settings from command-line arguments."""

import sys
from typing import Tuple

from ffmpeg.types import T

from hdr_forge import __version__
from hdr_forge.cli.cli_output import print_err, print_warn
from hdr_forge.typedefs.encoder_typing import CropMode, CropSettings, EncoderOverride, GrainMode, HEVC_NVENC_Preset, HdrForgeEncodingHardwarePresets, HdrForgeEncodingPresetSettings, HdrForgeEncodingPresets, HdrSdrFormat, EncoderSettings, LogoRemovalMode, NvencParams, NvencRcMode, SampleSettings, ScaleMode, UniversalEncoderParams, VideoCodec, VideoEncoderLibrary, Libx264Params, X264Tune, Libx265Params, X265Tune, x265_x264_Preset
from hdr_forge.typedefs.dolby_vision_typing import DolbyVisionProfileEncodingMode
from hdr_forge.typedefs.video_typing import ContentLightLevelMetadata, HdrMetadata, MasterDisplayMetadata

# Resolution constants
RESOLUTIONS: dict = {
    'FUHD': 4320,
    'UHD': 2160,
    'QHD+': 1800,
    'WQHD': 1440,
    'FHD': 1080,
    'HD': 720,
    'QHD': 540,
    'SD': 480
}

def _get_scale_height(scale: str | None) -> int | None:
    """Get target height from scale argument.
    Args:
        scale: Scale argument string
    Returns:
        Target height in pixels or None
    """

    target_height = None
    if scale:
        if scale.upper() in RESOLUTIONS:
            target_height = RESOLUTIONS[scale.upper()]
        else:
            try:
                # Try to parse as integer height
                target_height = int(scale)
            except ValueError:
                print(f"Warning: Invalid scale value '{scale}', using original size")

    return target_height


def _get_hdr_sdr_format_from_string(format_str: str | None) -> HdrSdrFormat:
    """Convert string to ColorFormat enum.

    Args:
        format_str: Color format string

    Returns:
        Corresponding ColorFormat enum value
    """
    if format_str is None:
        return HdrSdrFormat.AUTO

    format_str = format_str.lower()
    if format_str == 'sdr':
        return HdrSdrFormat.SDR
    elif format_str == 'hdr':
        return HdrSdrFormat.HDR
    elif format_str == 'hdr10':
        return HdrSdrFormat.HDR10
    elif format_str == 'dolby_vision':
        return HdrSdrFormat.DOLBY_VISION
    else:
        return HdrSdrFormat.AUTO

def _get_dolby_vision_profile_from_string(profile_str: str | None) -> DolbyVisionProfileEncodingMode:
    """Convert string to DolbyVision enum.

    Args:
        profile_str: Dolby Vision profile string

    Returns:
        Corresponding DolbyVision enum value
    """
    if profile_str is None:
        return DolbyVisionProfileEncodingMode.AUTO

    profile_str = profile_str.lower()
    if profile_str == '8':
        return DolbyVisionProfileEncodingMode._8

    return DolbyVisionProfileEncodingMode.AUTO


def _get_video_codec_from_string(codec_str: str | None) -> VideoCodec:
    """Convert string to VideoEncoder enum.

    Args:
        codec_str: Video codec string

    Returns:
        Corresponding VideoEncoder enum value
    """
    if codec_str is None:
        return VideoCodec.H265

    codec_str = codec_str.lower()
    if codec_str == 'copy':
        return VideoCodec.COPY
    elif codec_str == 'h264':
        return VideoCodec.H264

    return VideoCodec.H265


def _get_crop_settings_from_string(crop_str: str | None) -> CropSettings:
    """Convert crop argument string to CropSettings object.

    Args:
        crop_str: Crop argument string

    Returns:
        CropSettings object
    """
    if crop_str is None or crop_str.lower() == 'off':
        return CropSettings(mode=CropMode.OFF)

    # Preset for aspect ratios
    if crop_str.lower() == 'cinema':
        crop_str = '2.35:1'
    elif crop_str.lower() == 'cinema-modern':
        crop_str = '2.39:1'
    elif crop_str.lower() == 'european':
        crop_str = '1.66:1'
    elif crop_str.lower() == 'us-widescreen':
        crop_str = '1.85:1'

    if crop_str.lower() == 'auto':
        return CropSettings(mode=CropMode.AUTO)
    elif ':' in crop_str:
        parts = crop_str.split(':')
        if len(parts) == 4:
            try:
                w, h, x, y = map(int, parts)
                return CropSettings(mode=CropMode.MANUAL, manual_crop=(x, y, w, h))
            except ValueError:
                pass
        elif len(parts) == 2:
            try:
                ar_w, ar_h = map(float, parts)
                return CropSettings(mode=CropMode.RATIO, ratio=(ar_w, ar_h))
            except ValueError:
                pass
    print_err(f"Invalid crop value '{crop_str}', using automatic cropping")
    sys.exit(1)

def _get_dar_ratio_settings_from_string(ratio_str: str | None) -> Tuple[int, int] | None:
    """Convert crop argument string to CropSettings object.

    Args:
        crop_str: Crop argument string

    Returns:
        CropSettings object
    """
    if ratio_str is None or ratio_str.lower() == 'off':
        return None

    # Preset for aspect ratios
    if ratio_str.lower() == 'cinema':
        ratio_str = '2.35:1'
    elif ratio_str.lower() == 'cinema-modern':
        ratio_str = '2.39:1'
    elif ratio_str.lower() == 'european':
        ratio_str = '1.66:1'
    elif ratio_str.lower() == 'us-widescreen':
        ratio_str = '1.85:1'

    parts = ratio_str.split(':')
    if len(parts) == 2:
        try:
            ar_w, ar_h = map(float, parts)
            return (int(ar_w*100), int(ar_h*100))
        except ValueError:
            pass
    print_err(f"Invalid dar ratio value '{ratio_str}'")
    sys.exit(1)

def _get_grain_settings_from_string(grain_str: str | None) -> GrainMode:
    """Convert grain argument string to GrainMode enum.

    Args:
        grain_str: Grain argument string

    Returns:
        GrainMode enum value
    """
    if grain_str is None:
        return GrainMode.OFF

    grain_str = grain_str.lower()
    if grain_str == 'off':
        return GrainMode.OFF
    elif grain_str == 'auto':
        return GrainMode.AUTO
    elif grain_str == 'cat1':
        return GrainMode.CAT1
    elif grain_str == 'cat2':
        return GrainMode.CAT2
    elif grain_str == 'cat3':
        return GrainMode.CAT3

    print_err(f"Invalid grain value '{grain_str}', using 'off'")
    sys.exit(1)

def _get_logo_removal_mode_from_string(logo_str: str | None) -> LogoRemovalMode:
    """Convert logo removal argument string to LogoRemovalMode enum.

    Args:
        logo_str: Logo removal argument string

    Returns:
        LogoRemovalMode enum value
    """
    if logo_str is None:
        return LogoRemovalMode.OFF

    logo_str = logo_str.lower()
    if logo_str == 'off':
        return LogoRemovalMode.OFF
    elif logo_str == 'auto':
        return LogoRemovalMode.AUTO

    print_err(f"Invalid logo removal value '{logo_str}', using 'off'")
    sys.exit(1)


def _get_sample_settings_from_string(sample_str: str | None) -> SampleSettings:
    """Convert sample argument string to SampleSettings object.

    Args:
        sample_str: Sample argument string

    Returns:
        SampleSettings object
    """
    if sample_str is None:
        return SampleSettings(enabled=False)

    if sample_str.lower() == 'auto':
        return SampleSettings(enabled=True, start_time=None, end_time=None)

    if ':' in sample_str:
        parts = sample_str.split(':')
        if len(parts) == 2:
            try:
                start = float(parts[0])
                end = float(parts[1])
                return SampleSettings(enabled=True, start_time=start, end_time=end)
            except ValueError:
                pass
    print(f"Warning: Invalid sample value '{sample_str}', not using sampling")
    return SampleSettings(enabled=False)


def _get_master_display_from_string(md_str: str | None) -> MasterDisplayMetadata | None:
    """Convert master display argument string.

    Args:
        md_str: Master display argument string

    Returns:
        Master display MasterDisplayMetadata
    """
    if md_str is None:
        return None

    try:
        parts = md_str.split('L(')
        lum_part = parts[1].rstrip(')')
        max_lum, min_lum = map(float, lum_part.split(','))

        md_values = parts[0]
        r_x = float(md_values.split('R(')[1].split(',')[0]) / 50000
        r_y = float(md_values.split('R(')[1].split(')')[0].split(',')[1]) / 50000
        g_x = float(md_values.split('G(')[1].split(',')[0]) / 50000
        g_y = float(md_values.split('G(')[1].split(')')[0].split(',')[1]) / 50000
        b_x = float(md_values.split('B(')[1].split(',')[0]) / 50000
        b_y = float(md_values.split('B(')[1].split(')')[0].split(',')[1]) / 50000
        wp_x = float(md_values.split('WP(')[1].split(',')[0]) / 10000
        wp_y = float(md_values.split('WP(')[1].split(')')[0].split(',')[1]) / 10000

        return MasterDisplayMetadata(
            r_x=r_x, r_y=r_y,
            g_x=g_x, g_y=g_y,
            b_x=b_x, b_y=b_y,
            wp_x=wp_x, wp_y=wp_y,
            min_lum=min_lum,
            max_lum=max_lum
        )
    except (IndexError, ValueError):
        print_err(f"Invalid master display value '{md_str}'")
        sys.exit(1)


def _get_content_lightLevel_metadata_from_string(cll_str: str | None) -> ContentLightLevelMetadata | None:
    """Convert content light level argument string.

    Args:
        cll_str: Content light level argument string

    Returns:
        ContentLightLevelMetadata object
    """
    if cll_str is None:
        return None

    try:
        maxcll_str, maxfall_str = cll_str.split(',')
        maxcll = int(maxcll_str)
        maxfall = int(maxfall_str)
        return ContentLightLevelMetadata(maxcll=maxcll, maxfall=maxfall)
    except (ValueError, IndexError):
        print_err(f"Invalid content light level value '{cll_str}'")
        sys.exit(1)

def _get_libx265_params_from_string(params_str: str | None) -> Libx265Params:
    """Convert libx265 parameters argument string to libx265Params object.

    Args:
        params_str: libx265 parameters argument string

    Returns:
        Libx265Params object
    """
    params = Libx265Params()
    if params_str is None:
        return params

    parts: list[str] = params_str.split(':')
    try:
        for part in parts:
            if part.startswith('crf='):
                params.crf = int(part.split('=')[1])
                if not (0 <= params.crf <= 51):
                    raise ValueError("CRF out of range")
            elif part.startswith('preset='):
                params.preset = x265_x264_Preset(part.split('=')[1])
            elif part.startswith('tune='):
                params.tune = X265Tune(part.split('=')[1])
    except ValueError as err:
        print_err(msg=f"Invalid libx265 parameters value '{params_str}'. Err: {err}")
        sys.exit(1)

    return params

def _get_libx264_params_from_string(params_str: str | None) -> Libx264Params:
    """Convert libx264 parameters argument string to libx264Params object.

    Args:
        params_str: libx264 parameters argument string

    Returns:
        libx264Params object
    """
    params = Libx264Params()
    if params_str is None:
        return params

    parts: list[str] = params_str.split(':')
    try:
        for part in parts:
            if part.startswith('crf='):
                params.crf = int(part.split('=')[1])
                if not (0 <= params.crf <= 51):
                    raise ValueError("CRF out of range")
            elif part.startswith('preset='):
                params.preset = x265_x264_Preset(part.split('=')[1])
            elif part.startswith('tune='):
                params.tune = X264Tune(part.split('=')[1])
    except ValueError as err:
        print_err(msg=f"Invalid libx264 parameters value '{params_str}'. Err: {err}")
        sys.exit(1)

    return params

def _get_encoder_override_from_string(encoder_str: str | None) -> EncoderOverride:
    """Convert string to EncoderOverride enum.

    Args:
        encoder_str: Encoder override string

    Returns:
        Corresponding EncoderOverride enum value
    """
    if encoder_str is None or encoder_str == 'auto':
        return EncoderOverride.AUTO

    encoder_str = encoder_str.lower()
    if encoder_str == 'libx265':
        return EncoderOverride.LIBX265
    elif encoder_str == 'libx264':
        return EncoderOverride.LIBX264
    elif encoder_str == 'libsvtav1':
        return EncoderOverride.LIBSVTAV1
    elif encoder_str == 'hevc_nvenc':
        return EncoderOverride.HEVC_NVENC
    elif encoder_str == 'h264_nvenc':
        return EncoderOverride.H264_NVENC

    return EncoderOverride.AUTO


def _get_nvenc_params_from_string(params_str: str | None) -> NvencParams:
    """Convert NVENC parameters argument string to NvencParams object.

    Args:
        params_str: NVENC parameters argument string

    Returns:
        NvencParams object
    """
    params = NvencParams()
    if params_str is None:
        return params

    parts: list[str] = params_str.split(':')
    try:
        for part in parts:
            if part.startswith('cq='):
                params.cq = int(part.split('=')[1])
                if not (0 <= params.cq <= 51):
                    raise ValueError("CQ out of range")
            elif part.startswith('preset='):
                params.preset = HEVC_NVENC_Preset(part.split('=')[1])
            elif part.startswith('rc='):
                params.rc = NvencRcMode(part.split('=')[1])
    except ValueError as err:
        print_err(msg=f"Invalid NVENC parameters value '{params_str}'. Err: {err}")
        sys.exit(1)

    return params


def _parse_encoder_params(params_str: str | None, encoder_override: EncoderOverride) -> tuple[Libx265Params | None, Libx264Params | None, NvencParams | None]:
    """Parse --encoder-params based on the selected encoder.

    Args:
        params_str: Encoder parameters string
        encoder_override: Selected encoder override

    Returns:
        Tuple of (libx265_params, libx264_params, nvenc_params), where only one is non-None
    """
    if params_str is None:
        return (None, None, None)

    if encoder_override == EncoderOverride.AUTO:
        print_err("Error: --encoder-params requires --encoder to be set (not 'auto')")
        sys.exit(1)

    if encoder_override in [EncoderOverride.LIBX265]:
        return (_get_libx265_params_from_string(params_str), None, None)
    elif encoder_override in [EncoderOverride.LIBX264]:
        return (None, _get_libx264_params_from_string(params_str), None)
    elif encoder_override in [EncoderOverride.HEVC_NVENC, EncoderOverride.H264_NVENC]:
        return (None, None, _get_nvenc_params_from_string(params_str))

    return (None, None, None)


def _get_universal_params_from_args(args) -> UniversalEncoderParams:
    """Create UniversalEncoderParams object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()

    Returns:
        UniversalEncoderParams object with quality and speed
    """
    quality = getattr(args, 'quality', None)
    speed_str = getattr(args, 'speed', None)

    speed = None
    if speed_str is not None:
        try:
            speed = x265_x264_Preset(speed_str)
        except ValueError:
            print_err(msg=f"Invalid speed value '{speed_str}'")
            sys.exit(1)

    # Validate quality range
    if quality is not None:
        if not (0 <= quality <= 51):
            print_err(msg=f"Invalid quality value '{quality}'. Must be between 0 and 51.")
            sys.exit(1)

    return UniversalEncoderParams(
        quality=quality,
        speed=speed
    )


def _validate_hw_preset_with_encoder(hw_preset_str: str, encoder_override: EncoderOverride) -> str:
    """Validate hw-preset compatibility with encoder and add prefix if needed.

    Args:
        hw_preset_str: Hardware preset string from arguments
        encoder_override: Encoder override selection

    Returns:
        Validated hardware preset string with prefix (cpu: or gpu:)

    Raises:
        SystemExit: If explicit prefix doesn't match encoder type
    """
    # Determine if encoder is GPU-based
    is_gpu_encoder = False
    if encoder_override != EncoderOverride.AUTO:
        # Explicit encoder specified
        is_gpu_encoder = encoder_override in [EncoderOverride.HEVC_NVENC, EncoderOverride.H264_NVENC]
    # If AUTO, default is CPU (libx265/libx264)

    # Check if preset already has a prefix
    if hw_preset_str.startswith('cpu:') or hw_preset_str.startswith('gpu:'):
        # Validate explicit prefix against encoder
        preset_is_gpu = hw_preset_str.startswith('gpu:')

        if encoder_override != EncoderOverride.AUTO:
            if is_gpu_encoder and not preset_is_gpu:
                print_err(f"Error: Hardware preset '{hw_preset_str}' is not compatible with GPU encoder '{encoder_override.value}'.")
                print_err(f"Use 'gpu:{hw_preset_str.split(':')[1]}' or a prefix-free preset like '{hw_preset_str.split(':')[1]}'.")
                sys.exit(1)
            elif not is_gpu_encoder and preset_is_gpu:
                print_err(f"Error: Hardware preset '{hw_preset_str}' is not compatible with CPU encoder '{encoder_override.value}'.")
                print_err(f"Use 'cpu:{hw_preset_str.split(':')[1]}' or a prefix-free preset like '{hw_preset_str.split(':')[1]}'.")
                sys.exit(1)

        # Prefix is valid or encoder is AUTO
        return hw_preset_str

    # Prefix-free preset - add appropriate prefix based on encoder
    prefix = 'gpu' if is_gpu_encoder else 'cpu'
    return f"{prefix}:{hw_preset_str}"

def _get_hdr_forge_encoder_presets_from_args(args, encoder_override: EncoderOverride) -> HdrForgeEncodingPresetSettings:
    """Create HdrForgeEncodingPresetSettings object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()
        encoder_override: Encoder override for validation

    Returns:
        HdrForgeEncodingPresetSettings object with preset and hardware preset
    """
    preset: HdrForgeEncodingPresets
    hw_preset: HdrForgeEncodingHardwarePresets
    if args.preset is None:
        preset = HdrForgeEncodingPresets.AUTO
    else:
        try:
            preset = HdrForgeEncodingPresets(args.preset)
        except ValueError:
            print_err(msg=f"Invalid preset value '{args.preset}'")
            sys.exit(1)

    # Validate and normalize hw_preset with encoder compatibility check
    hw_preset_str = args.hw_preset if args.hw_preset is not None else "cpu:balanced"
    validated_hw_preset_str: str = _validate_hw_preset_with_encoder(hw_preset_str=hw_preset_str, encoder_override=encoder_override)

    try:
        hw_preset = HdrForgeEncodingHardwarePresets(validated_hw_preset_str)
    except ValueError:
        print_err(msg=f"Invalid hardware preset value '{validated_hw_preset_str}'")
        sys.exit(1)

    return HdrForgeEncodingPresetSettings(
        preset=preset,
        hardware_preset=hw_preset,
    )

def get_hdr_metadata_from_args(args) -> HdrMetadata:
    """Create HdrMetadata object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()

    Returns:
        HdrMetadata object with mastering display and content light level metadata
    """
    return HdrMetadata(
        mastering_display_metadata=_get_master_display_from_string(getattr(args, 'master_display', None)),
        content_light_level_metadata=_get_content_lightLevel_metadata_from_string(getattr(args, 'max_cll', None))
    )

def create_encoder_settings_from_args(args) -> EncoderSettings:
    """Create EncoderSettings object from parsed command-line arguments.

    Args:
        args: Parsed arguments from parse_args()

    Returns:
        EncoderSettings object with all encoding parameters
    """
    # Parse encoder override
    encoder_override: EncoderOverride = _get_encoder_override_from_string(encoder_str=getattr(args, 'encoder', 'auto'))

    # Parse universal parameters
    universal_params: UniversalEncoderParams = _get_universal_params_from_args(args)

    # Validate --speed with NVENC encoders
    if universal_params.speed is not None and encoder_override in [EncoderOverride.HEVC_NVENC, EncoderOverride.H264_NVENC]:
        print_err("Error: --speed is not supported with NVENC encoders. Use --encoder-params 'preset=hq' instead.")
        sys.exit(1)

    # Parse encoder-specific parameters from --encoder-params
    encoder_params_libx265: Libx265Params | None
    encoder_params_libx264: Libx264Params | None
    encoder_params_nvenc: NvencParams | None
    encoder_params_libx265, encoder_params_libx264, encoder_params_nvenc = _parse_encoder_params(
        params_str=getattr(args, 'encoder_params', None),
        encoder_override=encoder_override
    )

    # Use encoder-params if provided, otherwise default to empty params
    libx265_params: Libx265Params = encoder_params_libx265 if encoder_params_libx265 is not None else Libx265Params()
    libx264_params: Libx264Params = encoder_params_libx264 if encoder_params_libx264 is not None else Libx264Params()
    nvenc_params: NvencParams = encoder_params_nvenc if encoder_params_nvenc is not None else NvencParams()

    hdr_metadata: HdrMetadata = get_hdr_metadata_from_args(args)

    # Get validated hardware preset settings (includes encoder compatibility check)
    hdr_forge_preset_settings: HdrForgeEncodingPresetSettings = _get_hdr_forge_encoder_presets_from_args(args, encoder_override)

    return EncoderSettings(
        video_codec=_get_video_codec_from_string(codec_str=args.video_codec),
        vfilter=getattr(args, 'vfilter', None),
        dar_ratio=_get_dar_ratio_settings_from_string(getattr(args, 'dar_ratio', None)),
        hdr_forge_encoding_preset=hdr_forge_preset_settings,
        hdr_sdr_format=_get_hdr_sdr_format_from_string(format_str=args.hdr_sdr_format),
        enable_gpu_acceleration=hdr_forge_preset_settings.hardware_preset.value.startswith('gpu:'),
        target_dv_profile=_get_dolby_vision_profile_from_string(profile_str=args.dv_profile),
        libx265_params=libx265_params,
        libx264_params=libx264_params,
        nvenc_params=nvenc_params,
        universal_params=universal_params,
        encoder_override=encoder_override,
        scale_height=_get_scale_height(scale=args.scale),
        scale_mode=ScaleMode(args.scale_mode),
        crop=_get_crop_settings_from_string(crop_str=args.crop),
        grain=_get_grain_settings_from_string(grain_str=args.grain),
        logo_removal=_get_logo_removal_mode_from_string(logo_str=args.remove_logo),
        sample=_get_sample_settings_from_string(sample_str=args.sample),
        hdr_metadata=hdr_metadata,
    )


def print_parameter_warnings(encoder_settings: EncoderSettings, active_encoder_lib: VideoEncoderLibrary) -> None:
    """Print warnings for incompatible encoder parameters.

    Args:
        encoder_settings: EncoderSettings object
        active_encoder_lib: Currently active encoder library
    """
    # Check for x265-specific parameters with non-x265 encoder
    if active_encoder_lib != VideoEncoderLibrary.LIBX265:
        libx265_params: Libx265Params = encoder_settings.libx265_params
        if libx265_params.crf is not None or libx265_params.preset is not None or libx265_params.tune is not None:
            print_warn(f"Warning: --encoder-params for x265 specified but using {active_encoder_lib.value} encoder. Parameters will be ignored.")

    # Check for x264-specific parameters with non-x264 encoder
    if active_encoder_lib != VideoEncoderLibrary.LIBX264:
        libx264_params: Libx264Params = encoder_settings.libx264_params
        if libx264_params.crf is not None or libx264_params.preset is not None or libx264_params.tune is not None:
            print_warn(f"Warning: --encoder-params for x264 specified but using {active_encoder_lib.value} encoder. Parameters will be ignored.")

    # Check for nvenc-specific parameters with non-nvenc encoder
    if active_encoder_lib not in [VideoEncoderLibrary.HEVC_NVENC, VideoEncoderLibrary.H264_NVENC]:
        nvenc_params: NvencParams = encoder_settings.nvenc_params
        if nvenc_params.cq is not None or nvenc_params.preset is not None or nvenc_params.rc is not None:
            print_warn(f"Warning: --encoder-params for NVENC specified but using {active_encoder_lib.value} encoder. Parameters will be ignored.")
