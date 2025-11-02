# HDR Forge - Codebase Documentation for Claude Code

## Project Overview

HDR Forge (Easy HDR Video Converter) is a Python-based command-line tool for converting video files with intelligent HDR metadata preservation, automatic quality optimization, hardware acceleration support, and advanced encoding features including grain analysis and flexible cropping.

**Current Version:** Python v0.6.0

## Documentation Structure

**IMPORTANT:** When updating user-facing documentation, always consider the modular documentation structure:

### Main README.md
- **Purpose:** User-friendly overview and quick start guide
- **Content:** Basic usage, installation, common examples, quick reference
- **Target Length:** ~600 lines (keep it concise!)
- **Rule:** Technical details should be moved to `documentation/` files

### documentation/ Directory

**When to update documentation files:**

1. **encoders.md** - Update when:
   - Adding new encoder support
   - Changing encoder selection logic
   - Updating hardware requirements
   - Adding encoder-specific features
   - Modifying performance characteristics

2. **advanced-examples.md** - Update when:
   - Adding new CLI parameters
   - Creating new feature combinations
   - Adding complex workflows
   - Providing use-case-specific examples

3. **technical-details.md** - Update when:
   - Changing internal algorithms
   - Modifying parameter priority systems
   - Updating auto-calculation logic
   - Changing filter chains or processing workflows
   - Adding technical implementation details

4. **troubleshooting.md** - Update when:
   - Discovering new common issues
   - Adding error message explanations
   - Creating solutions for known problems
   - Updating dependency requirements

**Best Practices:**
- Keep README.md high-level and user-friendly
- Move technical details to appropriate documentation files
- Add cross-references between documentation files
- Update all affected files when making changes
- Ensure consistency across all documentation

## Technology Stack

-   **Language:** Python 3.7+
-   **Video Processing:** ffmpeg, ffprobe
-   **Hardware Acceleration:** NVIDIA NVENC (HEVC/H.264)
-   **Key Dependencies:**
    -   `python-ffmpeg` - FFmpeg wrapper for Python
    -   `dovi_tool` - Dolby Vision RPU extraction (external binary)
    -   `hevc_hdr_editor` - HDR metadata injection into HEVC bitstreams (external binary)
    -   `mkvmerge` - MKV container operations (external binary)
    -   `numpy` - MaxCLL/MaxFALL calculation

## Project Structure

```
hdr_forge/
├── documentation/                            # User documentation (modular structure)
│   ├── README.md                             # Documentation overview and navigation
│   ├── encoders.md                           # Encoder guide and comparisons
│   ├── advanced-examples.md                  # Complex encoding workflows
│   ├── technical-details.md                  # In-depth technical information
│   └── troubleshooting.md                    # Common issues and solutions
├── src/hdr_forge/
│   ├── __init__.py                           # Package initialization with version info
│   ├── main.py                               # CLI entry point with argparse (272 lines)
│   ├── video.py                              # Video metadata extraction and analysis (476 lines)
│   ├── encoder.py                            # Unified encoder orchestration (681 lines)
│   ├── hdr_metadata_injector.py              # HDR metadata injection without re-encoding (73 lines)
│   ├── cli/
│   │   ├── cli_output.py                     # Progress tracking and colored terminal output
│   │   ├── encoder.py                        # Encoder CLI output helpers
│   │   ├── video.py                          # Video info CLI output
│   │   ├── video_codec_base.py               # CLI helpers for video codec info
│   │   └── args/
│   │       ├── pars_args.py                  # CLI argument parsing
│   │       └── pars_encoder_settings.py      # Encoder settings from CLI args
│   ├── typedefs/
│   │   ├── video_typing.py                   # Video-related type definitions
│   │   ├── encoder_typing.py                 # Encoder settings and parameter types
│   │   ├── dolby_vision_typing.py            # Dolby Vision type definitions
│   │   ├── ffmpeg_typing.py                  # FFmpeg-related types
│   │   └── mkv_typing.py                     # MKV container types
│   ├── ffmpeg/
│   │   ├── ffmpeg_wrapper.py                 # FFmpeg execution wrapper
│   │   └── video_codec/
│   │       ├── video_codec_base.py           # Base class for video codecs (11934 lines)
│   │       ├── libx265.py                    # libx265 encoder implementation (261 lines)
│   │       ├── libx264.py                    # libx264 encoder implementation (5985 lines)
│   │       ├── hevc_nvenc.py                 # HEVC NVENC encoder implementation (166 lines)
│   │       ├── h264_nvenc.py                 # H.264 NVENC encoder implementation (4438 lines)
│   │       └── service/
│   │           └── presets.py                # Hardware preset calculations
│   ├── tools/
│   │   ├── dovi_tool.py                      # Dolby Vision RPU/EL operations (19881 lines)
│   │   ├── hevc_hdr_editor.py                # HDR metadata injection tool (6491 lines)
│   │   └── mkvmerge.py                       # MKV muxing/demuxing operations (5873 lines)
│   ├── analyze/
│   │   └── maxcll.py                         # MaxCLL/MaxFALL calculation with parallel processing
│   └── core/
│       ├── config.py                         # Global configuration (debug mode)
│       └── service.py                        # Helper functions for FFmpeg commands
├── README.md                                 # User documentation
└── pyproject.toml                            # Python project configuration
```

## Module Breakdown

### 1. main.py (CLI Entry Point)

**Lines:** 272 | **Key Function:** CLI argument parsing and command routing

**Subcommands:**

-   `info` - Display detailed video information
-   `convert` - Convert videos with format conversion support
-   `calc_maxcll` - Calculate MaxCLL and MaxFALL values (BETA)
-   `inject-hdr-metadata` - Inject HDR metadata into HEVC bitstream without re-encoding

**Key Functions:**

-   `get_video_files(path, supported_formats)` - Find video files in path/directory
-   `determine_output_file(video_file, output_path, is_batch)` - Calculate output path
-   `show_video_info(input_file)` - Display video information
-   `convert_video(video, target_file, settings)` - Universal conversion function
-   `process_convert_command(args)` - Handle video conversion workflow
-   `process_info_command(args)` - Display video information
-   `process_inject_hdr_metadata_command(args)` - Inject HDR metadata into existing video

**Features:**

-   Batch folder processing
-   Auto-detection of video format (SDR/HDR10/Dolby Vision)
-   Format conversion: Dolby Vision → HDR10 → SDR (downgrades only)
-   Multiple video codec support (h265, h264, copy)
-   Hardware acceleration (NVIDIA NVENC)
-   Resolution scaling with multiple modes (height, adaptive)
-   Flexible cropping (auto, manual, aspect ratio presets, off)
-   Grain analysis and optimization
-   HDR Forge presets (auto, film, action, animation)
-   Hardware presets (cpu:balanced, cpu:quality, gpu:balanced, gpu:quality)
-   Video sampling for testing
-   Custom HDR metadata injection
-   Dolby Vision profile selection (auto, 8)

**Supported Formats:** `.mkv`, `.m2ts`, `.ts`, `.mp4`

### 2. video.py (Metadata Extraction)

**Lines:** 476 | **Key Class:** `Video`

**Core Responsibilities:**

-   Extract video metadata using ffprobe
-   Parse HDR metadata (master display, content light level)
-   Detect Dolby Vision profiles and enhancement layers
-   Determine video format (SDR/HDR10/Dolby Vision)
-   Calculate video dimensions and pixel count

**Key Methods:**

-   `__init__(filepath)` - Initialize video with metadata extraction
-   `is_hdr_video()` - Detect HDR by checking for 10-bit pixel format
-   `is_dolby_vision_video()` - Check for Dolby Vision RPU flag
-   `get_dolby_vision_profile()` - Get Dolby Vision profile number
-   `get_dolby_vision_enhancement_layer()` - Get enhancement layer info
-   `get_master_display()` - Extract master display metadata
-   `get_content_light_level_metadata()` - Extract MaxCLL/MaxFALL values
-   `get_hdr_sdr_format()` - Determine video format (SDR/HDR10/DOLBY_VISION)
-   `get_duration_seconds()` - Get video duration
-   `get_total_frames()` - Get total frame count
-   `get_pixel_count()` - Calculate total pixel count (width × height)

### 3. encoder.py (Unified Video Encoder Orchestration)

**Lines:** 681 | **Key Class:** `Encoder`

**Purpose:** Orchestrates video encoding by coordinating codec selection, format detection, and conversion workflows

**Key Methods:**

-   `__init__(video, target_file, settings)` - Initialize encoder with video and settings
-   `get_available_hw_encoders()` - Detect available hardware encoders (NVENC)
-   `_get_video_codec_lib_instance(settings, video, scale_tuple)` - Select and instantiate codec
-   `_get_codec_from_override(settings, video, scale_tuple)` - Get codec from explicit override
-   `_determine_dv_profile(dv_profile)` - Determine Dolby Vision profile for encoding
-   `_determine_dv_enhancement_layer(target_dv_profile)` - Determine if EL should be preserved
-   `_determine_video_sample(sample_settings)` - Calculate video sampling times
-   `_build_ffmpeg_output_options()` - Build complete FFmpeg option dictionary
-   `_run_ffmpeg_encoding_process(input_file, target_file)` - Execute FFmpeg with progress
-   `convert_sdr_hdr10()` - Execute SDR/HDR10 conversion
-   `convert_dolby_vision_to_hdr10_without_re_encoding()` - Extract DV base layer (copy mode)
-   `convert_dolby_vision_to_other_profile_without_re_encoding()` - Convert DV profile (copy mode)
-   `_convert_dolby_profile(input_file, hevc_bl, source_dv_profile, target_dv_profile)` - Convert DV profile with RPU/EL
-   `convert_dolby_vision()` - Execute Dolby Vision conversion with re-encoding
-   `convert()` - Universal conversion method (routes to appropriate workflow)

**Encoder Selection Priority:**

1. `--encoder` flag (explicit override: libx265, libx264, hevc_nvenc, h264_nvenc)
2. `--video-codec` + `--hw-preset` (automatic selection based on hardware)
3. Default: x265 with CPU encoding

**Format Conversion Rules:**

-   AUTO: Keep source format
-   Only downgrades allowed: Dolby Vision → HDR10 → SDR
-   Upgrades blocked with error (e.g., cannot SDR → HDR10)
-   HDR to SDR includes tone mapping using zscale + Hable algorithm

### 4. ffmpeg/video_codec/ (Video Codec Implementations)

**Architecture:** Base class pattern with codec-specific implementations

#### 4.1 video_codec_base.py (Base Codec Class)

**Lines:** 11934 | **Purpose:** Abstract base class for all video encoders

**Key Features:**

-   HDR/SDR format determination with validation
-   Automatic CRF/CQ/preset selection based on resolution and content
-   Grain analysis integration
-   Filter chain building (crop, scale, tone mapping)
-   Hardware preset calculations
-   HDR metadata handling

**Key Methods:**

-   `__init__(lib, encoder_settings, video, scale, supported_hdr_sdr_formats)` - Initialize codec
-   `get_encoding_hdr_sdr_format()` - Determine effective encoding format
-   `_determine_effective_hdr_sdr_format(target_hdr_sdr_format)` - Validate and determine format
-   `calc_hw_preset_settings(preset_class)` - Calculate hardware preset values
-   `_build_filter_chain()` - Build complete FFmpeg filter chain
-   `_get_crop_filter()` - Generate crop filter
-   `_get_scale_filter()` - Generate scale filter (height or adaptive mode)
-   `_get_tone_mapping_filter()` - Generate tone mapping filter (zscale + tonemap)
-   `_calculate_crf_adjustment_weight(current_crf, crf_delta)` - Calculate CRF adjustment weight
-   `get_ffmpeg_params()` - Get FFmpeg parameters (abstract, implemented by subclasses)
-   `get_custom_lib_parameters()` - Get codec-specific parameters (abstract)
-   `get_hdr_metadata_for_encoding()` - Get HDR metadata for encoding (abstract)

**Tone Mapping Filter (HDR→SDR):**

```python
zscale=
    transfer=linear:
    npl=100,
    format=gbrpf32le,
    tonemap=hable:
    desat=0,
    zscale=
    transfer=bt709:
    matrix=bt709:
    range=tv:
    primaries=bt709,
    format=yuv420p
```

#### 4.2 libx265.py (x265 CPU Encoder)

**Lines:** 261 | **Purpose:** Software HEVC encoding with libx265

**HDR Support:** HDR10, SDR, Dolby Vision (BL encoding)

**HDR x265 Parameters:**

```python
HDR_X265_PARAMS = [
    'profile=main10',
    'hdr-opt=1',
    'hdr10=1',
    'repeat-headers=1',
    'colorprim=bt2020',
    'transfer=smpte2084',
    'colormatrix=bt2020nc',
]
```

**SDR x265 Parameters:**

```python
SDR_X265_PARAMS = [
    'profile=main',
    'hdr-opt=0',
    'hdr10=0',
    'no-hdr10-opt=1',
    'colorprim=bt709',
    'transfer=bt709',
    'colormatrix=bt709',
]
```

**Parameter Priority (CRF):**

1. `--encoder-params` (libx265_params.crf)
2. `--quality` (universal_params.quality)
3. Auto-detection (hw_preset + HDR adjustment + action/grain adjustments)

**Parameter Priority (Preset):**

1. `--encoder-params` (libx265_params.preset)
2. `--speed` (universal_params.speed)
3. Auto-detection (hw_preset.preset)

**Parameter Priority (Tune):**

1. `--encoder-params` (libx265_params.tune)
2. Auto-detection (animation preset or grain category ≥2)

**Auto-CRF Adjustments:**

-   HDR10/DV: +1.0 CRF (10-bit allows higher CRF without quality loss)
-   Action preset: -2.0 CRF (weighted adjustment for fast motion)
-   Grain detection: Variable adjustment based on grain category

#### 4.3 libx264.py (x264 CPU Encoder)

**Lines:** 5985 | **Purpose:** Software H.264 encoding with libx264

**HDR Support:** SDR only (no HDR10 or Dolby Vision)

**Similar parameter priority and adjustment logic as libx265**

#### 4.4 hevc_nvenc.py (NVIDIA HEVC Hardware Encoder)

**Lines:** 166 | **Purpose:** Hardware-accelerated HEVC encoding

**HDR Support:** HDR10, SDR, Dolby Vision (BL encoding)

**Key Parameters:**

-   HDR10: `profile=main10`, `pix_fmt=p010le`, metadata in `metadata:s:v`
-   SDR: `profile=main`, `pix_fmt=yuv420p`
-   Rate control: `rc=vbr_hq` (variable bitrate, high quality)

**Parameter Priority (CQ):**

1. `--encoder-params` (nvenc_params.cq)
2. `--quality` (universal_params.quality)
3. Auto-detection (hw_preset.cq + adjustments)

**Parameter Priority (Preset):**

1. `--encoder-params` (nvenc_params.preset)
2. Auto-detection (hw_preset.preset)

**NVENC Presets:** default, slow, hq, llhq, llhp

**Current Limitations:**

-   Dolby Vision metadata injection not yet supported (warning issued)
-   HDR→SDR metadata removal not supported (warning issued)

#### 4.5 h264_nvenc.py (NVIDIA H.264 Hardware Encoder)

**Lines:** 4438 | **Purpose:** Hardware-accelerated H.264 encoding

**HDR Support:** SDR only (no HDR10 or Dolby Vision)

**Similar parameter structure and priority as hevc_nvenc**

### 5. tools/dovi_tool.py (Dolby Vision Operations)

**Lines:** 19881 | **Purpose:** Complete Dolby Vision metadata and layer handling

**Supported Profiles:**

-   Profile 5 (IPTPQc2, BL+RPU) → Converts to Profile 8.1 (mode 3)
-   Profile 7 (MEL, BL+EL+RPU) → Preserves Profile 7 or converts to Profile 8.1 (mode 2)
-   Profile 8 (BL+RPU) → Keeps Profile 8.1 (mode 2)

**Key Functions:**

-   `get_dovi_tool_path()` - Locate dovi_tool binary (project root or system PATH)
-   `extract_base_layer(input_path, output_hevc)` - Extract HDR10 base layer (HEVC without RPU)
-   `extract_rpu(input_path, output_rpu, dv_profile_source, dv_profile_encoding)` - Extract RPU with profile-specific mode
-   `inject_rpu(input_path, input_rpu, output_hevc)` - Inject RPU metadata into HEVC
-   `extract_enhancement_layer(input_file, output_el)` - Extract EL for Profile 7
-   `inject_dolby_vision_layers(bl_path, el_path, output_bl_el)` - Multiplex BL and EL

**RPU Extraction Pipeline:**

```bash
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - |
dovi_tool [-m MODE] extract-rpu - -o output.rpu
```

**Mode Selection for Profile Conversion:**

-   Profile 5 → Profile 8.1: Mode 3 (IPTPQc2 to MEL)
-   Profile 7 → Profile 8.1: Mode 2 (MEL to MEL)
-   Profile 7 → Profile 7: Mode 2 (with EL extraction)
-   Profile 8 → Profile 8.1: Mode 2 (default)

**Base Layer Extraction:**

```bash
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - |
dovi_tool remove - -o output_BL.hevc
```

**Tool Location Priority:**

1. Local `dovi_tool` in project root
2. System `dovi_tool` in PATH

### 6. tools/hevc_hdr_editor.py (HDR Metadata Injection)

**Lines:** 6491 | **Purpose:** Inject HDR metadata into HEVC bitstream without re-encoding

**Key Functions:**

-   `get_hevc_hdr_editor_path()` - Locate hevc_hdr_editor binary
-   `create_config_json_for_hevc_hdr_editor(hdr_metadata, output_json)` - Create JSON config
-   `inject_hdr_metadata(input_path, config_json, output_hevc)` - Inject metadata into HEVC

**Use Case:** Add or update HDR10 metadata (master display, MaxCLL/MaxFALL) in existing HEVC files without re-encoding

### 7. tools/mkvmerge.py (MKV Container Operations)

**Lines:** 5873 | **Purpose:** MKV container muxing and demuxing

**Key Functions:**

-   `get_mkvmerge_path()` - Locate mkvmerge binary
-   `mux_hevc_to_mkv(input_hevc_path, input_mkv, output_mkv)` - Mux HEVC video with audio/subs from MKV
-   `extract_hevc(input_path, output_hevc)` - Extract HEVC video stream from MKV

**Usage:** Combines encoded HEVC video with original audio/subtitle streams

### 8. analyze/maxcll.py (MaxCLL/MaxFALL Calculation)

**Purpose:** Parallel HDR10 MaxCLL/MaxFALL calculation using PQ EOTF

**Key Features:**

-   Parallel segment processing with multiprocessing.Pool
-   PQ (ST.2084) to nits conversion using ITU-R BT.2100 EOTF
-   BT.2020 luminance calculation
-   Hardware acceleration support (auto-detection)
-   Progress bar with segment tracking

**Key Functions:**

-   `calc_maxcll(video_path)` - Calculate MaxCLL and MaxFALL from video content
-   `pq_to_nits(pq)` - Convert PQ values to nits
-   `process_segment(args)` - Process video segment in parallel
-   `get_video_info(video_path)` - Get video metadata for processing

**Algorithm:**

1. Split video into segments (default 30s each)
2. Process segments in parallel (CPU count workers)
3. Decode to RGB48LE format
4. Convert RGB values to luminance using BT.2020 coefficients
5. Apply PQ EOTF to convert to nits
6. Calculate MaxCLL (max pixel luminance) and MaxFALL (max frame average)

### 9. hdr_metadata_injector.py (HDR Metadata Injector)

**Lines:** 73 | **Purpose:** Inject HDR metadata into videos without re-encoding

**Key Class:** `HdrMetadataInjector`

**Key Methods:**

-   `__init__(input_file, target_file, metadata)` - Initialize injector
-   `inject_metadata()` - Execute injection workflow
-   `_get_temp_directory()` - Create temporary directory
-   `_cleanup_temp_directory()` - Clean up temporary files

**Workflow:**

1. Create JSON config with HDR metadata
2. Extract HEVC stream from input
3. Inject metadata using hevc_hdr_editor
4. Mux HEVC back with original audio/subs

### 10. cli/args/pars_args.py (CLI Argument Parsing)

**Lines:** 411 | **Purpose:** Define all CLI arguments and subcommands

**Subcommands:**

-   `info` - Video information display
-   `convert` - Video conversion with all options
-   `calc_maxcll` - MaxCLL/MaxFALL calculation
-   `inject-hdr-metadata` - HDR metadata injection

**Convert Arguments:**

-   `-v, --video-codec` - Video codec selection (x265, x264, copy)
-   `-p, --preset` - HDR Forge preset (auto, film, action, animation)
-   `--hw-preset` - Hardware preset (cpu:balanced, cpu:quality, gpu:balanced, gpu:quality)
-   `--quality` - Universal quality parameter (0-51)
-   `--speed` - Encoding speed preset (ultrafast to veryslow, libx265/libx264 only)
-   `--crop` - Crop mode (off, auto, manual, aspect ratio)
-   `--grain` - Grain analysis (off, auto, cat1, cat2, cat3)
-   `--scale` - Target resolution (FUHD, UHD, WQHD, FHD, HD, SD, or height)
-   `--scale-mode` - Scale mode (height, adaptive)
-   `--hdr-sdr-format` - Target format (auto, hdr10, sdr)
-   `--dv-profile` - Dolby Vision profile (auto, 8)
-   `--sample` - Video sampling (auto, start:end)
-   `--master-display` - Custom master display metadata
-   `--max-cll` - Custom MaxCLL/MaxFALL values
-   `--encoder` - Encoder override (auto, libx265, libx264, hevc_nvenc, h264_nvenc)
-   `--encoder-params` - Encoder-specific parameters
-   `-d, --debug` - Debug mode

### 11. typedefs/ (Type Definitions)

**Purpose:** Centralized type definitions and data structures

**Key Files:**

-   `video_typing.py` - Video metadata types (HdrMetadata, MasterDisplayMetadata, ContentLightLevelMetadata)
-   `encoder_typing.py` - Encoder settings and parameter types (EncoderSettings, VideoCodec, HdrSdrFormat, EncoderOverride, HdrForgeEncodingPresets, Libx265Params, NvencParams)
-   `dolby_vision_typing.py` - Dolby Vision types (DolbyVisionProfile, DolbyVisionEnhancementLayer, DolbyVisionProfileEncodingMode)
-   `ffmpeg_typing.py` - FFmpeg-related types
-   `mkv_typing.py` - MKV container types

**Key Enums:**

-   `VideoCodec` - Target video codec (X265, X264, COPY)
-   `VideoEncoderLibrary` - Encoder library (LIBX265, LIBX264, HEVC_NVENC, H264_NVENC)
-   `HdrSdrFormat` - Video format (SDR, HDR10, DOLBY_VISION)
-   `EncoderOverride` - Encoder override (AUTO, LIBX265, LIBX264, HEVC_NVENC, H264_NVENC)
-   `HdrForgeEncodingPresets` - HDR Forge presets (AUTO, FILM, ACTION, ANIMATION)
-   `DolbyVisionProfile` - Dolby Vision profile numbers (_5, _7, _8)
-   `DolbyVisionProfileEncodingMode` - DV profile mode (AUTO, _8)

## Conversion Workflows

### SDR/HDR10 Conversion (FFmpeg + Encoder)

1. Create `Encoder` instance with video and settings
2. Select video codec based on settings and hardware availability
3. Determine effective HDR/SDR format (validate no upgrades)
4. Build filter chain (crop, scale, tone mapping if needed)
5. Build encoder-specific parameters (CRF/CQ, preset, x265-params)
6. Build FFmpeg output options
7. Execute FFmpeg with progress tracking
8. Copy audio and subtitle streams

**Format-Specific Processing:**

-   **HDR10:** Preserve HDR metadata via x265-params or metadata:s:v
-   **SDR from HDR:** Apply tone mapping filter, remove HDR metadata
-   **SDR from SDR:** Standard re-encoding with BT.709 color space

**Encoder Selection:**

-   Explicit: `--encoder libx265` or `hevc_nvenc`
-   Automatic: Based on `--hw-preset` and available hardware
-   GPU presets automatically select NVENC if available

### Dolby Vision Conversion (Three Workflows)

#### Workflow 1: DV → HDR10/SDR (Copy Mode, No Re-encoding)

**Command:** `--video-codec copy --hdr-sdr-format hdr10`

1. Extract base layer (HEVC without RPU) using `dovi_tool remove`
2. Mux BL HEVC with original audio/subtitles into target MKV
3. Clean up temporary directory

**Use Case:** Quick extraction of HDR10 base layer without re-encoding

#### Workflow 2: DV → DV (Copy Mode, Profile Conversion Only)

**Command:** `--video-codec copy --dv-profile 8`

1. Extract base layer (HEVC without RPU) using `dovi_tool remove`
2. Extract RPU with profile-specific mode conversion
3. If Profile 7 → Profile 7: Extract EL and multiplex with BL
4. Inject RPU into base layer HEVC
5. Mux HEVC (with RPU/EL+RPU) with audio/subs into target MKV
6. Clean up temporary directory

**Use Case:** Convert Dolby Vision profile without re-encoding video

#### Workflow 3: DV → Any Format (With Re-encoding)

**Command:** `--video-codec x265` (default)

1. **Extract Base Layer:**
   - Extract HEVC bitstream from source video
   - Use `dovi_tool remove` to strip RPU metadata
   - Result: HDR10-only base layer (BL)

2. **Prepare Base Layer for Encoding:**
   - Mux BL HEVC with original audio/subtitles into temporary MKV
   - Delete intermediate HEVC file

3. **Re-encode Base Layer:**
   - Apply FFmpeg encoding with selected codec, CRF/CQ, filters
   - For DV → HDR10/SDR: Write directly to target file and stop here
   - For DV → DV: Write to temporary MKV and continue

4. **Extract Encoded HEVC (DV → DV only):**
   - Demux encoded video stream from MKV container
   - Delete intermediate MKV file

5. **Extract and Prepare RPU Metadata (DV → DV only):**
   - Extract RPU with profile-specific mode (`dovi_tool extract-rpu -m MODE`)
   - For Profile 7 with AUTO: Extract Enhancement Layer (EL) and multiplex with BL

6. **Inject RPU into Encoded Video (DV → DV only):**
   - Use `dovi_tool inject-rpu` to add RPU metadata to encoded HEVC
   - Delete intermediate files (HEVC without RPU, RPU file)

7. **Final Muxing:**
   - Mux HEVC (with RPU if DV) + audio/subtitles into target MKV
   - Clean up temporary directory

**Temporary Files Management:**

-   All intermediate files stored in `.hdr_forge_temp_{filename}/` directory
-   Files deleted incrementally as soon as no longer needed
-   Entire temp directory removed at end of workflow

**Profile-Specific Handling:**

-   **Profile 5 (IPTPQc2):** Convert to Profile 8.1 (Mode 3)
-   **Profile 7 (MEL with EL):** Keep Profile 7 (extract EL, mux BL+EL) or convert to Profile 8.1 (Mode 2)
-   **Profile 8:** Keep Profile 8.1 (Mode 2)

**Important Limitations:**

-   Dolby Vision does NOT support cropping when preserving DV format
-   Dolby Vision does NOT support scaling when preserving DV format (RPU metadata is frame-position dependent)
-   Cropping/scaling ARE supported when converting DV → HDR10/SDR
-   Video sampling NOT supported for Dolby Vision encoding

### HDR Metadata Injection (Without Re-encoding)

**Command:** `hdr_forge inject-hdr-metadata -i input.mkv --master-display "..." --max-cll "..."`

1. Create JSON config with HDR metadata
2. Extract HEVC stream from input MKV
3. Inject metadata into HEVC using hevc_hdr_editor
4. Mux HEVC back with original audio/subs into target MKV
5. Clean up temporary directory

**Use Case:** Add or update HDR10 metadata in existing videos without re-encoding

## CLI Usage Examples

```bash
# Show video info
hdr_forge info -i input.mkv

# Convert video with auto settings (keeps source format)
hdr_forge convert -i input.mkv -o output.mkv

# Convert with GPU acceleration (NVENC)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# Convert with explicit encoder override
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# Convert with custom quality
hdr_forge convert -i input.mkv -o output.mkv --quality 16

# Convert with CPU-specific quality preset
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

# Convert with HDR Forge film preset
hdr_forge convert -i input.mkv -o output.mkv --preset film

# Convert action content (optimized for fast motion)
hdr_forge convert -i input.mkv -o output.mkv --preset action

# Batch convert folder
hdr_forge convert -i ./input_folder -o ./output_folder

# Scale video to 1080p with height mode (default)
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD

# Scale video with adaptive mode (fits within target resolution)
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale UHD --scale-mode adaptive

# Automatic black bar cropping
hdr_forge convert -i input.mkv -o output.mkv --crop auto

# Manual cropping
hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140

# Crop to 21:9 aspect ratio
hdr_forge convert -i input.mkv -o output.mkv --crop 21:9

# Disable cropping
hdr_forge convert -i input.mkv -o output.mkv --crop off

# Enable grain analysis
hdr_forge convert -i input.mkv -o output.mkv --grain auto

# Convert Dolby Vision to HDR10 (extracts base layer)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format hdr10

# Convert Dolby Vision to HDR10 without re-encoding (copy mode)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --video-codec copy --hdr-sdr-format hdr10

# Convert Dolby Vision to SDR with tone mapping
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format sdr

# Convert HDR10 to SDR with tone mapping
hdr_forge convert -i hdr10_video.mkv -o output.mkv --hdr-sdr-format sdr

# Preserve Dolby Vision with re-encoding
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop off

# Force Dolby Vision Profile 8.1 output (from Profile 5/7/8)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --dv-profile 8 --crop off

# Convert DV profile without re-encoding (copy mode)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --video-codec copy --dv-profile 8

# Process 30-second sample for testing (auto: 1:00-1:30)
hdr_forge convert -i input.mkv -o sample.mkv --sample auto

# Process custom sample (1:30-2:00)
hdr_forge convert -i input.mkv -o sample.mkv --sample 90:120

# Set custom HDR metadata during encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# Inject HDR metadata without re-encoding
hdr_forge inject-hdr-metadata -i input.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# Advanced: Expert mode with encoder-specific parameters
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=slow:crf=14:tune=grain"

hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"

# Calculate MaxCLL and MaxFALL (BETA feature)
hdr_forge calc_maxcll -i input.mkv

# Enable debug mode
hdr_forge convert -i input.mkv -o output.mkv --debug
```

## Key Technical Details

### Encoder Selection Algorithm

**Priority:**

1. **Explicit Override:** `--encoder` flag (libx265, libx264, hevc_nvenc, h264_nvenc)
2. **Automatic Selection:** Based on `--hw-preset` and available hardware
   - `gpu:balanced` or `gpu:quality` → NVENC (if available, otherwise error)
   - `cpu:balanced` or `cpu:quality` → libx265 or libx264
   - Prefix-free presets (`balanced`, `quality`) → Derived from codec and availability

**Hardware Detection:**

-   Query `ffmpeg -encoders` for available encoders
-   Check for NVENC availability (nvenc, qsv, vaapi, amf, v4l2)
-   Error if GPU preset selected but hardware not available

### Parameter Priority System

**Universal Parameters (Work with all encoders):**

-   `--quality` (0-51) → Maps to CRF (libx265/libx264) or CQ (NVENC)
-   `--speed` (ultrafast to veryslow) → Only for libx265/libx264

**Encoder-Specific Parameters:**

-   `--encoder-params` → Highest priority, overrides all auto-detection
-   Format: `preset=value:crf=value:tune=value` (libx265/libx264)
-   Format: `preset=value:cq=value:rc=value` (NVENC)

**Auto-Detection Parameters:**

-   `--hw-preset` → Defines baseline CRF/CQ and preset
-   `--preset` (film, action, animation) → Adjusts encoding parameters
-   `--grain` → Adjusts CRF and tune based on grain analysis

**Priority Chain Example (CRF):**

1. `--encoder-params` (e.g., `crf=14`) → Use 14
2. `--quality 16` → Use 16
3. Auto-detection → Calculate from hw_preset + adjustments

### Auto-CRF/CQ Calculation

**Base CRF from hw_preset:**

-   `cpu:balanced` / `gpu:balanced`: Resolution-based (lower CRF for higher res)
-   `cpu:quality` / `gpu:quality`: Lower CRF than balanced

**Adjustments:**

-   **HDR10/DV:** +1.0 CRF (10-bit encoding allows higher CRF without quality loss)
-   **Action Preset:** -2.0 CRF with weighted adjustment (better fast motion handling)
-   **Grain:** Variable adjustment based on grain category (cat1: -1, cat2: -2, cat3: -3)
-   **Weighting:** Adjustments weighted to avoid extreme values

**CRF Adjustment Weighting:**

```python
def _calculate_crf_adjustment_weight(current_crf, crf_delta):
    # Reduce adjustment impact when CRF is already low
    if crf_delta > 0:
        # Lowering CRF (improving quality)
        if current_crf <= 14:
            return 0.3  # Minimal adjustment at very high quality
        elif current_crf <= 18:
            return 0.7  # Moderate adjustment
        else:
            return 1.0  # Full adjustment at lower quality
    return 1.0
```

### Crop Detection Algorithm

**Process:**

-   Analyzes 10 evenly-distributed positions across video timeline
-   Uses ThreadPoolExecutor for parallel processing
-   Selects most common crop dimensions using Counter
-   Progress callback for real-time updates

**Crop Modes:**

-   `off` - No cropping (default)
-   `auto` - Automatic black bar detection
-   `width:height:x:y` - Manual crop (e.g., `1920:800:0:140`)
-   `16:9`, `21:9`, etc. - Aspect ratio-based cropping
-   `cinema` - CinemaScope 2.35:1
-   `cinema-modern` - CinemaScope 2.39:1

### HDR Metadata Extraction

-   Uses `ffprobe -show_frames -read_intervals %+#1` to extract first frame metadata
-   Parses mastering display and light level side data
-   Handles multiple metadata formats (JSON parsing)
-   Fallback to default values if metadata missing

### Progress Tracking

-   **FFmpeg:** Parses progress callback from python-ffmpeg library
-   **Real-time ETA:** Calculation based on FPS and remaining frames
-   **Multi-line display:** ANSI escape codes for line clearing
-   **Subprocess monitoring:** Spinner animation for dovi_tool, hevc_hdr_editor, mkvmerge

### Resolution Scaling

**Scale Modes:**

-   **height:** Fixed target height, width calculated from aspect ratio (default)
-   **adaptive:** Scales to fit within target resolution without exceeding width or height

**Named Resolutions:**

-   `FUHD` - 4320p (7680x4320)
-   `UHD` - 2160p (3840x2160)
-   `WQHD` - 1440p (2560x1440)
-   `FHD` - 1080p (1920x1080)
-   `HD` - 720p (1280x720)
-   `SD` - 480p (640x480)

**Process:**

-   Preserves aspect ratio when scaling
-   Applies scaling AFTER cropping if both enabled
-   Recalculates pixel count for auto-CRF/preset after scaling
-   Only downscaling supported (no upscaling)

### Grain Analysis

**Purpose:** Detect film grain and optimize encoding settings

**Categories:**

-   `cat1` - Light grain (CRF adjustment: -1)
-   `cat2` - Medium grain (CRF adjustment: -2, tune=grain)
-   `cat3` - Strong grain (CRF adjustment: -3, tune=grain)

**Integration:**

-   Automatic detection: `--grain auto`
-   Manual override: `--grain cat1`, `cat2`, `cat3`
-   Affects CRF and tune parameters for libx265/libx264

### Dolby Vision Processing

**Multi-Stage Workflow:**

1. **Base Layer Extraction:** Removes RPU to get HDR10 base layer using `dovi_tool remove`
2. **Temporary MKV Creation:** Muxes base layer with audio/subs for FFmpeg processing
3. **Re-encoding:** Applies encoder, CRF/CQ, and quality settings to base layer via FFmpeg
4. **RPU Extraction:** Extracts RPU with profile-specific mode conversion
5. **Enhancement Layer (Profile 7 only):** Extracts and multiplexes EL for Profile 7 preservation
6. **RPU Injection:** Re-injects RPU into encoded base layer via `dovi_tool inject-rpu`
7. **Final Muxing:** Creates final MKV with video, audio, subtitles

**Profile Conversion:**

-   Profile 5 (IPTPQc2) → Profile 8.1 via mode 3
-   Profile 7 (MEL+EL) → Profile 7 (with EL) or Profile 8.1 via mode 2
-   Profile 8 → Profile 8.1 via mode 2

**Format Downgrade:**

-   DV → HDR10: Extracts and re-encodes base layer only (no RPU injection)
-   DV → SDR: Extracts base layer, applies tone mapping, removes HDR metadata

**Copy Mode (No Re-encoding):**

-   DV → HDR10: Extract base layer only
-   DV → DV: Extract base layer, convert RPU profile, inject RPU

**Temporary File Management:**

-   Creates `.hdr_forge_temp_{filename}/` directory in output location
-   Incremental deletion of intermediate files during workflow
-   Final cleanup removes entire temp directory

## External Dependencies

**Required:**

-   `ffmpeg` - Video decoding and encoding
-   `ffprobe` - Metadata extraction

**Optional:**

-   `dovi_tool` - Dolby Vision RPU/EL extraction, base layer extraction, RPU injection, layer multiplexing
-   `hevc_hdr_editor` - HDR metadata injection into HEVC bitstreams
-   `mkvmerge` - MKV container operations (usually part of MKVToolNix)

**Hardware (Optional):**

-   NVIDIA GPU with NVENC support - Hardware-accelerated HEVC/H.264 encoding

## Common Development Tasks

### Adding a New Video Codec

1. Create new codec class in `ffmpeg/video_codec/` inheriting from `VideoCodecBase`
2. Implement required methods: `get_ffmpeg_params()`, `get_custom_lib_parameters()`, `get_hdr_metadata_for_encoding()`
3. Define supported HDR/SDR formats in `HDR_SDR_SUPPORT`
4. Add codec to `encoder.py` in `_get_video_codec_lib_instance()`
5. Add enum value to `VideoEncoderLibrary` in `typedefs/encoder_typing.py`
6. Update CLI arguments in `cli/args/pars_args.py`

### Modifying Auto-CRF/Preset Logic

1. Edit `calc_hw_preset_settings()` in `ffmpeg/video_codec/service/presets.py`
2. Adjust resolution thresholds and CRF/preset mappings
3. Modify `_get_auto_crf()` and `_get_auto_preset()` in codec classes for codec-specific adjustments

### Adding New CLI Parameters

1. Add argument to appropriate subcommand in `cli/args/pars_args.py`
2. Parse argument in `cli/args/pars_encoder_settings.py`
3. Add to `EncoderSettings` dataclass in `typedefs/encoder_typing.py`
4. Update `main.py` to handle new parameter
5. Update README.md and CLAUDE.md documentation

### Adding New HDR Forge Preset

1. Add enum value to `HdrForgeEncodingPresets` in `typedefs/encoder_typing.py`
2. Add choice to `--preset` argument in `cli/args/pars_args.py`
3. Implement preset logic in `_get_auto_crf()` and `_get_auto_tune()` in codec classes
4. Update documentation

### Adding New Hardware Preset

1. Add preset calculation logic in `ffmpeg/video_codec/service/presets.py`
2. Create new preset class (e.g., `Hdr_Forge_X265_X264_Preset`)
3. Add choice to `--hw-preset` argument in `cli/args/pars_args.py`
4. Update codec classes to use new preset

### Debugging

**Enable Debug Mode:**

```bash
hdr_forge convert -i input.mkv -o output.mkv --debug
```

**Debug Output Includes:**

-   FFmpeg command construction
-   Encoder parameter selection
-   Format detection details
-   Filter chain composition
-   Tool execution commands (dovi_tool, hevc_hdr_editor, mkvmerge)

**Set Debug in Code:**

```python
from hdr_forge.core import config
config.debug_mode = True
```

## Testing Checklist

-   [ ] SDR video conversion (libx265, libx264)
-   [ ] HDR10 video conversion (libx265)
-   [ ] HDR10 to SDR conversion with tone mapping
-   [ ] Dolby Vision conversion (Profile 5, 7, 8)
-   [ ] Dolby Vision to HDR10 conversion
-   [ ] Dolby Vision to SDR conversion with tone mapping
-   [ ] Dolby Vision profile conversion (copy mode)
-   [ ] Dolby Vision Profile 7 with EL preservation
-   [ ] Hardware encoding (NVENC HEVC, NVENC H.264)
-   [ ] Batch folder processing
-   [ ] Crop detection (auto, manual, aspect ratio)
-   [ ] Resolution scaling (height mode, adaptive mode)
-   [ ] HDR Forge presets (film, action, animation)
-   [ ] Hardware presets (cpu:balanced, cpu:quality, gpu:balanced, gpu:quality)
-   [ ] Grain analysis and optimization
-   [ ] Video sampling for testing
-   [ ] Custom HDR metadata injection during encoding
-   [ ] HDR metadata injection without re-encoding
-   [ ] Encoder overrides (--encoder)
-   [ ] Encoder-specific parameters (--encoder-params)
-   [ ] Different input formats (.mkv, .mp4, .m2ts, .ts)
-   [ ] Progress tracking accuracy
-   [ ] Temporary file cleanup
-   [ ] MaxCLL/MaxFALL calculation

## Known Limitations

1. **Dolby Vision Cropping/Scaling:** DV videos cannot be cropped or scaled when preserving DV format (RPU metadata is frame-position dependent). Cropping/scaling only works when converting DV → HDR10/SDR.
2. **Dolby Vision Sampling:** Video sampling (`--sample`) not supported for Dolby Vision encoding
3. **NVENC HDR Metadata:** NVENC encoders have limited HDR metadata support:
   - Dolby Vision metadata injection not yet supported
   - HDR→SDR metadata removal not supported
4. **Upscaling Not Supported:** Scaling only supports downscaling (videos cannot be upscaled to larger resolutions)
5. **Crop Detection Speed:** Crop detection requires 10 ffmpeg invocations (can be slow for large files)
6. **Format Upgrades Not Possible:** Cannot upgrade from lower to higher format (e.g., SDR → HDR10, HDR10 → Dolby Vision)
7. **Profile 7 EL Auto-Detection:** Profile 7 with EL only preserved when using `--dv-profile auto`, force-converting to Profile 8.1 will discard EL
8. **Temporary Disk Usage:** Dolby Vision conversion requires temporary storage (up to 2x source file size during processing)
9. **Hardware Acceleration:** Currently only NVIDIA NVENC is supported for GPU encoding (no Intel QSV, AMD VCE, or Apple VideoToolbox yet)
10. **Speed Preset with NVENC:** `--speed` parameter not compatible with NVENC encoders (use `--encoder-params` instead)

## Future Improvements

-   Complete NVENC HDR metadata support (Dolby Vision, HDR→SDR removal)
-   Additional hardware acceleration (Intel QSV, AMD VCE, Apple VideoToolbox)
-   Dolby Vision Profile 5 MEL-to-FEL conversion support
-   Audio transcoding options
-   Multi-pass encoding support
-   AV1 encoder support (libsvtav1, av1_nvenc)
-   VP9 encoder support (libvpx-vp9)
-   Custom LUT support for color grading
-   Automatic bitrate calculation mode
-   HDR10+ metadata preservation
