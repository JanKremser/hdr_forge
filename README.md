# EHDR - Easy HDR Video Converter

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line tool for converting video files to H.265/HEVC format with intelligent HDR metadata preservation, automatic quality optimization, and black bar detection.

## Features

-   **Multiple Format Support:** Convert between Dolby Vision, HDR10, and SDR formats
-   **Format Conversion:** DV → HDR10 → SDR with tone mapping support
-   **Dolby Vision Profiles:** Support for Profile 5, 7 (with EL), and 8
-   **Automatic Black Bar Detection:** Multi-threaded crop analysis (can be disabled)
-   **Resolution Scaling:** Scale videos to target resolutions (UHD, FHD, HD, etc.)
-   **Intelligent Quality Control:** Resolution-based auto-scaling for CRF and preset
-   **Batch Processing:** Convert entire folders with one command
-   **HDR Metadata Preservation:** Maintains master display and content light level metadata
-   **Dolby Vision Re-encoding:** Base layer re-encoding with RPU injection
-   **Stream Copying:** Preserves all audio and subtitle tracks
-   **Real-time Progress:** Live encoding progress with ETA and statistics

All videos are converted to H.265 (HEVC) with compression settings dynamically adjusted based on resolution. Settings can be customized using `--crf` and `--preset` parameters. See the [ffmpeg H.265 documentation](https://trac.ffmpeg.org/wiki/Encode/H.265) for details.

## Version History

**Current: v0.4.0** (Complete rewrite in Python)

-   Previous Rust version removed from main branch

## Installation

### Requirements

-   **Python 3.7 or higher**
-   **[ffmpeg / ffprobe](https://ffmpeg.org/download.html)** with libx265 support
-   **[x265 >=4.1](https://github.com/videolan/x265)** for libx265
    -   [Windows builds](http://msystem.waw.pl/x265/)
    -   **Linux:** Available in the repositories

**Only for Dolby Vision:**

-   **[dovi_tool](https://github.com/quietvoid/dovi_tool)** - For RPU/EL extraction and injection
    -   **for Arch Linux:** Available in the repositories
    -   **for the others:** Download from releases and place in PATH or project root

### Install EHDR

```bash
# Install from source
git clone https://github.com/yourusername/ehdr.git
cd ehdr
pip install -e .

# Or install directly with pip (when published to PyPI)
pip install ehdr
```

### Verify Installation

```bash
ehdr --version
ffmpeg -version
ffprobe -version
x265 --version

# For Dolby Vision support
dovi_tool --help
```

## Usage

### Video Information

Display detailed video metadata without conversion:

```bash
ehdr info -i video.mkv
```

Shows resolution, frame rate, color information, HDR metadata, and Dolby Vision details if present.

### Basic Conversion

Convert a single video file. Black bars are automatically detected and cropped by default:

```bash
ehdr convert -i input.mkv -o output.mkv
```

To disable automatic cropping:

```bash
ehdr convert -i input.mkv -o output.mkv --ncrop
```

### Dolby Vision

Dolby Vision videos are automatically detected based on RPU metadata flags.

**Supported Profiles:**
- Profile 5 (IPTPQc2, BL+RPU) → Preserves Profile 5 or converts to Profile 8.1
- Profile 7 (MEL, BL+EL+RPU) → Preserves Profile 7 or converts to Profile 8.1
- Profile 8 (BL+RPU) → Keeps Profile 8.1

**Preserve Dolby Vision (re-encode with DV):**
```bash
# Must disable cropping when preserving DV
ehdr convert -i dolby_vision.mkv -o output.mkv --ncrop

# Force conversion to Profile 8.1
ehdr convert -i dolby_vision.mkv -o output.mkv --dv-profile 8 --ncrop
```

**Convert to HDR10 (extract base layer only):**
```bash
# Cropping and scaling supported when converting to HDR10
ehdr convert -i dolby_vision.mkv -o output.mkv --color-format hdr10
ehdr convert -i dolby_vision.mkv -o output.mkv --color-format hdr10 --scale FHD
```

**Convert to SDR (with tone mapping):**
```bash
# Converts DV → HDR10 base layer → SDR with tone mapping
ehdr convert -i dolby_vision.mkv -o output.mkv --color-format sdr
```

**Important Notes:**
- Dolby Vision does NOT support cropping or scaling when preserving DV format (use `--ncrop` and avoid `--scale`)
- Cropping and scaling ARE supported when converting DV → HDR10 or DV → SDR
- Profile 7 with Enhancement Layer is preserved only with `--dv-profile auto` (default)

### Format Conversion

Convert between different HDR/SDR formats. Only downgrades are supported (DV → HDR10 → SDR):

```bash
# Convert HDR10 to SDR with tone mapping
ehdr convert -i hdr10_video.mkv -o output.mkv --color-format sdr

# Convert Dolby Vision to HDR10 (extracts base layer)
ehdr convert -i dolby_vision.mkv -o output.mkv --color-format hdr10

# Keep source format (default behavior)
ehdr convert -i input.mkv -o output.mkv --color-format auto
```

**Tone Mapping:**
- HDR to SDR conversion uses zscale filter with Hable tone mapping algorithm
- Automatically removes HDR metadata for SDR output
- Adjusts color space to BT.709 for SDR

### Batch Processing

Convert all supported video files in a folder:

```bash
ehdr convert -i ./input_folder -o ./output_folder
```

Output files maintain original names with `.mkv` extension.

### Custom Quality Settings

Override automatic quality settings:

```bash
# Higher quality (lower CRF = better quality, larger file size)
ehdr convert -i input.mkv -o output.mkv --crf 12 --preset slow

# Faster encoding (faster preset = quicker encoding)
ehdr convert -i input.mkv -o output.mkv --preset faster

# Combine both
ehdr convert -i input.mkv -o output.mkv --crf 14 --preset medium
```

### Resolution Scaling

Scale videos to specific resolutions:

```bash
# Using named resolutions
ehdr convert -i 4k_video.mkv -o output.mkv --scale FHD    # 1920x1080
ehdr convert -i 2k_video.mkv -o output.mkv --scale HD     # 1280x720

# Using numeric height (width calculated automatically)
ehdr convert -i 4k_video.mkv -o output.mkv --scale 1080
ehdr convert -i input.mkv -o output.mkv --scale 720
```

**Available Named Resolutions:**

-   `UHD` - 2160p (3840x2160)
-   `QHD` - 1440p (2560x1440)
-   `FHD` - 1080p (1920x1080)
-   `HD` - 720p (1280x720)
-   `SD` - 480p (640x480)

**Important Limitations:**

-   **Only downscaling is supported** - Videos can only be scaled to smaller resolutions than the original
-   **Not compatible with Dolby Vision** - Scaling modifies frame dimensions which breaks RPU metadata
-   Scaling preserves aspect ratio and is applied after cropping (if enabled)

### Supported Formats

**Input Formats:** `.mkv`, `.m2ts`, `.ts`, `.mp4`
**Output Format:** `.mkv` (H.265/HEVC video + original audio/subtitle streams)

## Command Reference

### Global Options

```
ehdr --version              Show program version
ehdr --help                 Show help message
```

### Info Subcommand

```
ehdr info -i INPUT          Display video metadata

Options:
  -i, --input INPUT         Input video file
```

### Convert Subcommand

```
ehdr convert -i INPUT -o OUTPUT [OPTIONS]

Required Arguments:
  -i, --input INPUT         Input video file or folder
  -o, --output OUTPUT       Output video file or folder

Optional Arguments:
  --crf CRF                 Constant Rate Factor (lower = higher quality)
                            Auto-calculated if not specified
  -p, --preset PRESET       Encoding preset: ultrafast, superfast, veryfast,
                            faster, fast, medium, slow, slower, veryslow
                            Auto-calculated if not specified
  --ncrop                   Disable automatic black bar cropping
  --scale RESOLUTION        Scale video to target resolution
                            (UHD, FHD, HD, SD, or numeric height)
  --color-format FORMAT     Target color format (auto, hdr10, sdr)
                            auto = keep source format (default)
                            hdr10 = convert to HDR10
                            sdr = convert to SDR with tone mapping
  --dv-profile PROFILE      Dolby Vision profile (auto, 8)
                            auto = automatic detection (default)
                            8 = force Profile 8.1 output
```

## Automatic Quality Optimization

EHDR automatically adjusts encoding parameters based on video resolution for optimal quality and encoding speed:

### CRF (Quality) - Lower = Better Quality

| Resolution Range | Pixel Count      | CRF Value      |
| ---------------- | ---------------- | -------------- |
| 4K+              | 6.1M+ pixels     | 13             |
| 2K-4K            | 2.2M-6.1M pixels | 14-18 (scaled) |
| Full HD          | ~2.1M pixels     | 18             |
| HD               | 1M-2.1M pixels   | 19             |
| Lower            | <1M pixels       | 20             |

### Preset (Speed) - Faster = Quicker Encoding

| Resolution Range | Pixel Count      | Preset    |
| ---------------- | ---------------- | --------- |
| 4K+              | 8.8M+ pixels     | superfast |
| 2K-4K            | 2.1M-8.8M pixels | faster    |
| Full HD          | ~2.1M pixels     | fast      |
| Lower            | <2.1M pixels     | medium    |

These defaults can be overridden with `--crf` and `--preset` parameters.

## Advanced Examples

```bash
# Convert 4K video to 1080p with high quality
ehdr convert -i 4k_movie.mkv -o 1080p_movie.mkv --scale FHD --crf 14

# Batch convert folder without cropping
ehdr convert -i ./videos -o ./encoded --ncrop

# Fast conversion with lower quality for previews
ehdr convert -i input.mkv -o preview.mkv --crf 22 --preset ultrafast

# High-quality conversion for archiving
ehdr convert -i input.mkv -o archive.mkv --crf 12 --preset veryslow

# Convert Dolby Vision library to HDR10 with scaling
ehdr convert -i ./dv_movies -o ./hdr10_movies --color-format hdr10 --scale FHD

# Create SDR copies from HDR10 content
ehdr convert -i ./hdr10_videos -o ./sdr_videos --color-format sdr

# Re-encode Dolby Vision with custom quality
ehdr convert -i dolby_vision.mkv -o output.mkv --ncrop --crf 14 --preset slow
```

## Technical Details

### Crop Detection

-   Analyzes 10 evenly-distributed samples across video timeline
-   Multi-threaded processing for speed
-   Selects most common crop dimensions for consistency

### HDR Metadata Extraction

-   Extracts mastering display metadata (color primaries, luminance)
-   Preserves content light level information (MaxCLL, MaxFALL)
-   Applies proper HDR x265 parameters automatically

### Dolby Vision Processing

**Multi-Stage Workflow:**
1. Extracts HDR10 base layer (strips RPU) using `dovi_tool remove`
2. Muxes base layer with audio/subtitles into temporary MKV
3. Re-encodes base layer with FFmpeg (applies CRF, filters)
4. Extracts RPU metadata with profile-specific conversion mode
5. For Profile 7: Extracts Enhancement Layer and multiplexes with base layer
6. Injects RPU back into encoded video using `dovi_tool inject-rpu`
7. Final muxing with all streams into target MKV

**Profile Handling:**
- Profile 5 (IPTPQc2) → Profile 5 preserved or converts to Profile 8.1 (mode 3 conversion)
- Profile 7 (MEL+EL) → Profile 7 preserved or Profile 8.1 (mode 2 conversion)
- Profile 8 → Profile 8.1 (mode 2 conversion)

**Format Downgrade:**
- DV → HDR10: Stops after step 3 (base layer only, no RPU)
- DV → SDR: Base layer with tone mapping applied

**Temporary Files:**
- Stored in `.ehdr_temp_{filename}/` directory
- Incrementally deleted during workflow
- Final cleanup removes entire temp directory

## Troubleshooting

### "Command not found: ffmpeg"

Install ffmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) and ensure it's in your PATH.

### "dovi_tool not found" (Dolby Vision only)

Install dovi_tool from [GitHub releases](https://github.com/quietvoid/dovi_tool/releases) or place the binary in the project root directory.

### Slow crop detection

Crop detection analyzes 10 video samples. For very large files, consider using `--ncrop` to skip this step.

### Black bars still visible after conversion

Some videos have irregular black bars that vary throughout the video. Crop detection uses the most common dimensions found. You can manually specify crop parameters in the source code if needed.

### "Cannot crop/scale Dolby Vision" warning

When preserving Dolby Vision format, cropping and scaling are not supported because RPU metadata is frame-position dependent. Options:
- Use `--ncrop` to disable cropping for DV preservation
- Convert to HDR10 or SDR to enable cropping/scaling: `--color-format hdr10`

### High disk usage during Dolby Vision conversion

Dolby Vision conversion creates temporary files that can use up to 2x the source file size. These are automatically cleaned up after conversion. Ensure sufficient disk space in the output directory.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Acknowledgments

-   [FFmpeg](https://ffmpeg.org/) - Video processing
-   [x265](https://www.videolan.org/developers/x265.html) - HEVC encoding
-   [dovi_tool](https://github.com/quietvoid/dovi_tool) - Dolby Vision metadata handling
