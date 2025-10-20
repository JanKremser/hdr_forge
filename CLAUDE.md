# EHDR - Codebase Documentation for Claude Code

## Project Overview

EHDR (Easy HDR Video Converter) is a Python-based command-line tool for converting video files to H.265/HEVC format with intelligent HDR metadata preservation, automatic quality optimization, and black bar detection.

**Current Version:** Python v0.4.0 (Rust code has been removed)

## Technology Stack

- **Language:** Python 3.7+
- **Video Processing:** ffmpeg, ffprobe, x265 (for Dolby Vision)
- **Key Dependencies:**
  - `python-ffmpeg` - FFmpeg wrapper for Python
  - `dovi_tool` - Dolby Vision RPU extraction (external binary)

## Project Structure

```
ehdr/
├── src/ehdr/
│   ├── __init__.py           # Package initialization with version info
│   ├── main.py               # CLI entry point with argparse
│   ├── video.py              # Video metadata extraction and analysis
│   ├── encoding.py           # FFmpeg parameter building
│   ├── dolby_vision.py       # Dolby Vision RPU extraction
│   ├── dataclass.py          # Data structures (HDR metadata, crop info)
│   └── cli_output.py         # Progress tracking and colored terminal output
├── README.md                 # User documentation
└── pyproject.toml            # Python project configuration
```

## Module Breakdown

### 1. main.py (CLI Entry Point)
**Lines:** 447 | **Key Function:** CLI argument parsing and command routing

**Subcommands:**
- `info` - Display detailed video information
- `convert` - Convert videos with HDR/SDR support

**Key Functions:**
- `parse_args()` - Parse CLI arguments with subcommands (info, convert)
- `process_convert_command(args)` - Handle video conversion workflow
- `process_info_command(args)` - Display video information
- `convert_sdr_hdr10(video, output_file)` - Convert using ffmpeg with libx265
- `convert_dolby_vision(video, output_file)` - Convert using x265 with RPU injection
- `get_scale_height(scale)` - Parse scale argument to target height

**Features:**
- Batch folder processing
- Auto-detection of video format (SDR/HDR10/Dolby Vision)
- Resolution scaling support (--scale parameter, downscaling only, not compatible with Dolby Vision)
- Custom CRF and preset overrides
- Automatic cropping (can be disabled with --ncrop)

**Supported Formats:** `.mkv`, `.m2ts`, `.ts`, `.mp4`

### 2. video.py (Metadata Extraction)
**Lines:** 626 | **Key Class:** `Video`

**Core Responsibilities:**
- Extract video metadata using ffprobe
- Parse HDR metadata (master display, content light level)
- Multi-threaded black bar detection (crop analysis)
- Auto-calculate CRF and preset based on resolution
- Video scaling calculations

**Key Methods:**
- `__init__(filepath, crf, preset, scale_height, enable_crop, callback_handler_crop_video)` - Initialize video with metadata extraction
- `extract_hdr_metadata()` - Extract HDR metadata using ffmpeg showinfo filter
- `crop_video(num_threads, callback)` - Multi-threaded crop detection (10 samples)
- `is_hdr_video()` - Detect HDR by checking for 10-bit pixel format
- `is_dolby_vision_video()` - Check for Dolby Vision RPU flag
- `get_master_display()` - Extract master display metadata
- `get_max_cll_max_fall(return_fallback)` - Extract MaxCLL/MaxFALL values
- `_get_auto_crf()` - Calculate optimal CRF based on pixel count
- `_get_auto_preset()` - Select encoding preset based on resolution
- `get_crop_filter()` - Generate ffmpeg crop filter string
- `get_scale_filter()` - Generate ffmpeg scale filter string
- `get_scale_dimensions()` - Calculate target dimensions considering crop and scale

**Auto-Scaling Logic:**

**CRF (Quality):**
- 4K (6.1M+ pixels): CRF 13
- 2K-4K (2.2M-6.1M pixels): CRF 14-18 (linear interpolation)
- Full HD (2.1M pixels): CRF 18
- Lower: CRF 19-20

**Preset (Speed):**
- 4K+ (8.8M+ pixels): superfast
- 2K-4K: faster
- Full HD: fast
- Lower: medium

### 3. encoding.py (FFmpeg Configuration)
**Lines:** 117 | **Key Function:** FFmpeg parameter building

**Key Functions:**
- `build_ffmpeg_output_options(video)` - Build complete FFmpeg option dictionary
- `build_hdr_x265_params(video)` - Generate x265 parameters for HDR encoding
- `get_video_files(path, supported_formats)` - Find video files in path/directory
- `determine_output_file(video_file, output_path, is_batch)` - Calculate output path

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

### 4. dolby_vision.py (Dolby Vision Handling)
**Lines:** 139 | **Key Function:** `extract_rpu()`

**Workflow:**
1. Check for cached RPU file (avoids re-extraction)
2. Extract HEVC bitstream using ffmpeg
3. Pipe to `dovi_tool` for RPU extraction
4. Return path to extracted `.rpu` file

**Pipeline:**
```bash
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - |
dovi_tool extract-rpu - -o output.rpu
```

**Tool Location Priority:**
1. Local `dovi_tool` in project root
2. System `dovi_tool` in PATH

### 5. dataclass.py (Data Structures)
**Lines:** 43 | **Type Definitions**

**Classes:**
- `DolbyVisionInfo` - Dolby Vision profile, level, RPU flag
- `MasterDisplayMetadata` - HDR10 mastering display color primaries and luminance
- `ContentLightLevelMetadata` - MaxCLL and MaxFALL values
- `HdrMetadata` - Container for mastering display and light level metadata
- `CropHandler` - Progress tracking for crop detection

### 6. cli_output.py (Terminal Output)
**Lines:** 352 | **Key Functions:** Progress tracking and colored output

**Features:**
- Real-time progress bars with ETA calculation
- ANSI color codes for terminal output (BLUE, GREEN, YELLOW, RED)
- FFmpeg progress parsing (frame, fps, speed, bitrate)
- x265 progress parsing (different format than ffmpeg)
- Multi-line progress display with line clearing
- Crop detection progress callback

**Key Functions:**
- `create_progress_handler(duration, total_frames)` - Create FFmpeg progress callback
- `monitor_x265_progress(stderr, total_frames)` - Monitor x265 encoding
- `print_video_infos(video)` - Display video metadata
- `print_encoding_params(video)` - Display encoding configuration
- `print_conversion_summary(success_count, fail_count)` - Final summary
- `callback_handler_crop_video(crop_handler)` - Crop progress display

## Conversion Workflows

### SDR/HDR10 Conversion (using ffmpeg + libx265)
1. Load video metadata with `Video(filepath, ...)`
2. Run crop detection if enabled (multi-threaded, 10 samples)
3. Calculate auto-CRF and auto-preset if not specified
4. Build FFmpeg options with `build_ffmpeg_output_options()`
5. Execute FFmpeg with progress tracking
6. Copy audio and subtitle streams

### Dolby Vision Conversion (using x265 CLI)
1. Extract RPU metadata with `extract_rpu()` (cached if exists)
2. Load video metadata
3. Build x265 command with HDR parameters
4. Create pipeline: `ffmpeg (yuv4mpegpipe) | x265 (with --dolby-vision-rpu)`
5. Monitor x265 progress in real-time
6. Mux audio/subtitles separately (not shown in current code)

**Note:** Dolby Vision does NOT support cropping or scaling (RPU metadata is position-dependent)

## CLI Usage Examples

```bash
# Show video info
ehdr info -i input.mkv

# Convert HDR10/SDR video with auto settings
ehdr convert -i input.mkv -o output.mkv

# Convert with custom quality
ehdr convert -i input.mkv -o output.mkv --crf 16 --preset slow

# Batch convert folder
ehdr convert -i ./input_folder -o ./output_folder

# Scale video to 1080p (downscaling only)
ehdr convert -i 4k_video.mkv -o output.mkv --scale FHD

# Disable automatic cropping
ehdr convert -i input.mkv -o output.mkv --ncrop

# Dolby Vision (auto-detected based on RPU flag)
ehdr convert -i dolby_vision.mkv -o output.mkv --ncrop
```

## Key Technical Details

### Crop Detection Algorithm
- Analyzes 10 evenly-distributed positions across video timeline
- Uses ThreadPoolExecutor for parallel processing
- Selects most common crop dimensions using Counter
- Progress callback for real-time updates

### HDR Metadata Extraction
- Uses `ffmpeg -vf showinfo` to extract side data
- Regex parsing for mastering display and light level metadata
- Handles multiple metadata formats (showinfo vs side_data)
- Fallback to default values if metadata missing

### Progress Tracking
- FFmpeg: Parses JSON-like progress output via python-ffmpeg library
- x265: Parses stderr with regex (format: "160 frames: 20.64 fps, 483.46 kb/s")
- Real-time ETA calculation based on FPS and remaining frames
- Multi-line display with ANSI escape codes for line clearing

### Resolution Scaling
- Preserves aspect ratio when scaling
- Applies scaling AFTER cropping if both are enabled
- Supports named resolutions (UHD, FHD, HD, SD) or numeric height
- Recalculates pixel count for auto-CRF/preset after scaling

## External Dependencies

**Required:**
- `ffmpeg` - Video decoding and HDR10/SDR encoding
- `ffprobe` - Metadata extraction

**Optional (Dolby Vision only):**
- `x265` (10-bit build) - Direct encoding with RPU injection
- `dovi_tool` - RPU metadata extraction from HEVC streams

## Common Development Tasks

### Adding a New Video Format
1. Add extension to `SUPPORTED_FORMATS` list in `main.py:22`
2. Test with `get_video_files()` function

### Modifying Auto-CRF/Preset Logic
1. Edit `_get_auto_crf()` and `_get_auto_preset()` in `video.py`
2. Adjust pixel count thresholds and return values

### Adding New CLI Parameters
1. Add argument to `parse_args()` in `main.py`
2. Pass parameter to `Video()` constructor or conversion functions
3. Update README.md documentation

### Debugging Progress Output
1. Set `DEBUG_MODE = True` in `cli_output.py:30`
2. Enables verbose info messages from x265

## Testing Checklist

- [ ] SDR video conversion
- [ ] HDR10 video conversion
- [ ] Dolby Vision conversion
- [ ] Batch folder processing
- [ ] Crop detection (various aspect ratios)
- [ ] Custom CRF/preset overrides
- [ ] Resolution scaling (downscaling only)
- [ ] Different input formats (.mkv, .mp4, .m2ts, .ts)
- [ ] Progress tracking accuracy

## Known Limitations

1. Dolby Vision videos cannot be cropped or scaled (RPU metadata is frame-position dependent)
2. Scaling only supports downscaling (videos cannot be upscaled to larger resolutions)
3. x265 Dolby Vision encoding outputs raw .hevc file (requires manual muxing)
4. Crop detection requires 10 ffmpeg invocations (can be slow for large files)
5. HDR metadata extraction uses ffmpeg showinfo (processes 10 frames)
6. Scaling uses simple aspect ratio calculation (no advanced algorithms)

## Future Improvements

- Automatic Dolby Vision muxing after x265 encoding
- GPU-accelerated encoding support (NVENC, QSV)
- Advanced crop detection with scene change detection
- JSON output mode for programmatic usage
- Configuration file support (.ehdrrc)
