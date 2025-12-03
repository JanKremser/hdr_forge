# HDR Forge - SDR/HDR10/DolbyVision Video Converter

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line tool for converting video files with hardware-accelerated encoding (NVIDIA NVENC), intelligent HDR metadata preservation, automatic quality optimization, grain analysis, flexible cropping, and advanced format conversion (H.264, H.265/HEVC, AV1, Dolby Vision).

## Features

-   **Multiple Encoder Support:** CPU (libx265, libx264, libsvtav1) and GPU-accelerated encoding (NVIDIA NVENC)
-   **AV1 Encoding (Beta):** Next-generation codec with superior compression efficiency
-   **Hardware Acceleration:** NVIDIA NVENC support for H.265/HEVC and H.264 encoding
-   **Multiple Format Support:** Convert between Dolby Vision, HDR10, and SDR formats
-   **Format Conversion:** DV → HDR10 → SDR with tone mapping support
-   **Dolby Vision Profiles:** Support for Profile 5, 7 (with EL), and 8
-   **HDR Metadata Injection:** Add or update HDR10 metadata without re-encoding
-   **Advanced Cropping:** Automatic black bar detection, manual cropping, aspect ratio presets
-   **Flexible Scaling:** Height-based and adaptive scaling modes
-   **Grain Analysis:** Automatic grain detection with encoding optimization
-   **Content-Aware Presets:** Film, banding, video, action, and animation-optimized encoding profiles
-   **Logo Removal:** Automatic logo detection and removal with multiple algorithms (delogo, mask, inpaint)
-   **Hardware Presets:** CPU/GPU-specific encoding presets (balanced, quality)
-   **Video Sampling:** Test encoding settings on short video samples
-   **Intelligent Quality Control:** Resolution and content-based auto-optimization
-   **Batch Processing:** Convert entire folders with one command
-   **Real-time Progress:** Live encoding progress with ETA and statistics

All videos are converted with compression settings dynamically adjusted based on resolution, content type, and grain. Settings can be customized using various CLI parameters.

## Quick Start

```bash
# Show video information
hdr_forge info -i video.mkv

# Basic conversion (auto settings)
hdr_forge convert -i input.mkv -o output.mkv

# GPU-accelerated conversion (NVIDIA NVENC)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# High-quality CPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

# AV1 encoding (Beta - next-generation codec)
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1

# Convert Dolby Vision to HDR10
hdr_forge convert -i dv.mkv -o output.mkv --hdr-sdr-format hdr10

# Inject HDR metadata without re-encoding
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(1000,0.05)"
```

## Documentation

- **[Encoder Guide](documentation/encoders.md)** - Comprehensive encoder information (libx265, libx264, libsvtav1, NVENC)
- **[Advanced Examples](documentation/advanced-examples.md)** - Complex encoding workflows and examples
- **[Technical Details](documentation/technical-details.md)** - In-depth technical information
- **[Troubleshooting](documentation/troubleshooting.md)** - Solutions to common problems

## Version History

**Current: v0.7.11**

### New Features
-   **AV1 Encoding (Beta):** Full support for AV1 codec via libsvtav1 encoder
-   **Logo Removal:** Automatic logo detection and removal with three algorithms:
    -   `delogo` - FFmpeg delogo filter
    -   `mask` - Mask-based removal
    -   `inpaint` - Experimental inpainting (best quality)
-   **New Presets:**
    -   `banding` - Banding reduction preset (8-bit → 10-bit for SDR)
    -   `video` - Neutral preset for mixed content
-   **Enhanced Speed Control:**
    -   `medium:plus` - Improved quality over medium
    -   `slow:plus` - Better quality/speed tradeoff than slow
-   **New Scale Options:**
    -   `QHD+` (1800p) and `QHD` (540p) resolutions
-   **Display Aspect Ratio:** Custom DAR with `--dar-ratio` parameter
-   **Custom Filters:** Add FFmpeg video filters with `--vfilter`
-   **New Subcommands:**
    -   `detect-logo` - Analyze and detect logos in videos
    -   `extract-metadata` - Extract Dolby Vision/HDR10/HDR10+ metadata
    -   `inject-metadata` - Inject DV/HDR10/HDR10+ metadata without re-encoding

### Improvements
-   Master-display support for GPU encoded videos
-   Extended metadata injection capabilities (HDR10+, Dolby Vision EL)
-   Improved preset system with more granular control

**v0.6.0**

-   Master-display support for GPU encoded videos

**v0.4.0** (Complete rewrite in Python)

-   Previous Rust version removed from main branch
-   Hardware acceleration support (NVIDIA NVENC)
-   Multiple encoder support (libx265, libx264, HEVC NVENC, H.264 NVENC)
-   Advanced cropping modes (auto, manual, aspect ratio)
-   Flexible scaling modes (height-based, adaptive)
-   Grain analysis and optimization
-   HDR metadata injection without re-encoding
-   Content-aware encoding presets (film, action, animation)
-   Video sampling for testing
-   Enhanced CLI with comprehensive parameter support

## What's New in v0.7.11

### AV1 Support (Beta)

HDR Forge now supports AV1 encoding via libsvtav1 (SVT-AV1 encoder). AV1 is a next-generation video codec that offers:

-   **Superior Compression:** 20-40% smaller file sizes compared to HEVC at similar quality
-   **Royalty-Free:** Open-source codec with no licensing fees
-   **HDR Support:** Full HDR10 and SDR support with proper metadata preservation
-   **Future-Proof:** Growing platform support (YouTube, Netflix, modern browsers)

**Beta Status:** AV1 encoding is currently in beta. While the encoder is stable and produces excellent results, some advanced features may still be refined in future releases.

```bash
# Basic AV1 encoding
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1

# AV1 with quality control
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1 --quality 23

# AV1 HDR encoding
hdr_forge convert -i hdr_video.mkv -o output.mkv --encoder libsvtav1
```

**See [Encoder Guide - AV1](documentation/encoders.md#libsvtav1-av1) for detailed information.**

## Installation

### Requirements

#### Software Requirements (Mandatory)

-   **Python 3.7 or higher**
-   **[ffmpeg / ffprobe](https://ffmpeg.org/download.html)** with libx265, libx264, or libsvtav1 support
-   **[x265 >=4.1](https://github.com/videolan/x265)** for libx265
    -   [Windows builds](http://msystem.waw.pl/x265/)
    -   **Linux:** Available in the repositories
-   **[SVT-AV1](https://gitlab.com/AOMediaCodec/SVT-AV1)** for AV1 encoding (Beta)
    -   **Linux:** Available in most repositories as `svt-av1` or `libsvtav1`
    -   **Windows:** Included in recent FFmpeg builds

#### Hardware Acceleration (Optional)

-   **NVIDIA GPU** with NVENC support (GTX 1050 or newer)
    -   FFmpeg compiled with NVENC support
    -   Recent NVIDIA drivers (recommended: 470+ for Linux, 472+ for Windows)

**See [Encoder Guide](documentation/encoders.md) for detailed hardware requirements and setup.**

#### Optional Tools for Advanced Features

**For Dolby Vision:**

-   **[dovi_tool](https://github.com/quietvoid/dovi_tool)** - RPU/EL extraction and injection
    -   **for Arch Linux:** Available in the repositories
    -   **for others:** Download from releases and place in PATH or project root

**For HDR Metadata Injection:**

-   **[hevc_hdr_editor](https://github.com/quietvoid/hevc_hdr_editor)** - HDR metadata injection tool
    -   Download from releases and place in PATH or project root

**For Container Operations:**

-   **[mkvmerge](https://mkvtoolnix.download/)** (part of MKVToolNix) - MKV muxing/demuxing
    -   Usually available in system repositories

**For MaxCLL Calculation:**

-   **numpy** - For parallel MaxCLL/MaxFALL calculation
    -   Install via: `pip install numpy`

### Install HDR Forge

```bash
# Install from source
git clone https://github.com/JanKremser/hdr_forge.git
cd hdr_forge
pip install -e .

# Or install directly with pip (when published to PyPI)
pip install hdr_forge
```

### Verify Installation

```bash
hdr_forge --version
ffmpeg -version
ffprobe -version
x265 --version

# For AV1 support
ffmpeg -hide_banner -encoders | grep svt_av1

# For Dolby Vision support
dovi_tool --help

# For HDR metadata injection
hevc_hdr_editor --help

# Check available hardware encoders
ffmpeg -hide_banner -encoders | grep nvenc
```

**For GPU setup instructions, see [Encoder Guide - GPU Setup](documentation/encoders.md#checking-gpu-support).**

## Usage

### Video Information

Display detailed video metadata:

```bash
hdr_forge info -i video.mkv
```

Shows resolution, frame rate, color information, HDR metadata, and Dolby Vision details if present.

### Basic Conversion

Convert a video with automatic settings:

```bash
# Auto settings (keeps source format, auto crop)
hdr_forge convert -i input.mkv -o output.mkv

# Disable automatic cropping
hdr_forge convert -i input.mkv -o output.mkv --crop off
```

### Encoder Selection

HDR Forge supports multiple encoders:

```bash
# CPU encoding (libx265) - highest quality
hdr_forge convert -i input.mkv -o output.mkv --encoder libx265

# GPU encoding (NVENC) - 3-10x faster
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# H.264 for maximum compatibility
hdr_forge convert -i input.mkv -o output.mkv --encoder libx264

# AV1 for best compression (Beta)
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1

# Stream copy (no re-encoding)
hdr_forge convert -i input.mkv -o output.mkv --video-codec copy
```

**See [Encoder Guide](documentation/encoders.md) for detailed encoder information and comparisons.**

### Hardware Acceleration

```bash
# Balanced GPU encoding (default GPU mode)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# Quality-focused GPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality

# CPU encoding presets
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:balanced
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality
```

**Encoder Comparison:**

| Aspect | CPU (libx265) | GPU (NVENC) | AV1 (Beta) |
|--------|---------------|-------------|------------|
| Speed | Slower | 3-10x faster | Slowest |
| Quality | Highest | Good (slightly lower) | Excellent |
| File Size | Small | Larger (10-20%) | Smallest (20-40% smaller) |
| Compatibility | Excellent | Excellent | Growing |
| Best For | Archival, max quality | Fast encoding, testing | Long-term archival, streaming |

**See [Encoder Guide - Performance Comparison](documentation/encoders.md#performance-comparison) for detailed benchmarks.**

### Encoding Presets

```bash
# Content-aware presets
hdr_forge convert -i film.mkv -o output.mkv --preset film
hdr_forge convert -i action.mkv -o output.mkv --preset action
hdr_forge convert -i anime.mkv -o output.mkv --preset animation

# Banding reduction (8-bit to 10-bit for SDR)
hdr_forge convert -i input.mkv -o output.mkv --preset banding

# Neutral preset for mixed content
hdr_forge convert -i input.mkv -o output.mkv --preset video

# Combine with hardware presets
hdr_forge convert -i film.mkv -o output.mkv \
  --preset film \
  --hw-preset cpu:quality
```

### Cropping

```bash
# Automatic black bar detection
hdr_forge convert -i input.mkv -o output.mkv --crop auto

# Manual crop (width:height:x:y)
hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140

# Aspect ratio crop
hdr_forge convert -i input.mkv -o output.mkv --crop 16:9
hdr_forge convert -i input.mkv -o output.mkv --crop 21:9

# CinemaScope presets
hdr_forge convert -i input.mkv -o output.mkv --crop cinema          # 2.35:1
hdr_forge convert -i input.mkv -o output.mkv --crop cinema-modern   # 2.39:1

# Disable cropping
hdr_forge convert -i input.mkv -o output.mkv --crop off
```

### Resolution Scaling

```bash
# Named resolutions
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD   # 1920x1080
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale HD    # 1280x720
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale QHD+  # 1800p

# Numeric height
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale 1080

# Scaling modes
hdr_forge convert -i input.mkv -o output.mkv --scale 1080 --scale-mode height    # Fixed height
hdr_forge convert -i input.mkv -o output.mkv --scale 1920 --scale-mode adaptive  # Fit within bounds
```

**Available resolutions:** FUHD (8K), UHD (4K), QHD+ (1800p), WQHD (1440p), FHD (1080p), HD (720p), QHD (540p), SD (480p)

**Note:** Only downscaling is supported. Not compatible with Dolby Vision preservation.

### Grain Analysis

```bash
# Automatic grain detection
hdr_forge convert -i old_film.mkv -o output.mkv --grain auto

# Manual grain categories
hdr_forge convert -i input.mkv -o output.mkv --grain cat1  # Light grain
hdr_forge convert -i input.mkv -o output.mkv --grain cat2  # Medium grain
hdr_forge convert -i input.mkv -o output.mkv --grain cat3  # Heavy grain
```

### Logo Removal

```bash
# Automatic logo detection and removal
hdr_forge convert -i input.mkv -o output.mkv --remove-logo auto

# Delogo filter (fast, good for simple logos)
hdr_forge convert -i input.mkv -o output.mkv --remove-logo delogo:auto
hdr_forge convert -i input.mkv -o output.mkv --remove-logo delogo:top-left

# Mask-based removal (better quality)
hdr_forge convert -i input.mkv -o output.mkv --remove-logo mask:auto
hdr_forge convert -i input.mkv -o output.mkv --remove-logo mask:top-right

# Inpainting (experimental, best quality)
hdr_forge convert -i input.mkv -o output.mkv --remove-logo inpaint:auto
hdr_forge convert -i input.mkv -o output.mkv --remove-logo inpaint:bot-left
```

**Note:** Logo removal is not supported for Dolby Vision encoding.

### Dolby Vision

```bash
# Preserve Dolby Vision (re-encode with DV)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop off

# Force Profile 8.1
hdr_forge convert -i dolby_vision.mkv -o output.mkv --dv-profile 8 --crop off

# Convert to HDR10 (extract base layer)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format hdr10

# Fast conversion without re-encoding
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --video-codec copy \
  --hdr-sdr-format hdr10

# Convert to SDR with tone mapping
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format sdr
```

**Important:** Cropping and scaling NOT supported when preserving DV format.

### Format Conversion

```bash
# Convert HDR10 to SDR with tone mapping
hdr_forge convert -i hdr10_video.mkv -o output.mkv --hdr-sdr-format sdr

# Keep source format (default)
hdr_forge convert -i input.mkv -o output.mkv --hdr-sdr-format auto
```

**Format hierarchy:** Dolby Vision → HDR10 → SDR (only downgrades supported)

### Video Sampling

Test encoding settings on short samples:

```bash
# Automatic sample (30s at 1:00)
hdr_forge convert -i large_file.mkv -o sample.mkv --sample auto

# Custom sample (1:30 to 2:00)
hdr_forge convert -i input.mkv -o sample.mkv --sample 90:120

# Fast GPU sample for testing
hdr_forge convert -i input.mkv -o sample.mkv \
  --sample auto \
  --encoder hevc_nvenc

# AV1 sample for quality comparison
hdr_forge convert -i input.mkv -o sample_av1.mkv \
  --sample auto \
  --encoder libsvtav1
```

### Custom Quality Settings

```bash
# Universal quality parameter (all encoders)
hdr_forge convert -i input.mkv -o output.mkv --quality 16

# Speed presets (libx265/libx264 only)
hdr_forge convert -i input.mkv -o output.mkv --speed slow
hdr_forge convert -i input.mkv -o output.mkv --speed slow:plus      # Better than slow
hdr_forge convert -i input.mkv -o output.mkv --speed medium:plus    # Better than medium

# Advanced: encoder-specific parameters
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=slow:crf=14:tune=grain"

hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"
```

### Advanced Options

```bash
# Custom display aspect ratio
hdr_forge convert -i input.mkv -o output.mkv --dar-ratio 16:9
hdr_forge convert -i input.mkv -o output.mkv --dar-ratio cinema

# Custom FFmpeg video filters
hdr_forge convert -i input.mkv -o output.mkv \
  --vfilter "eq=contrast=1.2:brightness=0.05,unsharp=5:5:1.0"
```

### HDR Metadata Injection

Add or update HDR10 metadata without re-encoding (ultra-fast):

```bash
# Inject master display metadata
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(1000,0.05)"

# With MaxCLL/MaxFALL values
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

**See [Advanced Examples - HDR Metadata Injection](documentation/advanced-examples.md#hdr-metadata-injection) for common display presets.**

### Batch Processing

```bash
# Convert all videos in folder
hdr_forge convert -i ./input_folder -o ./output_folder

# With specific settings
hdr_forge convert -i ./videos -o ./encoded \
  --hw-preset gpu:balanced \
  --crop auto \
  --scale FHD

# Batch convert to AV1
hdr_forge convert -i ./videos -o ./av1_encoded \
  --encoder libsvtav1 \
  --quality 23
```

### Supported Formats

**Input:** `.mkv`, `.m2ts`, `.ts`, `.mp4`
**Output:** `.mkv` (H.265/HEVC, H.264, or AV1 video + original audio/subtitle streams)

## Command Reference

### Global Options

```
hdr_forge --version              Show program version
hdr_forge --help                 Show help message
```

### Info Subcommand

```
hdr_forge info -i INPUT          Display video metadata

Options:
  -i, --input INPUT         Input video file
  -d, --debug               Enable debug output
```

### detect-logo Subcommand

```
hdr_forge detect-logo -i INPUT   Detect logos in video

Options:
  -i, --input INPUT         Input video file
  -e, --export PATH         Export detected logo mask as PNG image
  -d, --debug               Enable debug output
```

### extract-metadata Subcommand

```
hdr_forge extract-metadata -i INPUT   Extract DV/HDR10/HDR10+ metadata

Options:
  -i, --input INPUT         Input video file
  -o, --output FOLDER       Output folder for metadata files
  -d, --debug               Enable debug output
```

### inject-metadata Subcommand

```
hdr_forge inject-metadata -i INPUT -o OUTPUT   Inject DV/HDR10/HDR10+ metadata

Description:
  Inject Dolby Vision/HDR10/HDR10+ metadata into HEVC stream without re-encoding

Required Arguments:
  -i, --input INPUT         Input video file
  -o, --output OUTPUT       Output video file

Optional Arguments:
  --rpu PATH                RPU file (Dolby Vision metadata)
  --el PATH                 Enhancement Layer file (DV)
  --hdr10 PATH              HDR10 metadata JSON file
  --hdr10plus PATH          HDR10+ metadata JSON file
  -d, --debug               Enable debug output
```

### Convert Subcommand

```
hdr_forge convert -i INPUT -o OUTPUT [OPTIONS]

Required Arguments:
  -i, --input INPUT         Input video file or folder
  -o, --output OUTPUT       Output video file or folder

Encoder Selection:
  -v, --video-codec CODEC   Video codec: h265, h264, av1, copy (default: h265)
  --encoder CODEC           Force specific encoder: auto, libx265, libx264,
                            libsvtav1, hevc_nvenc, h264_nvenc (default: auto)

Encoding Presets:
  -p, --preset PRESET       Content preset: auto, film, banding, video, action,
                            animation (default: auto)
  --hw-preset PRESET        Hardware preset: cpu:balanced, cpu:quality,
                            gpu:balanced, gpu:quality, balanced, quality
                            (default: cpu:balanced)

Quality Settings:
  --quality VALUE           Universal quality (0-51, lower = better)
  --speed PRESET            Speed preset (libx265/libx264 only):
                            ultrafast, superfast, veryfast, faster, fast,
                            medium, medium:plus, slow, slow:plus, slower, veryslow

Cropping & Scaling:
  --crop MODE               Crop mode: off, auto, width:height:x:y,
                            16:9, 21:9, european, us-widescreen,
                            cinema, cinema-modern (default: off)
  --scale RESOLUTION        Target resolution: FUHD, UHD, QHD+, WQHD, FHD, HD,
                            QHD, SD, or numeric height
  --scale-mode MODE         Scale mode: height, adaptive (default: height)

Content Analysis & Filtering:
  --grain MODE              Grain analysis: off, auto, cat1, cat2, cat3 (default: off)
  --remove-logo MODE        Logo removal: off, auto, delogo:auto, mask:auto,
                            inpaint:auto (default: off)
  --sample TIME             Process sample: auto or start:end in seconds
  --dar-ratio RATIO         Custom display aspect ratio (e.g., 16:9, cinema)
  --vfilter FILTERS         Custom FFmpeg video filters

Format Conversion:
  --hdr-sdr-format FORMAT   Target format: auto, hdr10, sdr (default: auto)
  --dv-profile PROFILE      Dolby Vision profile: auto, 8 (default: auto)

Expert Options:
  --encoder-params PARAMS   Encoder-specific parameters
  --master-display STRING   Custom master display metadata
  --max-cll STRING          Custom MaxCLL/MaxFALL values

Debug:
  -d, --debug               Enable debug output
```

**For detailed parameter explanations, see [Technical Details](documentation/technical-details.md).**

### calc_maxcll Subcommand

```
hdr_forge calc_maxcll -i INPUT   Calculate MaxCLL and MaxFALL (BETA)

Options:
  -i, --input INPUT         Input video file
  -d, --debug               Enable debug output
```

## Automatic Quality Optimization

HDR Forge automatically adjusts encoding parameters based on video resolution:

### CRF/CQ (Quality) - Lower = Better

| Resolution | Pixel Count | CPU Balanced | GPU Balanced | AV1 Balanced |
|------------|-------------|--------------|--------------|--------------|
| 4K+ | 6.1M+ | 13 | 15 | 25 |
| Full HD | 2.1M | 18 | 20 | 23 |
| HD | 1M-2.1M | 19 | 21 | 23 |

**Adjustments:**
- HDR10/DV: +1.0 CRF/CQ (libx265/libx264/NVENC only)
- Action preset: -2.0 CRF/CQ (weighted, libx265/libx264/NVENC only)
- Grain: -1 to -3 CRF/CQ based on category (libx265/libx264 only)

**Note:** AV1 uses higher CRF values due to superior compression efficiency. CRF 25 in AV1 roughly equals CRF 18 in HEVC.

**For detailed calculations, see [Technical Details - Auto-CRF Calculation](documentation/technical-details.md#auto-crfcq-calculation).**

## Examples

### Basic Examples

```bash
# High-quality CPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

# Fast GPU encoding
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# AV1 encoding for long-term archival
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1 --quality 21

# 4K to 1080p with auto crop
hdr_forge convert -i 4k_video.mkv -o 1080p.mkv \
  --scale FHD \
  --crop auto
```

### Complex Workflows

```bash
# Film restoration with grain
hdr_forge convert -i old_film.mkv -o restored.mkv \
  --preset film \
  --grain cat3 \
  --crop auto \
  --quality 14

# Fast batch with GPU
hdr_forge convert -i ./4k_videos -o ./1080p_videos \
  --encoder hevc_nvenc \
  --hw-preset gpu:balanced \
  --crop auto \
  --scale FHD

# Archival encoding with AV1
hdr_forge convert -i source.mkv -o archive.mkv \
  --encoder libsvtav1 \
  --quality 18 \
  --crop auto

# Maximum quality HEVC archival
hdr_forge convert -i source.mkv -o archive.mkv \
  --encoder libx265 \
  --encoder-params "preset=veryslow:crf=12:tune=grain" \
  --crop auto
```

**See [Advanced Examples](documentation/advanced-examples.md) for many more scenarios.**

## Troubleshooting

### Common Issues

**NVENC not available:**
```bash
# Check available encoders
ffmpeg -hide_banner -encoders | grep nvenc

# Update drivers and reinstall FFmpeg with NVENC support
```

**AV1 encoder not found:**
```bash
# Check if SVT-AV1 is available
ffmpeg -hide_banner -encoders | grep svt_av1
```

**Slow crop detection:**
```bash
# Use manual crop instead
hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140

# Or disable cropping
hdr_forge convert -i input.mkv -o output.mkv --crop off
```

**Quality issues:**
```bash
# Lower CRF for better quality
hdr_forge convert -i input.mkv -o output.mkv --quality 14

# Use CPU encoding for maximum quality
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality
```

**See [Troubleshooting Guide](documentation/troubleshooting.md) for detailed solutions.**

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Acknowledgments

-   [FFmpeg](https://ffmpeg.org/) - Video processing
-   [x265](https://www.videolan.org/developers/x265.html) - HEVC encoding
-   [SVT-AV1](https://gitlab.com/AOMediaCodec/SVT-AV1) - AV1 encoding
-   [NVIDIA NVENC](https://developer.nvidia.com/nvidia-video-codec-sdk) - Hardware-accelerated encoding
-   [dovi_tool](https://github.com/quietvoid/dovi_tool) - Dolby Vision metadata handling
-   [hevc_hdr_editor](https://github.com/quietvoid/hevc_hdr_editor) - HDR metadata injection
-   [MKVToolNix](https://mkvtoolnix.download/) - MKV container operations
