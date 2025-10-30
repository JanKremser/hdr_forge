# HDR Forge - SDR/HDR10/DolbyVision Video converter

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line tool for converting video files with hardware-accelerated encoding (NVIDIA NVENC), intelligent HDR metadata preservation, automatic quality optimization, grain analysis, flexible cropping, and advanced format conversion (H.264, H.265/HEVC, Dolby Vision).

## Features

-   **Multiple Encoder Support:** CPU (libx265, libx264) and GPU-accelerated encoding (NVIDIA NVENC)
-   **Hardware Acceleration:** NVIDIA NVENC support for H.265/HEVC and H.264 encoding
-   **Multiple Format Support:** Convert between Dolby Vision, HDR10, and SDR formats
-   **Format Conversion:** DV → HDR10 → SDR with tone mapping support
-   **Dolby Vision Profiles:** Support for Profile 5, 7 (with EL), and 8
-   **HDR Metadata Injection:** Add or update HDR10 metadata without re-encoding
-   **Advanced Cropping:** Automatic black bar detection, manual cropping, aspect ratio presets
-   **Flexible Scaling:** Height-based and adaptive scaling modes
-   **Grain Analysis:** Automatic grain detection with encoding optimization
-   **Content-Aware Presets:** Film, action, and animation-optimized encoding profiles
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

# Convert Dolby Vision to HDR10
hdr_forge convert -i dv.mkv -o output.mkv --hdr-sdr-format hdr10

# Inject HDR metadata without re-encoding
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"
```

## Documentation

- **[Encoder Guide](documentation/encoders.md)** - Comprehensive encoder information (libx265, libx264, NVENC)
- **[Advanced Examples](documentation/advanced-examples.md)** - Complex encoding workflows and examples
- **[Technical Details](documentation/technical-details.md)** - In-depth technical information
- **[Troubleshooting](documentation/troubleshooting.md)** - Solutions to common problems

## Version History

**Current: v0.6.0**

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

## Installation

### Requirements

#### Software Requirements (Mandatory)

-   **Python 3.7 or higher**
-   **[ffmpeg / ffprobe](https://ffmpeg.org/download.html)** with libx265 or libx264 support
-   **[x265 >=4.1](https://github.com/videolan/x265)** for libx265
    -   [Windows builds](http://msystem.waw.pl/x265/)
    -   **Linux:** Available in the repositories

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

**GPU vs CPU Trade-offs:**

| Aspect | CPU (libx265) | GPU (NVENC) |
|--------|---------------|-------------|
| Speed | Slower | 3-10x faster |
| Quality | Highest | Good (slightly lower) |
| File Size | Smallest | Larger (10-20%) |
| Best For | Archival, max quality | Fast encoding, testing |

**See [Encoder Guide - Performance Comparison](documentation/encoders.md#performance-comparison) for detailed benchmarks.**

### Encoding Presets

```bash
# Content-aware presets
hdr_forge convert -i film.mkv -o output.mkv --preset film
hdr_forge convert -i action.mkv -o output.mkv --preset action
hdr_forge convert -i anime.mkv -o output.mkv --preset animation

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
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD  # 1920x1080
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale HD   # 1280x720

# Numeric height
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale 1080

# Scaling modes
hdr_forge convert -i input.mkv -o output.mkv --scale 1080 --scale-mode height    # Fixed height
hdr_forge convert -i input.mkv -o output.mkv --scale 1920 --scale-mode adaptive  # Fit within bounds
```

**Available resolutions:** 8K, UHD (4K), QHD (1440p), FHD (1080p), HD (720p), SD (480p)

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
```

### Custom Quality Settings

```bash
# Universal quality parameter (all encoders)
hdr_forge convert -i input.mkv -o output.mkv --quality 16

# Speed preset (libx265/libx264 only)
hdr_forge convert -i input.mkv -o output.mkv --speed slow

# Advanced: encoder-specific parameters
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=slow:crf=14:tune=grain"

hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"
```

### HDR Metadata Injection

Add or update HDR10 metadata without re-encoding (ultra-fast):

```bash
# Inject master display metadata
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"

# With MaxCLL/MaxFALL values
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
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
```

### Supported Formats

**Input:** `.mkv`, `.m2ts`, `.ts`, `.mp4`
**Output:** `.mkv` (H.265/HEVC or H.264 video + original audio/subtitle streams)

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

### Convert Subcommand

```
hdr_forge convert -i INPUT -o OUTPUT [OPTIONS]

Required Arguments:
  -i, --input INPUT         Input video file or folder
  -o, --output OUTPUT       Output video file or folder

Encoder Selection:
  -v, --video-codec CODEC   Video codec: h265, h264, copy (default: h265)
  --encoder CODEC           Force specific encoder: auto, libx265, libx264,
                            hevc_nvenc, h264_nvenc (default: auto)

Encoding Presets:
  -p, --preset PRESET       Content preset: auto, film, action, animation (default: auto)
  --hw-preset PRESET        Hardware preset: cpu:balanced, cpu:quality,
                            gpu:balanced, gpu:quality (default: cpu:balanced)

Quality Settings:
  --quality VALUE           Universal quality (0-51, lower = better)
  --speed PRESET            Speed preset (libx265/libx264 only):
                            ultrafast, superfast, veryfast, faster, fast,
                            medium, slow, slower, veryslow

Cropping & Scaling:
  --crop MODE               Crop mode: off, auto, width:height:x:y,
                            16:9, 21:9, cinema, cinema-modern (default: off)
  --scale RESOLUTION        Target resolution: 8K, UHD, QHD, FHD, HD, SD,
                            or numeric height
  --scale-mode MODE         Scale mode: height, adaptive (default: height)

Content Analysis:
  --grain MODE              Grain analysis: off, auto, cat1, cat2, cat3 (default: off)
  --sample TIME             Process sample: auto or start:end in seconds

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

### inject-hdr-metadata Subcommand

```
hdr_forge inject-hdr-metadata -i INPUT [OPTIONS]

Description:
  Inject HDR10 metadata into HEVC bitstream without re-encoding

Required Arguments:
  -i, --input INPUT                Input video file (MKV or HEVC)
  --master-display METADATA        Master display metadata

Optional Arguments:
  -o, --output OUTPUT              Output MKV file (default: input.mkv)
  --max-cll VALUES                 MaxCLL and MaxFALL values
  -d, --debug                      Enable debug output
```

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

| Resolution | Pixel Count | CPU Balanced | GPU Balanced |
|------------|-------------|--------------|--------------|
| 4K+ | 6.1M+ | 13 | 15 |
| Full HD | 2.1M | 18 | 20 |
| HD | 1M-2.1M | 19 | 21 |

**Adjustments:**
- HDR10/DV: +1.0 CRF/CQ
- Action preset: -2.0 CRF/CQ (weighted)
- Grain: -1 to -3 CRF/CQ based on category

**For detailed calculations, see [Technical Details - Auto-CRF Calculation](documentation/technical-details.md#auto-crfcq-calculation).**

## Examples

### Basic Examples

```bash
# High-quality CPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

# Fast GPU encoding
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

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

# Archival encoding
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
-   [NVIDIA NVENC](https://developer.nvidia.com/nvidia-video-codec-sdk) - Hardware-accelerated encoding
-   [dovi_tool](https://github.com/quietvoid/dovi_tool) - Dolby Vision metadata handling
-   [hevc_hdr_editor](https://github.com/quietvoid/hevc_hdr_editor) - HDR metadata injection
-   [MKVToolNix](https://mkvtoolnix.download/) - MKV container operations
