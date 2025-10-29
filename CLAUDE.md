# HDR Forge - Codebase Documentation for Claude Code

## Project Overview

HDR Forge (Easy HDR Video Converter) is a Python-based command-line tool for converting video files to H.265/HEVC format with intelligent HDR metadata preservation, automatic quality optimization, and black bar detection.

**Current Version:** Python v0.4.0 (Rust code has been removed)

## Technology Stack

-   **Language:** Python 3.7+
-   **Video Processing:** ffmpeg, ffprobe, x265 (for Dolby Vision)
-   **Key Dependencies:**
    -   `python-ffmpeg` - FFmpeg wrapper for Python
    -   `dovi_tool` - Dolby Vision RPU extraction (external binary)

## Project Structure

```
hdr_forge/
├── src/hdr_forge/
│   ├── __init__.py              # Package initialization with version info
│   ├── main.py                  # CLI entry point with argparse
│   ├── video.py                 # Video metadata extraction and analysis
│   ├── encoder.py               # Unified encoder for all formats (SDR/HDR10/DV)
│   ├── dataclass.py             # Data structures (HDR metadata, crop info)
│   ├── cli/
│   │   ├── cli_output.py        # Progress tracking and colored terminal output
│   │   ├── encoder.py           # Encoder CLI output helpers
│   │   └── video.py             # Video info CLI output
│   ├── hdr_formats/
│   │   ├── dolby_vision.py      # Dolby Vision BL/EL/RPU handling
│   │   └── hdr10.py             # HDR10 utilities (MaxCLL calculation)
│   └── container/
│       └── mkv.py               # MKV muxing and demuxing operations
├── README.md                    # User documentation
└── pyproject.toml               # Python project configuration
```

## Module Breakdown

### 1. main.py (CLI Entry Point)

**Lines:** 452 | **Key Function:** CLI argument parsing and command routing

**Subcommands:**

-   `info` - Display detailed video information
-   `convert` - Convert videos with format conversion support
-   `calc_maxcll` - Calculate MaxCLL and MaxFALL values (BETA)

**Key Functions:**

-   `parse_args()` - Parse CLI arguments with subcommands (info, convert, calc_maxcll)
-   `process_convert_command(args)` - Handle video conversion workflow
-   `process_info_command(args)` - Display video information
-   `convert_video(video, target_file, ...)` - Universal conversion function
-   `get_scale_height(scale)` - Parse scale argument to target height
-   `get_color_format_from_string(format_str)` - Convert string to ColorFormat enum
-   `get_dolby_vision_profile_from_string(profile_str)` - Convert string to DolbyVisionProfile enum
-   `get_video_files(path, supported_formats)` - Find video files in path/directory
-   `determine_output_file(video_file, output_path, is_batch)` - Calculate output path

**Features:**

-   Batch folder processing
-   Auto-detection of video format (SDR/HDR10/Dolby Vision)
-   Format conversion: Dolby Vision → HDR10 → SDR (downgrades only)
-   Resolution scaling support (--scale parameter, downscaling only)
-   Custom CRF and preset overrides
-   Automatic cropping (can be disabled with --ncrop, not supported for DV)
-   Dolby Vision profile selection (--dv-profile: auto, 8)

**Supported Formats:** `.mkv`, `.m2ts`, `.ts`, `.mp4`

### 2. video.py (Metadata Extraction)

**Lines:** 626 | **Key Class:** `Video`

**Core Responsibilities:**

-   Extract video metadata using ffprobe
-   Parse HDR metadata (master display, content light level)
-   Multi-threaded black bar detection (crop analysis)
-   Auto-calculate CRF and preset based on resolution
-   Video scaling calculations

**Key Methods:**

-   `__init__(filepath, crf, preset, scale_height, enable_crop, callback_handler_crop_video)` - Initialize video with metadata extraction
-   `extract_hdr_metadata()` - Extract HDR metadata using ffmpeg showinfo filter
-   `crop_video(num_threads, callback)` - Multi-threaded crop detection (10 samples)
-   `is_hdr_video()` - Detect HDR by checking for 10-bit pixel format
-   `is_dolby_vision_video()` - Check for Dolby Vision RPU flag
-   `get_master_display()` - Extract master display metadata
-   `get_max_cll_max_fall(return_fallback)` - Extract MaxCLL/MaxFALL values
-   `_get_auto_crf()` - Calculate optimal CRF based on pixel count
-   `_get_auto_preset()` - Select encoding preset based on resolution
-   `get_crop_filter()` - Generate ffmpeg crop filter string
-   `get_scale_filter()` - Generate ffmpeg scale filter string
-   `get_scale_dimensions()` - Calculate target dimensions considering crop and scale

**Auto-Scaling Logic:**

**CRF (Quality):**

-   4K (6.1M+ pixels): CRF 13
-   2K-4K (2.2M-6.1M pixels): CRF 14-18 (linear interpolation)
-   Full HD (2.1M pixels): CRF 18
-   Lower: CRF 19-20

**Preset (Speed):**

-   4K+ (8.8M+ pixels): superfast
-   2K-4K: faster
-   Full HD: fast
-   Lower: medium

### 3. encoder.py (Unified Video Encoder)

**Lines:** 773 | **Key Class:** `Encoder`

**Purpose:** Unified encoding system for all video formats (SDR, HDR10, Dolby Vision)

**Key Methods:**

-   `__init__(video, target_file, color_format, dv_profile, ...)` - Initialize encoder with format detection
-   `_determine_effective_format(color_format)` - Determine effective format (only downgrades allowed)
-   `_determine_dv_profile(dv_profile)` - Select Dolby Vision profile for encoding
-   `get_encoding_dolby_vision_profile()` - Get DV profile number for encoding
-   `_crop_video(num_threads, callback)` - Multi-threaded black bar detection
-   `_get_auto_crf()` - Calculate optimal CRF based on resolution
-   `_get_auto_preset()` - Select encoding preset based on resolution
-   `build_ffmpeg_output_options()` - Build complete FFmpeg option dictionary
-   `_build_hdr_x265_params()` - Generate x265 parameters for HDR10 encoding
-   `_build_sdr_x265_params()` - Generate x265 parameters for SDR encoding
-   `convert_sdr_hdr10(progress_callback, finish_callback)` - Execute SDR/HDR10 conversion
-   `convert_dolby_vision(progress_callback, finish_callback)` - Execute Dolby Vision conversion
-   `convert(progress_callback, finish_callback)` - Universal conversion method

**HDR x265 Parameters:**

```python
HDR_X265_PARAMS = [
    'hdr-opt=1',
    'repeat-headers=1',
    'colorprim=bt2020',
    'transfer=smpte2084',
    'colormatrix=bt2020nc',
]
```

**SDR x265 Parameters:**

```python
SDR_X265_PARAMS = [
    'colorprim=bt709',
    'transfer=bt709',
    'colormatrix=bt709',
    'no-hdr10-opt=1',
]
```

**Format Conversion Rules:**

-   AUTO: Keep source format
-   Only downgrades allowed: Dolby Vision → HDR10 → SDR
-   Upgrades blocked with warning (e.g., cannot SDR → HDR10)
-   HDR to SDR includes tone mapping using zscale + Hable algorithm

### 4. hdr_formats/dolby_vision.py (Dolby Vision Handling)

**Lines:** 498 | **Purpose:** Complete Dolby Vision metadata and layer handling

**Supported Profiles:**

-   Profile 5 (IPTPQc2, BL+RPU) → Converts to Profile 8.1
-   Profile 7 (MEL, BL+EL+RPU) → Converts to Profile 7 or 8.1
-   Profile 8 (BL+RPU) → Keeps Profile 8.1

**Key Functions:**

-   `get_dovi_tool_path()` - Locate dovi_tool binary (project root or system PATH)
-   `extract_base_layer(input_file, output_hevc)` - Extract HDR10 base layer (HEVC without RPU)
-   `extract_rpu(video, output_rpu, dv_profile_encoding)` - Extract RPU with profile-specific mode
-   `inject_rpu(input_file, input_rpu, output_hevc)` - Inject RPU metadata into HEVC
-   `extract_enhancement_layer(input_file, output_el)` - Extract EL for Profile 7
-   `inject_dolby_vision_layers(bl_path, el_path, output_bl_el)` - Multiplex BL and EL

**RPU Extraction Pipeline:**

```bash
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - |
dovi_tool [-m MODE] extract-rpu - -o output.rpu
```

**Mode Selection for Profile 8 Conversion:**

-   Profile 5 → Mode 3 (IPTPQc2 to MEL)
-   Profile 7 → Mode 2 (MEL to MEL)
-   Profile 8 → Mode 2 (default)

**Base Layer Extraction:**

```bash
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - |
dovi_tool remove - -o output_BL.hevc
```

**Tool Location Priority:**

1. Local `dovi_tool` in project root
2. System `dovi_tool` in PATH

### 5. dataclass.py (Data Structures)

**Lines:** 57 | **Type Definitions**

**Classes:**

-   `DolbyVisionInfo` - Dolby Vision profile, level, RPU flag
-   `MasterDisplayMetadata` - HDR10 mastering display color primaries and luminance
-   `ContentLightLevelMetadata` - MaxCLL and MaxFALL values
-   `HdrMetadata` - Container for mastering display and light level metadata
-   `CropHandler` - Progress tracking for crop detection

**Enums:**

-   `ColorFormat` - Target color format (AUTO, SDR, HDR10, DOLBY_VISION)
-   `DolbyVisionProfile` - Dolby Vision profile selection (AUTO, 8)

### 6. cli/cli_output.py (Terminal Output)

**Purpose:** Progress tracking and colored terminal output

**Features:**

-   Real-time progress bars with ETA calculation
-   ANSI color codes for terminal output (BLUE, GREEN, ANSI_YELLOW, RED)
-   FFmpeg progress parsing (frame, fps, speed, bitrate)
-   Multi-line progress display with line clearing
-   Progress monitoring for subprocess operations (dovi_tool)

**Key Functions:**

-   `create_progress_handler(duration, total_frames)` - Create FFmpeg progress callback
-   `finish_progress(total_frames, duration)` - Display final progress statistics
-   `monitor_process_progress(process, prefix)` - Monitor subprocess with spinner
-   `print_conversion_summary(success_count, fail_count)` - Final conversion summary

### 7. cli/encoder.py (Encoder CLI Helpers)

**Purpose:** Display encoding parameters and crop detection progress

**Key Functions:**

-   `print_encoding_params(encoder)` - Display encoding configuration
-   `callback_handler_crop_video(crop_handler)` - Crop detection progress callback

### 8. cli/video.py (Video Info Display)

**Purpose:** Display video metadata in formatted output

**Key Functions:**

-   `print_video_infos(video)` - Display comprehensive video metadata

### 9. hdr_formats/hdr10.py (HDR10 Utilities)

**Purpose:** HDR10-specific utilities and MaxCLL/MaxFALL calculation

**Key Functions:**

-   `calc_maxcll(video_path)` - Calculate MaxCLL and MaxFALL from video content (BETA)

### 10. container/mkv.py (MKV Operations)

**Purpose:** MKV container muxing and demuxing

**Key Functions:**

-   `mux_hevc_to_mkv(input_hevc, input_mkv, output_mkv)` - Mux HEVC video with audio/subs from MKV
-   `extract_hevc(input_mkv, output_hevc)` - Extract HEVC video stream from MKV

## Conversion Workflows

### SDR/HDR10 Conversion (using ffmpeg + libx265)

1. Create `Encoder` instance with video and target format
2. Detect effective format (source format or valid downgrade)
3. Run crop detection if enabled (multi-threaded, 10 samples)
4. Calculate auto-CRF and auto-preset if not specified
5. Build FFmpeg options with `build_ffmpeg_output_options()`
6. Execute FFmpeg with progress tracking
7. Copy audio and subtitle streams

**Format-Specific Processing:**

-   **HDR10:** Preserve HDR metadata (master display, MaxCLL/MaxFALL)
-   **SDR from HDR:** Apply tone mapping (zscale + Hable algorithm), remove HDR metadata
-   **SDR from SDR:** Standard re-encoding with BT.709 color space

### Dolby Vision Conversion

**Complete workflow with base layer re-encoding and RPU injection:**

1. **Extract HDR10 Base Layer:**

    - Extract HEVC bitstream from source video
    - Use `dovi_tool remove` to strip RPU metadata
    - Result: HDR10-only base layer (BL)

2. **Prepare Base Layer for Encoding:**

    - Mux BL HEVC with original audio/subtitles into temporary MKV
    - Delete intermediate HEVC file

3. **Re-encode Base Layer:**

    - Apply FFmpeg encoding with CRF, filters (if HDR10/SDR target)
    - For DV → HDR10/SDR: Write directly to target file and stop here
    - For DV → DV: Continue with RPU injection

4. **Extract Encoded HEVC:**

    - Demux encoded video stream from MKV container
    - Delete intermediate MKV file

5. **Extract and Prepare RPU Metadata:**

    - Extract RPU with profile-specific mode (`dovi_tool extract-rpu -m MODE`)
    - For Profile 7 with AUTO: Extract Enhancement Layer (EL) and multiplex with BL

6. **Inject RPU into Encoded Video:**

    - Use `dovi_tool inject-rpu` to add RPU metadata to encoded HEVC
    - Delete intermediate files (HEVC without RPU, RPU file)

7. **Final Muxing:**
    - Mux HEVC (with RPU) + audio/subtitles into target MKV
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

-   Dolby Vision does NOT support cropping (use `--ncrop`)
-   Dolby Vision does NOT support scaling (RPU metadata is frame-position dependent)
-   Scaling/cropping only applied when converting DV → HDR10/SDR

## CLI Usage Examples

```bash
# Show video info
hdr_forge info -i input.mkv

# Convert video with auto settings (keeps source format)
hdr_forge convert -i input.mkv -o output.mkv

# Convert with custom quality
hdr_forge convert -i input.mkv -o output.mkv --crf 16 --preset slow

# Batch convert folder
hdr_forge convert -i ./input_folder -o ./output_folder

# Scale video to 1080p (downscaling only, not compatible with DV)
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD

# Disable automatic cropping
hdr_forge convert -i input.mkv -o output.mkv --ncrop

# Convert Dolby Vision to HDR10 (auto-detected, extracts base layer)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --color-format hdr10

# Convert Dolby Vision to SDR with tone mapping
hdr_forge convert -i dolby_vision.mkv -o output.mkv --color-format sdr

# Convert HDR10 to SDR with tone mapping
hdr_forge convert -i hdr10_video.mkv -o output.mkv --color-format sdr

# Preserve Dolby Vision with re-encoding (must disable crop)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --ncrop

# Force Dolby Vision Profile 8.1 output (from Profile 5/7/8)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --dv-profile 8 --ncrop

# Calculate MaxCLL and MaxFALL (BETA feature)
hdr_forge calc_maxcll -i input.mkv
```

## Key Technical Details

### Crop Detection Algorithm

-   Analyzes 10 evenly-distributed positions across video timeline
-   Uses ThreadPoolExecutor for parallel processing
-   Selects most common crop dimensions using Counter
-   Progress callback for real-time updates

### HDR Metadata Extraction

-   Uses `ffmpeg -vf showinfo` to extract side data
-   Regex parsing for mastering display and light level metadata
-   Handles multiple metadata formats (showinfo vs side_data)
-   Fallback to default values if metadata missing

### Progress Tracking

-   FFmpeg: Parses JSON-like progress output via python-ffmpeg library
-   x265: Parses stderr with regex (format: "160 frames: 20.64 fps, 483.46 kb/s")
-   Real-time ETA calculation based on FPS and remaining frames
-   Multi-line display with ANSI escape codes for line clearing

### Resolution Scaling

-   Preserves aspect ratio when scaling
-   Applies scaling AFTER cropping if both are enabled
-   Supports named resolutions (UHD, FHD, HD, SD) or numeric height
-   Recalculates pixel count for auto-CRF/preset after scaling

### Dolby Vision Processing

**Multi-Stage Workflow:**

1. **Base Layer Extraction:** Removes RPU to get HDR10 base layer using `dovi_tool remove`
2. **Temporary MKV Creation:** Muxes base layer with audio/subs for FFmpeg processing
3. **Re-encoding:** Applies CRF and quality settings to base layer via FFmpeg
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

**Temporary File Management:**

-   Creates `.hdr_forge_temp_{filename}/` directory in output location
-   Incremental deletion of intermediate files during workflow
-   Final cleanup removes entire temp directory

## External Dependencies

**Required:**

-   `ffmpeg` - Video decoding and HDR10/SDR encoding
-   `ffprobe` - Metadata extraction

**Optional (Dolby Vision only):**

-   `dovi_tool` - RPU/EL extraction, base layer extraction, RPU injection, layer multiplexing

## Common Development Tasks

### Adding a New Video Format

1. Add extension to `SUPPORTED_FORMATS` list in `main.py:22`
2. Test with `get_video_files()` function

### Modifying Auto-CRF/Preset Logic

1. Edit `_get_auto_crf()` and `_get_auto_preset()` in `encoder.py`
2. Adjust pixel count thresholds and return values

### Adding New CLI Parameters

1. Add argument to `parse_args()` in `main.py`
2. Pass parameter to `Encoder()` constructor
3. Update README.md documentation

### Adding New Color Format Conversion

1. Add new format to `ColorFormat` enum in `dataclass.py`
2. Update `_determine_effective_format()` in `encoder.py`
3. Add format-specific x265 parameters in encoder
4. Update format hierarchy for upgrade/downgrade validation

### Debugging Progress Output

1. Set `DEBUG_MODE = True` in `cli_output.py:30`
2. Enables verbose info messages from x265

## Testing Checklist

-   [ ] SDR video conversion
-   [ ] HDR10 video conversion
-   [ ] HDR10 to SDR conversion with tone mapping
-   [ ] Dolby Vision conversion (Profile 5, 7, 8)
-   [ ] Dolby Vision to HDR10 conversion
-   [ ] Dolby Vision to SDR conversion with tone mapping
-   [ ] Dolby Vision Profile 7 with EL preservation
-   [ ] Batch folder processing
-   [ ] Crop detection (various aspect ratios)
-   [ ] Custom CRF/preset overrides
-   [ ] Resolution scaling (downscaling only)
-   [ ] Different input formats (.mkv, .mp4, .m2ts, .ts)
-   [ ] Progress tracking accuracy
-   [ ] Temporary file cleanup

## Known Limitations

1. **Dolby Vision Cropping/Scaling:** DV videos cannot be cropped or scaled when preserving DV format (RPU metadata is frame-position dependent). Cropping/scaling only works when converting DV → HDR10/SDR.
2. **Upscaling Not Supported:** Scaling only supports downscaling (videos cannot be upscaled to larger resolutions)
3. **Crop Detection Speed:** Crop detection requires 10 ffmpeg invocations (can be slow for large files)
4. **HDR Metadata Extraction:** Uses ffmpeg showinfo filter (processes multiple frames)
5. **Format Upgrades Not Possible:** Cannot upgrade from lower to higher format (e.g., SDR → HDR10, HDR10 → Dolby Vision)
6. **Profile 7 EL Auto-Detection:** Profile 7 with EL only preserved when using `--dv-profile auto`, force-converting to Profile 8.1 will discard EL
7. **Temporary Disk Usage:** Dolby Vision conversion requires temporary storage (up to 2x source file size during processing)

## Future Improvements

-   GPU-accelerated encoding support (NVENC, QSV)
-   Dolby Vision Profile 5 MEL-to-FEL conversion support
-   Audio transcoding options
